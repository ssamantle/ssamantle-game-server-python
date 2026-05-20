from __future__ import annotations

from locust import constant

from loadtests import hooks as _hooks  # noqa: F401
from loadtests.users.host import HostUser
from loadtests.users.player import PlayerUser


class SmokeHostUser(HostUser):
    fixed_count = 1
    wait_time = constant(600)


class SmokePlayerUser(PlayerUser):
    fixed_count = 2
