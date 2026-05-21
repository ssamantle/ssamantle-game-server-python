from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from app.repository.models import GuessHistory
from app.schemas.game import GuessRequest
from app.service.exceptions import (
    BadRequestException,
    GameConflictException,
    GameNotFoundException,
    UnauthorizedException,
    WordNotFoundException,
)
from app.service.guesses import GuessService
from tests.conftest import make_game, make_guess, make_participant, utc_now


def build_guess_service():
    db = MagicMock()
    games = MagicMock()
    participants = MagicMock()
    guesses = MagicMock()
    leaderboard = MagicMock()
    vector_store = MagicMock()
    service = GuessService(
        db=db,
        games=games,
        participants=participants,
        guesses=guesses,
        leaderboard=leaderboard,
        vector_store=vector_store,
    )
    return service, db, games, participants, guesses, leaderboard, vector_store


def test_submit_v1_guess_raises_when_game_does_not_exist():
    # 게임이 없으면 추측 요청을 처리하지 않는다.
    service, _db, games, *_rest = build_guess_service()
    games.find_by_id.return_value = None

    with pytest.raises(GameNotFoundException):
        service.submit_v1_guess(GuessRequest(username="player", word="사랑"), "Bearer token")


def test_submit_v1_guess_rejects_when_game_is_not_ingame():
    # 게임이 진행 중이 아니면 추측을 받을 수 없다.
    service, _db, games, *_rest = build_guess_service()
    games.find_by_id.return_value = make_game(
        started_at=utc_now() + timedelta(minutes=1),
        ended_at=utc_now() + timedelta(minutes=2),
    )

    with pytest.raises(GameConflictException):
        service.submit_v1_guess(GuessRequest(username="player", word="사랑"), "Bearer token")


def test_submit_v1_guess_rejects_blank_fields():
    # 단어와 사용자 이름이 비어 있으면 예외를 발생시킨다.
    service, _db, games, *_rest = build_guess_service()
    games.find_by_id.return_value = make_game(
        started_at=utc_now() - timedelta(minutes=1),
        ended_at=utc_now() + timedelta(minutes=1),
    )

    with pytest.raises(BadRequestException):
        service.submit_v1_guess(GuessRequest(username=" ", word=" "), "Bearer token")


def test_submit_v1_guess_rejects_invalid_token():
    # 세션 토큰이 참가자와 맞지 않으면 인증 오류를 낸다.
    service, _db, games, participants, *_rest = build_guess_service()
    games.find_by_id.return_value = make_game(
        started_at=utc_now() - timedelta(minutes=1),
        ended_at=utc_now() + timedelta(minutes=1),
    )
    participants.find_by_nickname.return_value = make_participant(session_id="other-token")

    with pytest.raises(UnauthorizedException):
        service.submit_v1_guess(GuessRequest(username="player", word="사랑"), "Bearer token")


def test_submit_v1_guess_rejects_unknown_word():
    # 벡터 DB에 없는 단어는 추측 결과를 만들지 못한다.
    service, _db, games, participants, _guesses, _leaderboard, vector_store = build_guess_service()
    games.find_by_id.return_value = make_game(
        started_at=utc_now() - timedelta(minutes=1),
        ended_at=utc_now() + timedelta(minutes=1),
    )
    participants.find_by_nickname.return_value = make_participant(session_id="token")
    vector_store.get_similarity_and_rank.return_value = None

    with pytest.raises(WordNotFoundException):
        service.submit_v1_guess(GuessRequest(username="player", word="없는단어"), "Bearer token")


def test_submit_v1_guess_updates_best_similarity_and_rank():
    # 더 좋은 추측이면 최고 유사도와 랭킹 정보를 갱신한다.
    service, db, games, participants, guesses, leaderboard, vector_store = build_guess_service()
    games.find_by_id.return_value = make_game(
        target_word="정답",
        started_at=utc_now() - timedelta(minutes=1),
        ended_at=utc_now() + timedelta(minutes=1),
    )
    participant = make_participant(session_id="token", best_similarity=0.2)
    participants.find_by_nickname.return_value = participant
    vector_store.get_similarity_and_rank.return_value = (0.87654, 12)
    leaderboard.get_rank.return_value = 2

    result = service.submit_v1_guess(
        GuessRequest(username="player", word="가족"),
        "Bearer token",
    )

    added_guess = guesses.add.call_args.args[0]
    assert isinstance(added_guess, GuessHistory)
    assert participant.best_similarity == 0.8765
    assert participant.closest_word == "가족"
    db.commit.assert_called_once()
    leaderboard.update_score.assert_called_once_with(1, participant.id, 0.8765)
    assert result.rank == 2
    assert result.wordRank == 12
    assert result.isAnswer is False


def test_submit_v1_guess_marks_correct_answer():
    # 정답을 맞히면 참가자의 정답 상태를 켠다.
    service, _db, games, participants, guesses, leaderboard, vector_store = build_guess_service()
    games.find_by_id.return_value = make_game(
        target_word="정답",
        started_at=utc_now() - timedelta(minutes=1),
        ended_at=utc_now() + timedelta(minutes=1),
    )
    participant = make_participant(session_id="token", best_similarity=0.0)
    participants.find_by_nickname.return_value = participant
    vector_store.get_similarity_and_rank.return_value = (1.0, 1)
    leaderboard.get_rank.return_value = 1

    result = service.submit_v1_guess(
        GuessRequest(username="player", word="정답"),
        "Bearer token",
    )

    assert participant.is_correct is True
    assert result.isAnswer is True


def test_get_v1_guess_history_rejects_invalid_token():
    # 추측 기록 조회도 참가자 인증이 맞아야 한다.
    service, _db, _games, participants, *_rest = build_guess_service()
    participants.find_by_nickname.return_value = make_participant(session_id="other-token")

    with pytest.raises(UnauthorizedException):
        service.get_v1_guess_history("player", "Bearer token")


def test_get_v1_guess_history_assigns_rank_only_to_best_guess():
    # 최고 점수 추측에만 현재 랭킹을 붙이고 나머지는 -1로 둔다.
    service, _db, _games, participants, _guesses, leaderboard, _vector = build_guess_service()
    participant = make_participant(
        participant_id=5,
        session_id="token",
        best_similarity=0.9,
        closest_word="사랑",
        guesses=[
            make_guess(guess_id=1, participant_id=5, word="사랑", similarity=0.9, word_rank=3),
            make_guess(guess_id=2, participant_id=5, word="바다", similarity=0.7, word_rank=10),
        ],
    )
    participants.find_by_nickname.return_value = participant
    leaderboard.get_rank.return_value = 4

    result = service.get_v1_guess_history("player", "Bearer token")

    assert [item.rank for item in result] == [4, -1]
    assert [item.label for item in result] == ["사랑", "바다"]
