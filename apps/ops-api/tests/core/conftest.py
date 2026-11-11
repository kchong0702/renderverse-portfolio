import os
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.core.auth.models import User
from src.core.config import DatabaseSettings, EzcareerSettings
from src.core.stores import PostgresRunStore
from src.db.session import create_session_factory

DATABASE_URL = os.environ.get("OPS_API_TEST_DATABASE_URL", "")

needs_postgres = [
    pytest.mark.postgres,
    pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set"),
]


def postgres_store(engine: AsyncEngine, settings: EzcareerSettings) -> PostgresRunStore:
    """A Postgres store with a listener of its own, like one more ops-api process"""
    return PostgresRunStore(
        create_session_factory(engine),
        DatabaseSettings(url=SecretStr(DATABASE_URL)),
        settings,
    )


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """An engine on the test database, disposed after the test"""
    engine = create_async_engine(DATABASE_URL)
    yield engine
    await engine.dispose()


@pytest.fixture
async def postgres_user(engine: AsyncEngine) -> AsyncIterator[UUID]:
    """A user in the test database, deleted with their runs after the test"""
    factory = create_session_factory(engine)
    user_id = uuid4()
    async with factory() as session, session.begin():
        session.add(User(id=user_id, email=f"{user_id}@example.com"))
    yield user_id
    async with factory() as session, session.begin():
        await session.execute(delete(User).where(User.id == user_id))
