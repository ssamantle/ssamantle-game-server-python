from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.service.exceptions import GameNotFoundException
from app.service.leaderboard import (
    LeaderboardService,
    _build_submission_summary,
    to_unix_ms,
)
from tests.conftest import make_game, make_guess, make_participant, utc_now


def build_leaderboard_service():
    games = MagicMock()
    participants = MagicMock()
    leaderboard = MagicMock()
    service = LeaderboardService(
        games=games,
        participants=participants,
        leaderboard=leaderboard,
    )
    return service, games, participants, leaderboard


def test_to_unix_ms_returns_none_for_missing_datetime():
    # 시간이 없으면 Unix ms 값도 비워 둔다.
    assert to_unix_ms(None) is None


def test_to_unix_ms_converts_datetime_to_epoch_milliseconds():
    # UTC 기준 시각을 밀리초 단위 정수로 바꾼다.
    dt = datetime(2026, 5, 20, 0, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None)
    assert to_unix_ms(dt) == 1779235200000


def test_get_v1_game_info_from_cache_raises_when_game_is_missing():
    # 게임 정보가 없으면 polling 응답도 만들지 못한다.
    service, games, *_rest = build_leaderboard_service()
    games.find_by_id.return_value = None

    with pytest.raises(GameNotFoundException):
        service.get_v1_game_info_from_cache()


def test_get_v1_game_info_from_cache_maps_cache_entries_to_users():
    # Redis 순위와 참가자 정보를 합쳐 polling 응답을 만든다.
    service, games, participants, leaderboard = build_leaderboard_service()
    games.find_by_id.return_value = make_game(
        started_at=utc_now(),
        ended_at=utc_now(),
    )
    participant = make_participant(
        participant_id=10,
        nickname="alpha",
        best_similarity=0.9,
        closest_word="사랑",
        guesses=[
            make_guess(guess_id=1, participant_id=10, word="사랑", similarity=0.9, word_rank=2),
            make_guess(guess_id=2, participant_id=10, word="가족", similarity=0.8, word_rank=8),
        ],
    )
    leaderboard.list_entries.return_value = [(10, 0.9), (11, 0.7)]
    participants.list_by_game_and_ids_with_guesses.return_value = [participant]

    result = service.get_v1_game_info_from_cache()

    assert len(result.users) == 1
    assert result.users[0].name == "alpha"
    assert result.users[0].rank == 1
    assert result.users[0].bestSubmission.wordRank == 2
    assert result.users[0].latestSubmission.wordRank == 8


def test_get_v1_game_info_from_db_builds_ranked_user_list():
    # DB에서 정렬된 참가자 목록을 받아 응답으로 변환한다.
    service, games, participants, _leaderboard = build_leaderboard_service()
    games.find_by_id.return_value = make_game()
    participants.list_by_game_with_guesses_ordered_by_best_similarity.return_value = [
        make_participant(
            participant_id=10,
            nickname="alpha",
            best_similarity=0.9,
            guesses=[make_guess(guess_id=1, participant_id=10, word="사랑", similarity=0.9, word_rank=1)],
        ),
        make_participant(
            participant_id=11,
            nickname="beta",
            best_similarity=0.8,
            guesses=[make_guess(guess_id=2, participant_id=11, word="가족", similarity=0.8, word_rank=3)],
        ),
    ]

    result = service.get_v1_game_info_from_db()

    assert [user.name for user in result.users] == ["alpha", "beta"]
    assert [user.rank for user in result.users] == [1, 2]


def test_build_submission_summary_returns_none_for_missing_guess():
    # 추측이 없으면 요약 정보도 만들지 않는다.
    assert _build_submission_summary(None) is None


def test_build_submission_summary_rounds_similarity():
    # 응답용 요약은 유사도를 소수 넷째 자리까지 반올림한다.
    summary = _build_submission_summary(
        make_guess(similarity=0.87654, word_rank=7),
    )
    assert summary.similarity == 0.8765
    assert summary.wordRank == 7
