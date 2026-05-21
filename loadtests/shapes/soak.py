from __future__ import annotations

from locust import LoadTestShape


class SoakShape(LoadTestShape):
    stages = (
        {"duration": 120, "users": 50, "spawn_rate": 5},
        {"duration": 1800, "users": 50, "spawn_rate": 1},
    )

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None
