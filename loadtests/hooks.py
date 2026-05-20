from __future__ import annotations

import logging

from locust import events

from loadtests.config import (
    DEFAULT_GAME_DURATION_MINUTES,
    DEFAULT_GUESS_INTERVAL_SECONDS,
    DEFAULT_HOST_NICKNAME,
    DEFAULT_PLAYER_PREFIX,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_READY_TIMEOUT_SECONDS,
    DEFAULT_WORD_FILE,
)
from loadtests.state import LOADTEST_STATE, load_words


logger = logging.getLogger(__name__)


@events.init_command_line_parser.add_listener
def add_custom_arguments(parser) -> None:
    parser.add_argument(
        "--target-word",
        env_var="LOCUST_TARGET_WORD",
        default="",
        help="Valid game target word. Defaults to the first loaded word.",
    )
    parser.add_argument(
        "--word-file",
        env_var="LOCUST_WORD_FILE",
        default=str(DEFAULT_WORD_FILE),
        help="Word list for guess traffic.",
    )
    parser.add_argument(
        "--host-nickname",
        env_var="LOCUST_HOST_NICKNAME",
        default=DEFAULT_HOST_NICKNAME,
        help="Nickname used by the single host user.",
    )
    parser.add_argument(
        "--player-prefix",
        env_var="LOCUST_PLAYER_PREFIX",
        default=DEFAULT_PLAYER_PREFIX,
        help="Prefix used for generated player nicknames.",
    )
    parser.add_argument(
        "--game-duration-minutes",
        env_var="LOCUST_GAME_DURATION_MINUTES",
        type=int,
        default=DEFAULT_GAME_DURATION_MINUTES,
        help="Game end time offset in minutes from host creation.",
    )
    parser.add_argument(
        "--guess-interval-seconds",
        env_var="LOCUST_GUESS_INTERVAL_SECONDS",
        type=float,
        default=DEFAULT_GUESS_INTERVAL_SECONDS,
        help="Delay between guess requests for gameplay users.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        env_var="LOCUST_POLL_INTERVAL_SECONDS",
        type=float,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Delay between polling requests for gameplay and poller users.",
    )
    parser.add_argument(
        "--ready-timeout-seconds",
        env_var="LOCUST_READY_TIMEOUT_SECONDS",
        type=float,
        default=DEFAULT_READY_TIMEOUT_SECONDS,
        help="How long non-host users wait for the host to create the game.",
    )


@events.test_start.add_listener
def configure_loadtest_state(environment, **_kwargs) -> None:
    options = environment.parsed_options
    words = load_words(getattr(options, "word_file", ""))

    target_word = getattr(options, "target_word", "").strip() or words[0]

    LOADTEST_STATE.reset()
    LOADTEST_STATE.configure(words, target_word)

    logger.info(
        "Locust load test configured - targetWord=%s words=%d wordFile=%s guessInterval=%.2fs pollInterval=%.2fs",
        LOADTEST_STATE.target_word,
        len(LOADTEST_STATE.words),
        getattr(options, "word_file", ""),
        float(getattr(options, "guess_interval_seconds", DEFAULT_GUESS_INTERVAL_SECONDS)),
        float(getattr(options, "poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS)),
    )


@events.test_stop.add_listener
def log_loadtest_stop(_environment, **_kwargs) -> None:
    logger.info("Locust load test finished - runId=%s", LOADTEST_STATE.run_id)
