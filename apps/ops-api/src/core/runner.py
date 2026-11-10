import asyncio
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi.sse import format_sse_event
from pydantic import BaseModel

from src.core.stores import RunStore


class Runner:
    def __init__(self, store: RunStore):
        """Run tasks in the background, writing each one's events to store, so any
        ops-api process can stream them"""
        self._store = store
        """Where each task's events are kept"""

        self._tasks: set[asyncio.Task[None]] = set()
        """Every task still running, kept so none is garbage collected mid-run"""

    async def _write(self, run_id: str, events: AsyncIterator[BaseModel]) -> None:
        """Write each of the task's events to the store, then mark it finished"""
        seq = 0
        try:
            async for event in events:
                seq += 1
                await self._store.append(run_id, seq, event.model_dump_json())
        finally:
            await self._store.finish(run_id)

    async def start_task(
        self, user_id: UUID, key: str, events: AsyncIterator[BaseModel]
    ) -> str:
        """Start a task of the user's for key in the background and return its run
        id; Conflict while key's last task is still going"""
        run_id = await self._store.start(user_id, key)
        task = asyncio.create_task(self._write(run_id, events))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return run_id

    async def read(self, run_id: str, after: int) -> AsyncIterator[str]:
        """The run's events after the first `after` as server-sent events, then each
        new one until it ends"""
        async for event in self._store.read(run_id, after):
            yield format_sse_event(
                data_str=event.raw_data, id=event.id, retry=event.retry
            ).decode()

    async def resume(self, key: str, last_event_id: str | None) -> AsyncIterator[str]:
        """Key's run after the Last-Event-ID the client last saw, as server-sent
        events; NotFound when there is none to resume"""
        run_id, after = await self._store.resume(key, last_event_id)
        return self.read(run_id, after)
