from __future__ import annotations

from sqlalchemy.orm import Session

from app.repository.models import GuessHistory


class GuessHistoryRepository:
    """RDB-backed repository for guess history records."""

    def __init__(self, db: Session):
        self.db = db

    def add(self, guess: GuessHistory) -> GuessHistory:
        self.db.add(guess)
        return guess

    def list_by_participant_id(self, participant_id: int) -> list[GuessHistory]:
        return (
            self.db.query(GuessHistory)
            .filter(GuessHistory.participant_id == participant_id)
            .all()
        )

    def list_by_participant_id_ordered(
        self, participant_id: int
    ) -> list[GuessHistory]:
        return (
            self.db.query(GuessHistory)
            .filter(GuessHistory.participant_id == participant_id)
            .order_by(GuessHistory.submitted_at.asc(), GuessHistory.id.asc())
            .all()
        )
