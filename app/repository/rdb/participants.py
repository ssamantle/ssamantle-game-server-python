from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.core.logger import getLogger
from app.repository.models import Game, Participant

logger = getLogger(__name__)


class ParticipantRepository:
    """RDB-backed repository for Participant entities."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, participant_id: int) -> Participant | None:
        return (
            self.db.query(Participant)
            .filter(Participant.id == participant_id)
            .first()
        )

    def find_by_session_id(self, session_id: str) -> Participant | None:
        return (
            self.db.query(Participant)
            .filter(Participant.session_id == session_id)
            .first()
        )

    def find_by_nickname(self, game_id: int, nickname: str) -> Participant | None:
        return (
            self.db.query(Participant)
            .filter(
                Participant.game_id == game_id,
                Participant.nickname == nickname,
            )
            .first()
        )

    def find_by_nickname_and_session(
        self, game_id: int, nickname: str, session_id: str
    ) -> Participant | None:
        return (
            self.db.query(Participant)
            .filter(
                Participant.game_id == game_id,
                Participant.nickname == nickname,
                Participant.session_id == session_id,
            )
            .first()
        )

    def list_by_game(self, game_id: int) -> list[Participant]:
        return (
            self.db.query(Participant)
            .filter(Participant.game_id == game_id)
            .all()
        )

    def list_by_game_with_guesses(self, game_id: int) -> list[Participant]:
        return (
            self.db.query(Participant)
            .options(selectinload(Participant.guesses))
            .filter(Participant.game_id == game_id)
            .all()
        )

    def list_by_game_with_guesses_ordered_by_best_similarity(
        self, game_id: int
    ) -> list[Participant]:
        participants = (
            self.db.query(Participant)
            .options(selectinload(Participant.guesses))
            .filter(Participant.game_id == game_id)
            .order_by(Participant.best_similarity.desc())
            .all()
        )
        logger.debug(
            "RDB participants loaded with guesses - gameId=%d participants=%d ordering=best_similarity_desc",
            game_id,
            len(participants),
        )
        return participants

    def list_by_game_and_ids_with_guesses(
        self, game_id: int, participant_ids: list[int]
    ) -> list[Participant]:
        if not participant_ids:
            logger.debug(
                "RDB participant hydration skipped - gameId=%d requestedIds=0",
                game_id,
            )
            return []
        participants = (
            self.db.query(Participant)
            .options(selectinload(Participant.guesses))
            .filter(
                Participant.game_id == game_id,
                Participant.id.in_(participant_ids),
            )
            .all()
        )
        logger.debug(
            "RDB participant hydration completed - gameId=%d requestedIds=%d loadedParticipants=%d",
            game_id,
            len(participant_ids),
            len(participants),
        )
        return participants

    def list_by_game_ordered_by_best_similarity(
        self, game_id: int
    ) -> list[Participant]:
        return (
            self.db.query(Participant)
            .filter(Participant.game_id == game_id)
            .order_by(Participant.best_similarity.desc())
            .all()
        )

    def add(self, participant: Participant) -> Participant:
        self.db.add(participant)
        return participant

    def delete_by_game_id(self, game_id: int) -> int:
        participants = (
            self.db.query(Participant)
            .filter(Participant.game_id == game_id)
            .all()
        )
        for participant in participants:
            self.db.delete(participant)
        return len(participants)

    def exists_active_nickname(self, nickname: str) -> bool:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return (
            self.db.query(Participant)
            .join(Game)
            .filter(
                Participant.nickname == nickname,
                or_(Game.ended_at.is_(None), Game.ended_at > now),
            )
            .first()
            is not None
        )
