from __future__ import annotations

from locust import LoadTestShape


class SmokeShape(LoadTestShape):
    stages = (
        {"duration": 15, "users": 1, "spawn_rate": 1},
        {"duration": 45, "users": 3, "spawn_rate": 2},
        {"duration": 90, "users": 5, "spawn_rate": 2},
    )

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None
