from __future__ import annotations

import os
from functools import lru_cache
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

DEFAULT_DATABASE_URL = "postgresql+asyncpg://training:training@localhost:5432/training"
ASYNC_DATABASE_SCHEMES = ("postgresql+asyncpg://", "sqlite+aiosqlite://")


def get_database_url() -> str:
    """Return the configured database URL, defaulting to local Postgres."""

    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def is_async_database_url(database_url: str) -> bool:
    """Report whether *database_url* uses an async SQLAlchemy driver."""

    return database_url.startswith(ASYNC_DATABASE_SCHEMES)


def create_async_db_engine(database_url: str | None = None) -> AsyncEngine:
    """Build the runtime async engine used by the API service."""

    url = database_url or get_database_url()
    if not is_async_database_url(url):
        raise ValueError("DATABASE_URL must use an async SQLAlchemy driver such as postgresql+asyncpg://")

    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_async_engine(url, pool_pre_ping=True, connect_args=connect_args)


@lru_cache(maxsize=1)
def get_async_engine() -> AsyncEngine:
    return create_async_db_engine()


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_async_engine(), class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session for future DB-backed routes."""

    async with get_session_factory()() as session:
        yield session
