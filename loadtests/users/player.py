from __future__ import annotations

import time

import gevent
from locust import constant, task
from locust.exception import StopUser

from loadtests.state import LOADTEST_STATE
from loadtests.users.base import BaseGameUser


class PlayerUser(BaseGameUser):
    abstract = True
    wait_time = constant(0)

    def on_start(self) -> None:
        super().on_start()
        self.wait_for_game_ready()

        player_prefix = getattr(self.options, "player_prefix", "player")
        self.username = LOADTEST_STATE.next_player_name(player_prefix)

        result = self.request_json(
            "POST",
            "/api/v1/games/join",
            json={"nickname": self.username},
        )
        if not isinstance(result, dict):
            raise StopUser("Player failed to join the game")

        session_id = result.get("sessionId")
        if not session_id:
            raise StopUser("Join game response did not include sessionId")

        self.session_id = str(session_id)
        now = time.monotonic()
        self.next_guess_at = now
        self.next_poll_at = now

    def guess_interval_seconds(self) -> float:
        return max(
            0.0,
            float(getattr(self.options, "guess_interval_seconds", 2.0)),
        )

    def poll_interval_seconds(self) -> float:
        return max(
            0.0,
            float(getattr(self.options, "poll_interval_seconds", 3.0)),
        )

    def submit_guess(self) -> None:
        self.request_json(
            "POST",
            "/api/v1/games/guess",
            headers=self.authorization_headers(self.session_id),
            json={
                "username": self.username,
                "word": self.pick_word(),
            },
        )

    def poll_game(self) -> None:
        self.request_json("GET", "/api/v1/games/polling")

    @task
    def play(self) -> None:
        next_due_at = min(self.next_guess_at, self.next_poll_at)
        now = time.monotonic()
        if now < next_due_at:
            gevent.sleep(next_due_at - now)
            now = time.monotonic()

        if now >= self.next_guess_at:
            self.submit_guess()
            self.next_guess_at = now + self.guess_interval_seconds()

        if now >= self.next_poll_at:
            self.poll_game()
            self.next_poll_at = now + self.poll_interval_seconds()
