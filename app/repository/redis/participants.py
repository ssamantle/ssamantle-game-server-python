from __future__ import annotations

import json

import redis


class ParticipantCacheRepository:
    """Redis-backed repository for participant lookup/cache data."""

    def __init__(self, client: redis.Redis):
        self.client = client

    def clear(self, game_id: int) -> None:
        self.client.delete(self._participants_key(game_id))

    def put(
        self,
        game_id: int,
        participant_id: int,
        nickname: str,
        session_id: str,
        best_similarity: float,
        best_word_rank: int,
        latest_similarity: float,
        latest_word_rank: int,
    ) -> None:
        payload = json.dumps({
            "nickname": nickname,
            "sessionId": session_id,
            "bestSimilarity": best_similarity,
            "bestWordRank": best_word_rank,
            "latestSimilarity": latest_similarity,
            "latestWordRank": latest_word_rank,
        })
        self.client.hset(self._participants_key(game_id), participant_id, payload)

    def get_all(self, game_id: int) -> dict[int, dict]:
        raw_entries = self.client.hgetall(self._participants_key(game_id))
        result: dict[int, dict] = {}
        for participant_id, payload in raw_entries.items():
            result[int(participant_id)] = json.loads(payload)
        return result

    def get(self, game_id: int, participant_id: int) -> dict | None:
        payload = self.client.hget(self._participants_key(game_id), participant_id)
        if payload is None:
            return None
        return json.loads(payload)

    @staticmethod
    def _participants_key(game_id: int) -> str:
        return f"game:{game_id}:participants"
