from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

import redis

from app.core.logger import getLogger

logger = getLogger(__name__)

_KEY = "game:1:info"


@dataclass
class CachedGame:
    started_at: datetime | None
    ended_at: datetime | None


class GameCacheRepository:
    """Redis-backed repository for current game state."""

    def __init__(self, client: redis.Redis):
        self.client = client

    def set(self, started_at: datetime | None, ended_at: datetime | None) -> None:
        payload = json.dumps({
            "started_at": started_at.isoformat() if started_at else None,
            "ended_at": ended_at.isoformat() if ended_at else None,
        })
        self.client.set(_KEY, payload)
        logger.debug("Redis game cache updated - key=%s", _KEY)

    def get(self) -> CachedGame | None:
        raw = self.client.get(_KEY)
        if raw is None:
            logger.debug("Redis game cache miss - key=%s", _KEY)
            return None
        data = json.loads(raw)
        logger.debug("Redis game cache hit - key=%s", _KEY)
        return CachedGame(
            started_at=datetime.fromisoformat(data["started_at"]) if data["started_at"] else None,
            ended_at=datetime.fromisoformat(data["ended_at"]) if data["ended_at"] else None,
        )

    def clear(self) -> None:
        self.client.delete(_KEY)
        logger.debug("Redis game cache cleared - key=%s", _KEY)
