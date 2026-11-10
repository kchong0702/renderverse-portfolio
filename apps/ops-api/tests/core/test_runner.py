import asyncio
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from pydantic import BaseModel

from src.core.config import EzcareerSettings
from src.core.exceptions import Conflict, NotFound
from src.core.runner import Runner
from src.core.stores import InMemoryRunStore

SETTINGS = EzcareerSettings(stream_retry_ms=2000, replay_ttl_seconds=60)


class Event(BaseModel):
    n: int


async def _events(*numbers: int) -> AsyncIterator[BaseModel]:
    for n in numbers:
        yield Event(n=n)


async def _until(release: asyncio.Event) -> AsyncIterator[BaseModel]:
    await release.wait()
    yield Event(n=0)


def _id(event: str) -> str:
    return next(line[4:] for line in event.splitlines() if line.startswith("id: "))


async def test_a_run_streams_each_event_with_its_id_and_a_retry_hint_first():
    runner = Runner(InMemoryRunStore(SETTINGS), SETTINGS)

    events = [
        e async for e in await runner.start_task(uuid4(), "chat-1", _events(1, 2))
    ]

    run_id = _id(events[0]).partition(":")[0]
    assert events == [
        f'data: {{"n":1}}\nid: {run_id}:1\nretry: 2000\n\n',
        f'data: {{"n":2}}\nid: {run_id}:2\n\n',
    ]


async def test_a_key_runs_one_turn_at_a_time():
    runner = Runner(InMemoryRunStore(SETTINGS), SETTINGS)
    release = asyncio.Event()
    await runner.start_task(uuid4(), "chat-1", _until(release))

    with pytest.raises(Conflict):
        await runner.start_task(uuid4(), "chat-1", _events(1))
    release.set()


async def test_resume_skips_what_the_client_saw_and_refuses_another_runs_id():
    runner = Runner(InMemoryRunStore(SETTINGS), SETTINGS)
    events = [
        e async for e in await runner.start_task(uuid4(), "chat-1", _events(1, 2, 3))
    ]

    resumed = [e async for e in await runner.resume("chat-1", _id(events[1]))]

    assert resumed == [events[2]]
    with pytest.raises(NotFound):
        await runner.resume("chat-1", "0123456789abcdef:1")
    with pytest.raises(NotFound):
        await runner.resume("chat-1", "not-an-id")
    with pytest.raises(NotFound):
        await runner.resume("chat-2", None)
