from __future__ import annotations

from app.repository.rdb import GameRepository, ParticipantRepository
from app.service.exceptions import HostOnlyException, UnauthorizedException


def parse_authorization_token(authorization: str) -> str:
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return authorization


class AuthService:
    def __init__(
        self,
        games: GameRepository,
        participants: ParticipantRepository,
    ):
        self.games = games
        self.participants = participants

    def validate_token(self, authorization: str) -> bool:
        session_id = parse_authorization_token(authorization)
        return (
            self.games.exists_host_session(session_id)
            or self.participants.find_by_session_id(session_id) is not None
        )


def get_session_or_raise(session: dict) -> dict:
    if not session.get("nickname"):
        raise UnauthorizedException()
    return session


def require_host_session(session: dict, game_id: int) -> dict:
    session = get_session_or_raise(session)
    if not session.get("is_host") or session.get("game_id") != game_id:
        raise HostOnlyException()
    return session
