from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logger import getLogger
from app.repository.enums import GameStatus
from app.repository.models import GuessHistory
from app.repository.rdb import GameRepository, GuessHistoryRepository
from app.repository.rdb import ParticipantRepository
from app.repository.redis import ParticipantCacheRepository
from app.repository.redis import LeaderboardRepository
from app.repository.vector import VectorStore
from app.schemas.game import GuessHistoryItem, GuessRequest, GuessResponse
from app.service.auth import parse_authorization_token
from app.service.exceptions import BadRequestException, GameConflictException
from app.service.exceptions import GameNotFoundException, UnauthorizedException
from app.service.exceptions import WordNotFoundException
from app.service.games import V1_GAME_ID, get_game_status

logger = getLogger(__name__)


class GuessService:
    def __init__(
        self,
        db: Session,
        games: GameRepository,
        participants: ParticipantRepository,
        participant_cache: ParticipantCacheRepository,
        guesses: GuessHistoryRepository,
        leaderboard: LeaderboardRepository,
        vector_store: VectorStore,
    ):
        self.db = db
        self.games = games
        self.participants = participants
        self.participant_cache = participant_cache
        self.guesses = guesses
        self.leaderboard = leaderboard
        self.vector_store = vector_store

    def submit_v1_guess(
        self,
        body: GuessRequest,
        authorization: str,
    ) -> GuessResponse:
        game = self.games.find_by_id(V1_GAME_ID)
        if game is None:
            raise GameNotFoundException()
        if get_game_status(game.started_at, game.ended_at) != GameStatus.INGAME:
            raise GameConflictException("게임이 진행 중이 아닙니다.")

        word = body.word.strip()
        username = body.username.strip()
        if not word or not username:
            raise BadRequestException("요청 본문에 word와 username 필드는 필수입니다.")

        session_id = parse_authorization_token(authorization)
        participant = self.participants.find_by_nickname(V1_GAME_ID, username)
        if not participant or participant.session_id != session_id:
            logger.warning("추측 인증 실패 - username=%s", username)
            raise UnauthorizedException()

        result = self.vector_store.get_similarity_and_rank(word)
        if result is None:
            logger.info("추측 실패 - 사전에 없는 단어: '%s' (username=%s)", word, username)
            raise WordNotFoundException("사전에 없는 단어입니다.")

        raw_similarity, word_rank = result
        similarity = round(max(0.0, raw_similarity), 4)
        is_answer = word == game.target_word

        is_new_best = similarity > participant.best_similarity
        if is_new_best:
            participant.best_similarity = similarity
            participant.closest_word = word
            best_word_rank = word_rank
        else:
            cached = self.participant_cache.get(V1_GAME_ID, participant.id)
            best_word_rank = cached.get("bestWordRank", 0) if cached else 0

        if is_answer:
            participant.is_correct = True
            logger.info("정답 맞힘 - username=%s, word=%s", username, word)

        self.guesses.add(
            GuessHistory(
                participant_id=participant.id,
                word=word,
                similarity=similarity,
                word_rank=word_rank,
                is_answer=is_answer,
            )
        )
        
        # RDB 커밋 후 Redis 캐시 업데이트
        # RDB가 더 신뢰할 수 있는 데이터소스이므로, 커밋 이후에 캐시를 업데이트하여 일관성을 유지
        # 커밋 전에 캐시를 업데이트하면, RDB 커밋 실패 시 캐시와 RDB 간 데이터 불일치가 발생할 수 있음
        # 오염된 데이터보다 오래된 데이터가 캐시에 남아있는 것이 더 낫다고 판단하여 커밋 이후에 캐시 업데이트
        self.db.commit()
        
        # 참가자 정보 캐시 업데이트
        self.participant_cache.put(
            V1_GAME_ID,
            participant.id,
            participant.nickname,
            session_id,
            best_similarity=participant.best_similarity,
            best_word_rank=best_word_rank,
            latest_similarity=similarity,
            latest_word_rank=word_rank,
        )

        # 리더보드 업데이트
        self.leaderboard.update_score(
            V1_GAME_ID,
            participant.id,
            participant.best_similarity,
        )
        game_rank = self.leaderboard.get_rank(V1_GAME_ID, participant.id) or 1

        logger.debug(
            "추측 결과 - username=%s, word=%s, similarity=%s, wordRank=%d, gameRank=%d",
            username,
            word,
            similarity,
            word_rank,
            game_rank,
        )
        return GuessResponse(
            label=word,
            similarity=similarity,
            rank=game_rank,
            wordRank=word_rank,
            isAnswer=is_answer,
        )

    def get_v1_guess_history(
        self,
        username: str,
        authorization: str,
    ) -> list[GuessHistoryItem]:
        session_id = parse_authorization_token(authorization)
        participant = self.participants.find_by_nickname(V1_GAME_ID, username)
        if not participant or participant.session_id != session_id:
            logger.warning("추측 기록 조회 인증 실패 - username=%s", username)
            raise UnauthorizedException()

        result = []
        for guess in participant.guesses:
            if guess.similarity == participant.best_similarity:
                rank = self.leaderboard.get_rank(V1_GAME_ID, participant.id)
                game_rank = rank if rank is not None else -1
            else:
                game_rank = -1
            result.append(
                GuessHistoryItem(
                    label=guess.word,
                    similarity=guess.similarity,
                    rank=game_rank,
                    wordRank=guess.word_rank,
                    isAnswer=guess.is_answer,
                )
            )
        return result
