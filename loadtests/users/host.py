from __future__ import annotations

import gevent
from locust import task
from locust.exception import StopUser

from loadtests.state import LOADTEST_STATE
from loadtests.users.base import BaseGameUser


class HostUser(BaseGameUser):
    abstract = True

    def on_start(self) -> None:
        super().on_start()
        payload = self.build_game_payload()
        result = self.request_json(
            "POST",
            "/api/v1/games",
            expected_statuses=(201,),
            json=payload,
        )
        if not isinstance(result, dict):
            raise StopUser("Host failed to create the game")

        session_id = result.get("sessionId")
        if not session_id:
            raise StopUser("Host create game response did not include sessionId")

        LOADTEST_STATE.host_session_id = str(session_id)
        LOADTEST_STATE.ready.set()

    @task
    def idle(self) -> None:
        gevent.sleep(60)
