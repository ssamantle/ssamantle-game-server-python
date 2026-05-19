from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
import redis

from app.core.config import get_settings

settings = get_settings()

# ================================================================

sqlite_engine = create_async_engine(
    settings.vector_db_path,
    pool_timeout=10,
)
sqlite_session = async_sessionmaker(
    sqlite_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_sqlite_db() -> AsyncGenerator[AsyncSession, None]:
    async with sqlite_session() as session:
        yield session


# ================================================================

pg_engine = create_async_engine(
    settings.database_url,
    pool_size=50,
    max_overflow=50,
    pool_timeout=60,
)
pg_session = async_sessionmaker(
    pg_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_pg_db() -> AsyncGenerator[AsyncSession, None]:
    async with pg_session() as session:
        yield session


def init_pg_db():
    """앱 시작 시 테이블 생성"""
    from app.repository.models import GameBase  # noqa: F401

    GameBase.metadata.create_all(bind=pg_engine)


# ================================================================


async def get_redis() -> AsyncGenerator[redis.asyncio.Redis, None]:
    r = redis.asyncio.from_url(settings.redis_url, decode_responses=True)
    try:
        yield r
    finally:
        await r.close()
