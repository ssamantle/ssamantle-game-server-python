from __future__ import annotations

import redis

from app.core.logger import getLogger

logger = getLogger(__name__)


class LeaderboardRepository:
    """Redis-backed repository for leaderboard state."""

    def __init__(self, client: redis.Redis):
        self.client = client

    def clear(self, game_id: int) -> None:
        key = self._leaderboard_key(game_id)
        self.client.delete(key)
        logger.debug("Redis leaderboard cleared - gameId=%d key=%s", game_id, key)

    def register_participant(
        self, game_id: int, participant_id: int, score: float = 0.0
    ) -> None:
        key = self._leaderboard_key(game_id)
        self.client.zadd(
            key,
            {participant_id: score},
            nx=True,
        )
        logger.debug(
            "Redis leaderboard participant registered - gameId=%d key=%s participantId=%d score=%.4f",
            game_id,
            key,
            participant_id,
            score,
        )

    def update_score(self, game_id: int, participant_id: int, score: float) -> None:
        key = self._leaderboard_key(game_id)
        self.client.zadd(key, {participant_id: score})
        logger.debug(
            "Redis leaderboard score updated - gameId=%d key=%s participantId=%d score=%.4f",
            game_id,
            key,
            participant_id,
            score,
        )

    def get_rank(self, game_id: int, participant_id: int) -> int | None:
        key = self._leaderboard_key(game_id)
        rank = self.client.zrevrank(key, participant_id)
        if rank is None:
            logger.debug(
                "Redis leaderboard rank miss - gameId=%d key=%s participantId=%d",
                game_id,
                key,
                participant_id,
            )
            return None
        resolved_rank = int(rank) + 1
        logger.debug(
            "Redis leaderboard rank hit - gameId=%d key=%s participantId=%d rank=%d",
            game_id,
            key,
            participant_id,
            resolved_rank,
        )
        return resolved_rank

    def list_entries(self, game_id: int) -> list[tuple[int, float]]:
        key = self._leaderboard_key(game_id)
        entries = self.client.zrevrange(
            key,
            0,
            -1,
            withscores=True,
        )
        logger.debug(
            "Redis leaderboard entries fetched - gameId=%d key=%s entries=%d",
            game_id,
            key,
            len(entries),
        )
        return [(int(member), float(score)) for member, score in entries]

    @staticmethod
    def _leaderboard_key(game_id: int) -> str:
        return f"game:{game_id}:leaderboard"
