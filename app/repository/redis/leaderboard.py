from __future__ import annotations

import redis


class LeaderboardRepository:
    """Redis-backed repository for leaderboard state."""

    def __init__(self, client: redis.Redis):
        self.client = client

    def clear(self, game_id: int) -> None:
        self.client.delete(self._leaderboard_key(game_id))

    def register_participant(
        self, game_id: int, participant_id: int, score: float = 0.0
    ) -> None:
        self.client.zadd(
            self._leaderboard_key(game_id),
            {participant_id: score},
            nx=True,
        )

    def update_score(self, game_id: int, participant_id: int, score: float) -> None:
        self.client.zadd(self._leaderboard_key(game_id), {participant_id: score})

    def get_rank(self, game_id: int, participant_id: int) -> int | None:
        rank = self.client.zrevrank(self._leaderboard_key(game_id), participant_id)
        if rank is None:
            return None
        return int(rank) + 1

    def list_entries(self, game_id: int) -> list[tuple[int, float]]:
        entries = self.client.zrevrange(
            self._leaderboard_key(game_id),
            0,
            -1,
            withscores=True,
        )
        return [(int(member), float(score)) for member, score in entries]

    @staticmethod
    def _leaderboard_key(game_id: int) -> str:
        return f"game:{game_id}:leaderboard"
