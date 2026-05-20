from unittest.mock import MagicMock

import pytest

from app.service.auth import (
    AuthService,
    get_session_or_raise,
    parse_authorization_token,
    require_host_session,
)
from app.service.exceptions import HostOnlyException, UnauthorizedException


def test_parse_authorization_token_strips_bearer_prefix():
    # Bearer 접두사가 있으면 실제 토큰만 꺼낸다.
    assert parse_authorization_token("Bearer abc123") == "abc123"


def test_parse_authorization_token_returns_raw_value_for_non_bearer():
    # Bearer 형식이 아니면 원본 값을 그대로 사용한다.
    assert parse_authorization_token("plain-token") == "plain-token"


def test_validate_token_returns_true_for_host_session():
    # 호스트 세션이 존재하면 토큰을 유효하다고 본다.
    games = MagicMock()
    participants = MagicMock()
    games.exists_host_session.return_value = True

    service = AuthService(games=games, participants=participants)

    assert service.validate_token("Bearer host-token") is True
    participants.find_by_session_id.assert_not_called()


def test_validate_token_returns_true_for_participant_session():
    # 참가자 세션이 존재해도 토큰을 유효하다고 본다.
    games = MagicMock()
    participants = MagicMock()
    games.exists_host_session.return_value = False
    participants.find_by_session_id.return_value = object()

    service = AuthService(games=games, participants=participants)

    assert service.validate_token("Bearer player-token") is True


def test_get_session_or_raise_rejects_missing_nickname():
    # 닉네임이 없으면 인증되지 않은 세션으로 처리한다.
    with pytest.raises(UnauthorizedException):
        get_session_or_raise({})


def test_require_host_session_returns_session_for_valid_host():
    # 호스트 세션이면 그대로 통과시킨다.
    session = {
        "nickname": "host",
        "is_host": True,
        "game_id": 1,
    }

    assert require_host_session(session, 1) is session


def test_require_host_session_rejects_non_host_user():
    # 호스트가 아니면 권한 오류를 발생시킨다.
    session = {
        "nickname": "player",
        "is_host": False,
        "game_id": 1,
    }

    with pytest.raises(HostOnlyException):
        require_host_session(session, 1)
