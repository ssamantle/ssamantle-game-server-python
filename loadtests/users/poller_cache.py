from __future__ import annotations

from locust import task

from loadtests.users.base import BaseGameUser


class CachePollerUser(BaseGameUser):
    abstract = True

    def on_start(self) -> None:
        super().on_start()
        self.wait_for_game_ready()

    def wait_time(self) -> float:
        return max(0.0, float(getattr(self.options, "poll_interval_seconds", 3.0)))

    @task
    def poll_game(self) -> None:
        self.request_json("GET", "/api/v1/games/polling")
