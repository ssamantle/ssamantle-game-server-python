import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


os.environ["DEBUG"] = "false"
os.environ["DATABASE_URL"] = (
    "postgresql+psycopg2://user:password@localhost:5432/test_db"
)
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["SECRET"] = "test-secret"


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def make_game(
    *,
    game_id: int = 1,
    hostname: str = "host",
    host_session_id: str = "host-token",
    target_word: str = "사랑",
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
):
    from app.repository.models import Game

    return Game(
        id=game_id,
        hostname=hostname,
        host_session_id=host_session_id,
        target_word=target_word,
        started_at=started_at,
        ended_at=ended_at,
    )


def make_participant(
    *,
    participant_id: int = 1,
    game_id: int = 1,
    nickname: str = "player",
    session_id: str = "player-token",
    best_similarity: float = 0.0,
    closest_word: str | None = None,
    is_correct: bool = False,
    guesses: list | None = None,
):
    from app.repository.models import Participant

    participant = Participant(
        id=participant_id,
        game_id=game_id,
        nickname=nickname,
        session_id=session_id,
        best_similarity=best_similarity,
        closest_word=closest_word,
        is_correct=is_correct,
    )
    participant.guesses = guesses or []
    return participant


def make_guess(
    *,
    guess_id: int = 1,
    participant_id: int = 1,
    word: str = "사랑",
    similarity: float = 0.5,
    word_rank: int = 100,
    is_answer: bool = False,
    submitted_at: datetime | None = None,
):
    from app.repository.models import GuessHistory

    return GuessHistory(
        id=guess_id,
        participant_id=participant_id,
        word=word,
        similarity=similarity,
        word_rank=word_rank,
        is_answer=is_answer,
        submitted_at=submitted_at or (utc_now() - timedelta(seconds=1)),
    )
