import asyncio
import os
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.auth.models import User
from src.core.config import DatabaseSettings, EzcareerSettings
from src.core.exceptions import Conflict, NotFound
from src.core.stores import InMemoryRunStore, PostgresRunStore, RunStore
from src.db.session import create_session_factory

DATABASE_URL = os.environ.get("OPS_API_TEST_DATABASE_URL", "")
SETTINGS = EzcareerSettings(stream_retry_ms=2000, replay_ttl_seconds=60)

needs_postgres = [
    pytest.mark.postgres,
    pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set"),
]


async def _postgres(settings: EzcareerSettings) -> AsyncIterator[tuple[UUID, list]]:
    """A user in the test database, and a factory of Postgres stores on it that
    share nothing but the database, like two ops-api processes"""
    engine = create_async_engine(DATABASE_URL)
    factory = create_session_factory(engine)
    user_id = uuid4()
    async with factory() as session, session.begin():
        session.add(User(id=user_id, email=f"{user_id}@example.com"))
    stores: list[PostgresRunStore] = []

    def store() -> PostgresRunStore:
        stores.append(
            PostgresRunStore(
                create_session_factory(create_async_engine(DATABASE_URL)),
                DatabaseSettings(url=DATABASE_URL),
                settings,
            )
        )
        return stores[-1]

    yield user_id, [store]
    for each in stores:
        await each.aclose()
    async with factory() as session, session.begin():
        await session.execute(delete(User).where(User.id == user_id))
    await engine.dispose()


@pytest.fixture(
    params=[
        pytest.param("memory"),
        pytest.param("postgres", marks=needs_postgres),
    ]
)
async def store(request) -> AsyncIterator[tuple[UUID, RunStore]]:
    if request.param == "memory":
        yield uuid4(), InMemoryRunStore(SETTINGS)
        return
    async for user_id, [make] in _postgres(SETTINGS):
        yield user_id, make()


async def _read(store: RunStore, run_id: str, after: int = 0) -> list[tuple[str, str]]:
    return [
        (event.id or "", event.raw_data or "")
        async for event in store.read(run_id, after)
    ]


async def test_a_run_is_read_back_with_ids_and_a_retry_hint_then_ends(store):
    user_id, runs = store
    run_id = await runs.create(user_id, "chat-1")
    await runs.append(run_id, 1, '{"status":"started"}')
    await runs.append(run_id, 2, '{"status":"completed"}')
    await runs.finish(run_id)

    events = [event async for event in runs.read(run_id, 0)]

    assert [(e.id, e.raw_data) for e in events] == [
        (f"{run_id}:1", '{"status":"started"}'),
        (f"{run_id}:2", '{"status":"completed"}'),
    ]
    assert [e.retry for e in events] == [2000, None]


async def test_a_key_takes_one_run_at_a_time(store):
    user_id, runs = store
    first = await runs.create(user_id, "chat-1")

    with pytest.raises(Conflict):
        await runs.create(user_id, "chat-1")
    await runs.finish(first)
    second = await runs.create(user_id, "chat-1")

    assert second != first
    assert await runs.resume("chat-1", None) == (second, 0)


async def test_a_reader_follows_events_written_after_it_started(store):
    user_id, runs = store
    run_id = await runs.create(user_id, "chat-1")
    reading = asyncio.create_task(_read(runs, run_id))
    await asyncio.sleep(0.2)

    await runs.append(run_id, 1, '{"n":1}')
    await runs.finish(run_id)

    assert await asyncio.wait_for(reading, timeout=3) == [(f"{run_id}:1", '{"n":1}')]


async def test_resume_skips_what_the_client_has_and_refuses_other_runs(store):
    user_id, runs = store
    run_id = await runs.create(user_id, "chat-1")
    for seq in (1, 2, 3):
        await runs.append(run_id, seq, f'{{"n":{seq}}}')
    await runs.finish(run_id)

    assert await runs.resume("chat-1", f"{run_id}:2") == (run_id, 2)
    assert await _read(runs, run_id, 2) == [(f"{run_id}:3", '{"n":3}')]
    with pytest.raises(NotFound):
        await runs.resume("chat-1", "0123456789abcdef:1")
    with pytest.raises(NotFound):
        await runs.resume("chat-2", None)


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_another_process_follows_a_run_live():
    async for user_id, [make] in _postgres(SETTINGS):
        writer, reader = make(), make()
        run_id = await writer.create(user_id, "chat-1")
        reading = asyncio.create_task(_read(reader, run_id))
        await asyncio.sleep(0.3)

        await writer.append(run_id, 1, '{"n":1}')
        await asyncio.sleep(0.3)
        await writer.append(run_id, 2, '{"n":2}')
        await writer.finish(run_id)

        assert await asyncio.wait_for(reading, timeout=2) == [
            (f"{run_id}:1", '{"n":1}'),
            (f"{run_id}:2", '{"n":2}'),
        ]
        assert await reader.resume("chat-1", f"{run_id}:1") == (run_id, 1)


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_a_run_whose_writer_went_silent_ends_and_frees_its_key():
    settings = EzcareerSettings(run_timeout_seconds=1)
    async for user_id, [make] in _postgres(settings):
        runs = make()
        run_id = await runs.create(user_id, "chat-1")
        await runs.append(run_id, 1, '{"n":1}')
        await asyncio.sleep(1.2)

        assert await asyncio.wait_for(_read(runs, run_id), timeout=3) == [
            (f"{run_id}:1", '{"n":1}')
        ]
        with pytest.raises(NotFound):
            await runs.resume("chat-1", None)
        assert await runs.create(user_id, "chat-1") != run_id
