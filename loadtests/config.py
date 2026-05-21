from __future__ import annotations

from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
REPORTS_DIR = PACKAGE_DIR / "reports"

DEFAULT_TARGET_WORD = "사랑"
DEFAULT_HOST_NICKNAME = "loadtest-host"
DEFAULT_PLAYER_PREFIX = "player"
DEFAULT_WORD_FILE = DATA_DIR / "words_smoke.txt"

DEFAULT_WORDS = (
    "사랑",
    "행복",
    "마음",
    "사람",
    "친구",
    "가족",
    "학교",
    "음악",
    "책",
    "바다",
    "하늘",
    "도시",
)

DEFAULT_GAME_DURATION_MINUTES = 30
DEFAULT_GUESS_INTERVAL_SECONDS = 2.0
DEFAULT_POLL_INTERVAL_SECONDS = 3.0
DEFAULT_READY_TIMEOUT_SECONDS = 30.0
