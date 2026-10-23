from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.models import Base


def _ensure_sqlite_dir(url: str) -> None:
    if "sqlite" not in url:
        return
    if "///" not in url:
        return
    raw_path = url.split("///", 1)[1]
    path = Path(raw_path)
    if path.parent.as_posix() not in {"", "."}:
        path.parent.mkdir(parents=True, exist_ok=True)


def create_engine(settings: Settings):
    _ensure_sqlite_dir(settings.database_url)
    connect_args = {}
    kwargs = {"future": True}
    if "sqlite" in settings.database_url:
        connect_args["check_same_thread"] = False
        if ":memory:" in settings.database_url:
            kwargs["poolclass"] = StaticPool
    return create_async_engine(settings.database_url, connect_args=connect_args, **kwargs)


def session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session_dep(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session
