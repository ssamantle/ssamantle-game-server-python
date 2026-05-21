from __future__ import annotations

from locust import constant

from loadtests import hooks as _hooks  # noqa: F401
from loadtests.users.host import HostUser
from loadtests.users.player import PlayerUser
from loadtests.users.poller_cache import CachePollerUser


class PollingCacheHostUser(HostUser):
    fixed_count = 1
    wait_time = constant(600)


class PollingCachePlayerUser(PlayerUser):
    weight = 1


class PollingCacheUser(CachePollerUser):
    weight = 3
