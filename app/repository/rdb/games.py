from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.repository.models import Game, Participant


class GameRepository:
    """RDB-backed repository for Game aggregates."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, game_id: int) -> Game | None:
        return self.db.query(Game).filter(Game.id == game_id).first()

    def find_latest(self) -> Game | None:
        return self.db.query(Game).order_by(desc(Game.created_at)).first()

    def add(self, game: Game) -> Game:
        self.db.add(game)
        return game

    def exists_host_session(self, session_id: str) -> bool:
        return (
            self.db.query(Game).filter(Game.host_session_id == session_id).first()
            is not None
        )

    def count_participants(self, game_id: int) -> int:
        return self.db.query(Participant).filter(Participant.game_id == game_id).count()
