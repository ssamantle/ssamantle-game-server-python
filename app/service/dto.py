from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SessionPayload:
    session_id: str
    nickname: str
    game_id: int
    is_host: bool
    participant_id: int | None = None

    def as_session(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "session_id": self.session_id,
            "nickname": self.nickname,
            "game_id": self.game_id,
            "is_host": self.is_host,
        }
        if self.participant_id is not None:
            payload["participant_id"] = self.participant_id
        return payload


@dataclass(frozen=True)
class CreatedGame:
    game_id: int
    session_id: str
    session: SessionPayload


@dataclass(frozen=True)
class JoinedGame:
    game_id: int
    nickname: str
    session_id: str
    session: SessionPayload
