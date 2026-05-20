from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import logging
import random
import uuid

from gevent.event import Event

from loadtests.config import DEFAULT_TARGET_WORD, DEFAULT_WORDS


logger = logging.getLogger(__name__)


def load_words(path: str | Path | None) -> tuple[str, ...]:
    if not path:
        return DEFAULT_WORDS

    word_file = Path(path)
    if not word_file.exists():
        logger.warning(
            "Word file not found for Locust load test; using built-in defaults: %s",
            word_file,
        )
        return DEFAULT_WORDS

    words = tuple(
        line.strip()
        for line in word_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if not words:
        logger.warning(
            "Word file is empty for Locust load test; using built-in defaults: %s",
            word_file,
        )
        return DEFAULT_WORDS
    return words


@dataclass
class LoadTestState:
    ready: Event = field(default_factory=Event)
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    words: tuple[str, ...] = field(default_factory=lambda: DEFAULT_WORDS)
    target_word: str = DEFAULT_TARGET_WORD
    host_session_id: str | None = None

    def reset(self) -> None:
        self.ready.clear()
        self.run_id = uuid.uuid4().hex[:8]
        self.words = DEFAULT_WORDS
        self.target_word = DEFAULT_TARGET_WORD
        self.host_session_id = None

    def configure(self, words: tuple[str, ...], target_word: str) -> None:
        self.words = words or DEFAULT_WORDS
        self.target_word = target_word or self.words[0]

    def next_player_name(self, prefix: str) -> str:
        suffix = uuid.uuid4().hex[:6]
        return f"{prefix}-{self.run_id}-{suffix}"

    def pick_word(self, rng: random.Random) -> str:
        return rng.choice(self.words)


LOADTEST_STATE = LoadTestState()
