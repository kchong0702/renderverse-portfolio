import asyncio
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi.sse import format_sse_event
from pydantic import BaseModel

from src.core.exceptions import NotFound
from src.core.stores import RunStore


class Runner:
    def __init__(self, store: RunStore, retry_ms: int):
        """Run agent turns in the background, writing their events to store, so any
        ops-api process can stream them"""
        self._store = store
        """Where each run's events are kept"""

        self._retry_ms = retry_ms
        """The retry hint each stream starts with"""

        self._tasks: set[asyncio.Task[None]] = set()
        """Every run still writing, kept so none is garbage collected mid-run"""

    async def _write(self, run_id: str, events: AsyncIterator[BaseModel]) -> None:
        """Write each of the run's events to the store, then mark it finished"""
        seq = 0
        try:
            async for event in events:
                seq += 1
                await self._store.append(run_id, seq, event.model_dump_json())
        finally:
            await self._store.finish(run_id)

    async def _read(self, run_id: str, after: int) -> AsyncIterator[str]:
        """The run's events after the first `after` as server-sent events with run:seq
        ids, then each new one until it ends"""
        seq = after
        async for data in self._store.read(run_id, after):
            seq += 1
            yield format_sse_event(
                data_str=data,
                id=f"{run_id}:{seq}",
                retry=self._retry_ms if seq == 1 else None,
            ).decode()

    async def start_task(
        self, user_id: UUID, key: str, events: AsyncIterator[BaseModel]
    ) -> AsyncIterator[str]:
        """Run events in the background as key's new run and stream it from the start;
        Conflict while key's last run is still going"""
        run_id = await self._store.create(user_id, key)
        task = asyncio.create_task(self._write(run_id, events))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return self._read(run_id, 0)

    async def resume(self, key: str, last_event_id: str | None) -> AsyncIterator[str]:
        """Stream key's run after the Last-Event-ID the client last saw; NotFound when
        there is none to resume or the id is another run's"""
        run_id, count = await self._store.latest(key)
        if not last_event_id:
            return self._read(run_id, 0)
        seen_run_id, _, seq = last_event_id.partition(":")
        if seen_run_id != run_id or not seq.isdigit():
            raise NotFound("There is no reply to resume")
        return self._read(run_id, min(int(seq), count))

    async def aclose(self) -> None:
        """Cancel every run still writing and wait until each is marked finished"""
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)


__all__ = ["Runner"]
