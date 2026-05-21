from fastapi import Depends
from sqlalchemy.orm import Session

from app.repository.database import get_db
from app.repository.rdb import (
    GameRepository,
    GuessHistoryRepository,
    ParticipantRepository,
)
from app.repository.redis import (
    LeaderboardRepository,
    ParticipantCacheRepository,
)
from app.repository.redis.client import get_redis_client
from app.repository.vector import VectorStore


def get_game_repository(db: Session = Depends(get_db)) -> GameRepository:
    return GameRepository(db)


def get_participant_repository(
    db: Session = Depends(get_db),
) -> ParticipantRepository:
    return ParticipantRepository(db)


def get_guess_history_repository(
    db: Session = Depends(get_db),
) -> GuessHistoryRepository:
    return GuessHistoryRepository(db)


def get_leaderboard_repository() -> LeaderboardRepository:
    return LeaderboardRepository(get_redis_client())


def get_participant_cache_repository() -> ParticipantCacheRepository:
    return ParticipantCacheRepository(get_redis_client())


def get_vector_store() -> VectorStore:
    return VectorStore()
