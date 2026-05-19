from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.logger import getLogger
from app.repository.enums import GameStatus
from app.repository.models import Participant
from app.repository.rdb import GameRepository, ParticipantRepository
from app.repository.redis import LeaderboardRepository, ParticipantCacheRepository
from app.schemas.game import JoinGameRequest
from app.service.dto import JoinedGame, SessionPayload
from app.service.exceptions import BadRequestException, GameConflictException
from app.service.exceptions import GameNotFoundException
from app.service.games import V1_GAME_ID, get_game_status

logger = getLogger(__name__)


class ParticipantService:
    def __init__(
        self,
        db: Session,
        games: GameRepository,
        participants: ParticipantRepository,
        leaderboard: LeaderboardRepository,
        participant_cache: ParticipantCacheRepository,
    ):
        self.db = db
        self.games = games
        self.participants = participants
        self.leaderboard = leaderboard
        self.participant_cache = participant_cache

    def join_v1_game(self, body: JoinGameRequest) -> JoinedGame:
        game = self.games.find_by_id(V1_GAME_ID)
        if game is None:
            raise GameNotFoundException()

        nickname = body.nickname.strip()
        if not nickname:
            raise BadRequestException("요청 본문에 nickname 필드는 필수입니다.")

        if get_game_status(game.started_at, game.ended_at) == GameStatus.POSTGAME:
            logger.warning("게임 참가 실패 - 이미 종료된 게임 (nickname=%s)", nickname)
            raise GameConflictException("이미 종료된 게임입니다.")

        if self.participants.find_by_nickname(V1_GAME_ID, nickname):
            logger.warning("게임 참가 실패 - 닉네임 중복: '%s'", nickname)
            raise GameConflictException("이미 사용 중인 닉네임입니다.")

        session_id = str(uuid.uuid4())
        participant = Participant(
            game_id=V1_GAME_ID,
            nickname=nickname,
            session_id=session_id,
        )
        self.participants.add(participant)
        self.db.commit()
        self.db.refresh(participant)

        self.leaderboard.register_participant(V1_GAME_ID, participant.id, 0.0)
        self.participant_cache.put(
            V1_GAME_ID,
            participant.id,
            nickname,
            session_id,
        )

        logger.info("게임 참가 - nickname=%s, participantId=%s", nickname, participant.id)
        session = SessionPayload(
            session_id=session_id,
            nickname=nickname,
            game_id=V1_GAME_ID,
            is_host=False,
            participant_id=participant.id,
        )
        return JoinedGame(
            game_id=V1_GAME_ID,
            nickname=nickname,
            session_id=session_id,
            session=session,
        )
