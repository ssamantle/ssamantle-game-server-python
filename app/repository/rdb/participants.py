from __future__ import annotations

from sqlalchemy.orm import Session, selectinload

from app.repository.enums import GameStatus
from app.repository.models import Game, Participant


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
        return (
            self.db.query(Participant)
            .join(Game)
            .filter(
                Participant.nickname == nickname,
                Game.status.in_([GameStatus.PREGAME, GameStatus.INGAME]),
            )
            .first()
            is not None
        )
