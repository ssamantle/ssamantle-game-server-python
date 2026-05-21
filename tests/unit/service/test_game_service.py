from datetime import timedelta
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from app.repository.enums import GameStatus
from app.schemas.game import CreateGameRequest, UpdateWordRequest
from app.service.exceptions import BadRequestException, GameConflictException, WordNotFoundException
from app.service.games import GameService, V1_GAME_ID, get_game_status
from tests.conftest import make_game, make_participant, utc_now


def build_game_service():
    db = MagicMock()
    games = MagicMock()
    participants = MagicMock()
    leaderboard = MagicMock()
    participant_cache = MagicMock()
    vector_store = MagicMock()
    service = GameService(
        db=db,
        games=games,
        participants=participants,
        leaderboard=leaderboard,
        participant_cache=participant_cache,
        vector_store=vector_store,
    )
    return service, db, games, participants, leaderboard, participant_cache, vector_store


def test_get_game_status_returns_pregame_for_future_start():
    # 시작 시간이 미래면 대기 상태로 판단한다.
    now = utc_now()
    status = get_game_status(now + timedelta(minutes=1), now + timedelta(minutes=2), now)
    assert status == GameStatus.PREGAME


def test_get_game_status_returns_ingame_when_started_before_end():
    # 시작 이후 종료 전이면 진행 중 상태로 판단한다.
    now = utc_now()
    status = get_game_status(now - timedelta(minutes=1), now + timedelta(minutes=2), now)
    assert status == GameStatus.INGAME


def test_get_game_status_returns_postgame_after_end():
    # 종료 시간을 넘기면 종료 상태로 판단한다.
    now = utc_now()
    status = get_game_status(now - timedelta(minutes=2), now - timedelta(minutes=1), now)
    assert status == GameStatus.POSTGAME


def test_create_v1_game_rejects_blank_hostname():
    # 호스트 이름이 비어 있으면 바로 예외를 낸다.
    service, *_ = build_game_service()

    with pytest.raises(BadRequestException):
        service.create_v1_game(CreateGameRequest(hostname=" ", targetWord="사랑"))


def test_create_v1_game_rejects_unknown_target_word():
    # 벡터 DB에 없는 단어는 게임 정답으로 허용하지 않는다.
    service, *_rest, vector_store = build_game_service()
    vector_store.word_exists.return_value = False

    with pytest.raises(WordNotFoundException):
        service.create_v1_game(CreateGameRequest(hostname="host", targetWord="없는단어"))


def test_create_v1_game_creates_new_game_when_none_exists(monkeypatch):
    # 기존 게임이 없으면 새 게임을 생성하고 벡터 정보를 갱신한다.
    service, db, games, participants, leaderboard, participant_cache, vector_store = build_game_service()
    vector_store.word_exists.return_value = True
    games.find_by_id.return_value = None
    monkeypatch.setattr("app.service.games.uuid.uuid4", lambda: UUID("00000000-0000-0000-0000-000000000123"))

    body = CreateGameRequest(hostname="host", targetWord="사랑")
    result = service.create_v1_game(body)

    created_game = games.add.call_args.args[0]
    assert created_game.id == V1_GAME_ID
    assert created_game.target_word == "사랑"
    assert result.game_id == V1_GAME_ID
    assert result.session_id == "00000000-0000-0000-0000-000000000123"
    assert result.session.as_session()["is_host"] is True
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(created_game)
    vector_store.refresh_for_target.assert_called_once_with("사랑")
    participants.delete_by_game_id.assert_not_called()
    leaderboard.clear.assert_not_called()
    participant_cache.clear.assert_not_called()


def test_create_v1_game_resets_existing_game_and_clears_caches(monkeypatch):
    # 기존 게임이 있으면 참가자와 캐시를 비우고 같은 게임을 재사용한다.
    service, db, games, participants, leaderboard, participant_cache, vector_store = build_game_service()
    vector_store.word_exists.return_value = True
    existing = make_game(target_word="기존단어", hostname="old-host")
    games.find_by_id.return_value = existing
    monkeypatch.setattr("app.service.games.uuid.uuid4", lambda: UUID("00000000-0000-0000-0000-000000000456"))

    body = CreateGameRequest(hostname="new-host", targetWord="새단어")
    result = service.create_v1_game(body)

    assert existing.hostname == "new-host"
    assert existing.target_word == "새단어"
    assert existing.host_session_id == "00000000-0000-0000-0000-000000000456"
    participants.delete_by_game_id.assert_called_once_with(V1_GAME_ID)
    leaderboard.clear.assert_called_once_with(V1_GAME_ID)
    participant_cache.clear.assert_called_once_with(V1_GAME_ID)
    vector_store.refresh_for_target.assert_called_once_with("새단어")
    assert result.session.nickname == "new-host"


def test_update_v1_word_rejects_when_game_already_started():
    # 진행 중 게임에서는 정답 단어를 바꿀 수 없다.
    service, _db, games, *_rest = build_game_service()
    games.find_by_id.return_value = make_game(
        started_at=utc_now() - timedelta(minutes=1),
        ended_at=utc_now() + timedelta(minutes=1),
    )

    with pytest.raises(GameConflictException):
        service.update_v1_word(UpdateWordRequest(targetWord="새단어"))


def test_update_v1_word_updates_target_and_refreshes_vector_store():
    # 대기 상태 게임이면 정답 단어를 갱신하고 유사도 캐시를 다시 만든다.
    service, db, games, *_rest, vector_store = build_game_service()
    game = make_game(target_word="이전단어")
    games.find_by_id.return_value = game
    vector_store.word_exists.return_value = True

    service.update_v1_word(UpdateWordRequest(targetWord="새단어"))

    assert game.target_word == "새단어"
    db.commit.assert_called_once()
    vector_store.refresh_for_target.assert_called_once_with("새단어")


def test_get_v1_result_maps_repository_order_to_ranked_response():
    # 저장소가 준 순서를 그대로 랭킹 응답으로 바꾼다.
    service, _db, games, participants, *_rest = build_game_service()
    games.find_by_id.return_value = make_game(target_word="사랑")
    participants.list_by_game_ordered_by_best_similarity.return_value = [
        make_participant(participant_id=10, nickname="alpha", best_similarity=0.9, closest_word="가족", is_correct=True),
        make_participant(participant_id=11, nickname="beta", best_similarity=0.7, closest_word="친구", is_correct=False),
    ]

    result = service.get_v1_result()

    assert result.targetWord == "사랑"
    assert [item.rank for item in result.participants] == [1, 2]
    assert [item.nickname for item in result.participants] == ["alpha", "beta"]
