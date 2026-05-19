from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logger import getLogger
from app.repository.enums import GameStatus
from app.repository.models import Game
from app.repository.rdb import GameRepository, ParticipantRepository
from app.repository.redis import LeaderboardRepository, ParticipantCacheRepository
from app.repository.vector import VectorStore
from app.schemas.game import CreateGameRequest, GameResultResponse, ParticipantResult
from app.schemas.game import UpdateEndtimeRequest, UpdateWordRequest
from app.service.dto import CreatedGame, SessionPayload
from app.service.exceptions import (
    BadRequestException,
    GameConflictException,
    GameNotFoundException,
    WordNotFoundException,
)

logger = getLogger(__name__)

V1_GAME_ID = 1


def get_game_status(
    started_at: datetime | None,
    ended_at: datetime | None,
    now: datetime | None = None,
) -> GameStatus:
    current = now or datetime.now(timezone.utc).replace(tzinfo=None)
    if ended_at and current >= ended_at:
        return GameStatus.POSTGAME
    if started_at and current >= started_at:
        return GameStatus.INGAME
    return GameStatus.PREGAME


class GameService:
    def __init__(
        self,
        db: Session,
        games: GameRepository,
        participants: ParticipantRepository,
        leaderboard: LeaderboardRepository,
        participant_cache: ParticipantCacheRepository,
        vector_store: VectorStore,
    ):
        self.db = db
        self.games = games
        self.participants = participants
        self.leaderboard = leaderboard
        self.participant_cache = participant_cache
        self.vector_store = vector_store

    def get_game_or_raise(self, game_id: int) -> Game:
        game = self.games.find_by_id(game_id)
        if game is None:
            raise GameNotFoundException()
        return game

    def create_v1_game(self, body: CreateGameRequest) -> CreatedGame:
        hostname = body.hostname.strip()
        target_word = body.targetWord.strip()
        if not hostname:
            raise BadRequestException("요청 본문에 hostname 필드는 필수입니다.")
        if not target_word:
            raise BadRequestException("요청 본문에 targetWord 필드는 필수입니다.")
        if not self.vector_store.word_exists(target_word):
            logger.warning(
                "게임 생성 실패 - 사전에 없는 단어: '%s' (host=%s)",
                target_word,
                hostname,
            )
            raise WordNotFoundException(f"'{target_word}'은(는) 사전에 없는 단어입니다.")

        session_id = str(uuid.uuid4())
        initial_status = get_game_status(
            body.startTime.replace(tzinfo=None) if body.startTime else None,
            body.endTime.replace(tzinfo=None) if body.endTime else None,
        )

        game = self.games.find_by_id(V1_GAME_ID)
        if game is None:
            logger.info(
                "게임 생성 - host=%s, targetWord=%s, status=%s",
                hostname,
                target_word,
                initial_status,
            )
            game = Game(
                id=V1_GAME_ID,
                hostname=hostname,
                host_session_id=session_id,
                target_word=target_word,
                started_at=body.startTime,
                ended_at=body.endTime,
            )
            self.games.add(game)
        else:
            logger.info(
                "게임 재생성 (덮어쓰기) - host=%s, targetWord=%s, status=%s",
                hostname,
                target_word,
                initial_status,
            )
            game.hostname = hostname
            game.host_session_id = session_id
            game.target_word = target_word
            game.started_at = body.startTime
            game.ended_at = body.endTime
            game.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
            self.participants.delete_by_game_id(V1_GAME_ID)
            self.leaderboard.clear(V1_GAME_ID)
            self.participant_cache.clear(V1_GAME_ID)

        self.db.commit()
        self.db.refresh(game)
        self.vector_store.refresh_for_target(game.target_word)

        session = SessionPayload(
            session_id=session_id,
            nickname=hostname,
            game_id=V1_GAME_ID,
            is_host=True,
        )
        return CreatedGame(game_id=V1_GAME_ID, session_id=session_id, session=session)

    def update_v1_time(self, body: UpdateEndtimeRequest) -> None:
        game = self.get_game_or_raise(V1_GAME_ID)
        if body.startedAt is not None:
            game.started_at = body.startedAt
        if body.endedAt is not None:
            game.ended_at = body.endedAt
        self.db.commit()
        logger.info(
            "게임 시간 수정 - startedAt=%s, endedAt=%s",
            game.started_at,
            game.ended_at,
        )

    def update_v1_word(self, body: UpdateWordRequest) -> None:
        game = self.get_game_or_raise(V1_GAME_ID)
        status = get_game_status(game.started_at, game.ended_at)
        if status != GameStatus.PREGAME:
            logger.warning("단어 수정 실패 - 게임이 이미 시작됨 (status=%s)", status)
            raise GameConflictException("게임 시작 전에만 단어를 수정할 수 있습니다.")

        target_word = body.targetWord.strip()
        if not target_word:
            raise BadRequestException("요청 본문에 targetWord 필드는 필수입니다.")
        if not self.vector_store.word_exists(target_word):
            logger.warning("단어 수정 실패 - 사전에 없는 단어: '%s'", target_word)
            raise WordNotFoundException(f"'{target_word}'은(는) 사전에 없는 단어입니다.")

        logger.info("정답 단어 수정 - '%s' -> '%s'", game.target_word, target_word)
        game.target_word = target_word
        self.db.commit()
        self.vector_store.refresh_for_target(game.target_word)

    def end_v1_game(self) -> None:
        game = self.get_game_or_raise(V1_GAME_ID)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if not game.ended_at or game.ended_at > now:
            game.ended_at = now
        self.db.commit()
        logger.info("게임 강제 종료 - gameId=%d", V1_GAME_ID)

    def get_v1_result(self) -> GameResultResponse:
        game = self.get_game_or_raise(V1_GAME_ID)
        participants = self.participants.list_by_game_ordered_by_best_similarity(
            V1_GAME_ID
        )
        result_list = [
            ParticipantResult(
                rank=i + 1,
                nickname=participant.nickname,
                bestSimilarity=round(participant.best_similarity, 4),
                closestWord=participant.closest_word,
                isCorrect=participant.is_correct,
            )
            for i, participant in enumerate(participants)
        ]
        return GameResultResponse(
            targetWord=game.target_word,
            startedAt=game.started_at,
            endedAt=game.ended_at,
            participants=result_list,
        )
