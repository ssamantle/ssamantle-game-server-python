from __future__ import annotations

from locust import LoadTestShape


class RampShape(LoadTestShape):
    stages = (
        {"duration": 60, "users": 20, "spawn_rate": 5},
        {"duration": 180, "users": 100, "spawn_rate": 10},
        {"duration": 300, "users": 200, "spawn_rate": 20},
    )

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None
