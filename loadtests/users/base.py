from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import random
import time
from typing import Any, Iterable

import gevent
from locust import HttpUser, constant
from locust.exception import StopUser

from loadtests.state import LOADTEST_STATE


logger = logging.getLogger(__name__)


class BaseGameUser(HttpUser):
    abstract = True
    wait_time = constant(1)

    def on_start(self) -> None:
        self.rng = random.Random()

    @property
    def options(self):
        return self.environment.parsed_options

    def request_json(
        self,
        method: str,
        path: str,
        *,
        expected_statuses: Iterable[int] = (200,),
        name: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any] | None:
        expected = tuple(expected_statuses)
        request_name = name or f"{method.upper()} {path}"

        with self.client.request(
            method,
            path,
            name=request_name,
            catch_response=True,
            **kwargs,
        ) as response:
            if response.status_code not in expected:
                body = response.text[:200]
                response.failure(
                    f"Unexpected status {response.status_code}, expected {expected}, body={body!r}"
                )
                return None

            try:
                return response.json()
            except ValueError:
                response.failure("Response body was not valid JSON")
                return None

    def build_game_payload(self) -> dict[str, str]:
        now = datetime.now(timezone.utc)
        start_at = now - timedelta(seconds=5)
        end_at = now + timedelta(
            minutes=max(1, int(getattr(self.options, "game_duration_minutes", 30)))
        )
        return {
            "hostname": getattr(self.options, "host_nickname", "loadtest-host"),
            "targetWord": LOADTEST_STATE.target_word,
            "startTime": start_at.isoformat(),
            "endTime": end_at.isoformat(),
        }

    def wait_for_game_ready(self) -> None:
        timeout = max(
            0.0,
            float(getattr(self.options, "ready_timeout_seconds", 30.0)),
        )
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            if LOADTEST_STATE.ready.is_set():
                return
            gevent.sleep(0.25)

        raise StopUser("Timed out waiting for host to create the game")

    @staticmethod
    def authorization_headers(session_id: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {session_id}"}

    def pick_word(self) -> str:
        return LOADTEST_STATE.pick_word(self.rng)
