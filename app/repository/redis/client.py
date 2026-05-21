import redis

from app.core.config import get_settings

settings = get_settings()


def get_redis_client() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)
