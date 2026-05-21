from datetime import timedelta

from app.utils import build_submission_detail, get_best_guess, get_latest_guess
from tests.conftest import make_guess, make_participant, utc_now


def test_build_submission_detail_returns_none_when_required_values_are_missing():
    # 단어 또는 유사도가 없으면 응답 객체를 만들지 않는다.
    assert build_submission_detail(None, 0.5) is None
    assert build_submission_detail("사랑", None) is None


def test_build_submission_detail_rounds_similarity():
    # 응답에 들어가는 유사도는 소수 넷째 자리로 맞춘다.
    detail = build_submission_detail("사랑", 0.87654, utc_now())
    assert detail.label == "사랑"
    assert detail.similarity == 0.8765


def test_get_latest_guess_returns_most_recent_guess():
    # 제출 시간이 가장 늦은 추측을 최신 기록으로 선택한다.
    participant = make_participant(
        guesses=[
            make_guess(guess_id=1, submitted_at=utc_now() - timedelta(seconds=10)),
            make_guess(guess_id=2, submitted_at=utc_now()),
        ],
    )

    latest = get_latest_guess(participant)

    assert latest.id == 2


def test_get_best_guess_prefers_closest_word_among_best_score_ties():
    # 최고 점수가 같으면 closest_word와 일치하는 추측을 우선 선택한다.
    participant = make_participant(
        best_similarity=0.9,
        closest_word="사랑",
        guesses=[
            make_guess(guess_id=1, word="가족", similarity=0.9, submitted_at=utc_now() - timedelta(seconds=5)),
            make_guess(guess_id=2, word="사랑", similarity=0.9, submitted_at=utc_now()),
        ],
    )

    best = get_best_guess(participant)

    assert best.id == 2
