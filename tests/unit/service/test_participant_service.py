from unittest.mock import MagicMock
from uuid import UUID

import pytest

from app.schemas.game import JoinGameRequest
from app.service.exceptions import BadRequestException, GameConflictException, GameNotFoundException
from app.service.games import V1_GAME_ID
from app.service.participants import ParticipantService
from tests.conftest import make_game, utc_now


def build_participant_service():
    db = MagicMock()
    games = MagicMock()
    participants = MagicMock()
    leaderboard = MagicMock()
    participant_cache = MagicMock()
    service = ParticipantService(
        db=db,
        games=games,
        participants=participants,
        leaderboard=leaderboard,
        participant_cache=participant_cache,
    )
    return service, db, games, participants, leaderboard, participant_cache


def test_join_v1_game_raises_when_game_does_not_exist():
    # 대상 게임이 없으면 참가를 막는다.
    service, *_rest, games, _participants, _leaderboard, _cache = build_participant_service()
    games.find_by_id.return_value = None

    with pytest.raises(GameNotFoundException):
        service.join_v1_game(JoinGameRequest(nickname="player"))


def test_join_v1_game_rejects_blank_nickname():
    # 닉네임이 비어 있으면 참가 요청을 거절한다.
    service, *_rest, games, _participants, _leaderboard, _cache = build_participant_service()
    games.find_by_id.return_value = make_game(started_at=None, ended_at=utc_now())

    with pytest.raises(BadRequestException):
        service.join_v1_game(JoinGameRequest(nickname=" "))


def test_join_v1_game_rejects_duplicate_nickname():
    # 같은 게임 안에서 닉네임이 겹치면 참가를 막는다.
    service, *_rest, games, participants, _leaderboard, _cache = build_participant_service()
    games.find_by_id.return_value = make_game(started_at=None, ended_at=utc_now())
    participants.find_by_nickname.return_value = object()

    with pytest.raises(GameConflictException):
        service.join_v1_game(JoinGameRequest(nickname="player"))


def test_join_v1_game_registers_participant_in_db_and_cache(monkeypatch):
    # 참가가 성공하면 DB와 Redis 캐시에 모두 새 참가자를 반영한다.
    service, db, games, participants, leaderboard, participant_cache = build_participant_service()
    games.find_by_id.return_value = make_game()
    participants.find_by_nickname.return_value = None
    monkeypatch.setattr("app.service.participants.uuid.uuid4", lambda: UUID("00000000-0000-0000-0000-000000000789"))

    def refresh_side_effect(participant):
        participant.id = 42

    db.refresh.side_effect = refresh_side_effect

    result = service.join_v1_game(JoinGameRequest(nickname="player"))

    created_participant = participants.add.call_args.args[0]
    assert created_participant.game_id == V1_GAME_ID
    assert created_participant.nickname == "player"
    assert created_participant.session_id == "00000000-0000-0000-0000-000000000789"
    db.commit.assert_called_once()
    leaderboard.register_participant.assert_called_once_with(V1_GAME_ID, 42, 0.0)
    participant_cache.put.assert_called_once_with(
        V1_GAME_ID,
        42,
        "player",
        "00000000-0000-0000-0000-000000000789",
    )
    assert result.session.participant_id == 42
