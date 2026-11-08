from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import DatabaseSettings


def create_engine(settings: DatabaseSettings) -> AsyncEngine:
    """Create the async engine; Supabase's session pooler allows prepared statements"""
    return create_async_engine(
        settings.url.get_secret_value(),
        pool_size=settings.pool_size,
        pool_pre_ping=True,
        echo=settings.echo,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """One session per request, committed on success and rolled back on error"""
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request, from the factory the app keeps on its state"""
    async for session in session_scope(request.app.state.session_factory):
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]

__all__ = [
    "SessionDep",
    "create_engine",
    "create_session_factory",
    "get_session",
    "session_scope",
]
