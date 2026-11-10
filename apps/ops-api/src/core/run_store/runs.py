import asyncio
from collections.abc import AsyncIterator
from uuid import UUID

from pydantic import BaseModel

from src.core.run_store.protocol import RunStore

_PUMPS: set[asyncio.Task[None]] = set()
"""Every run still being written, kept so none is garbage collected mid-run"""


async def _pump(store: RunStore, run_id: str, events: AsyncIterator[BaseModel]) -> None:
    """Write each of the run's events to the store, then mark it finished"""
    seq = 0
    try:
        async for event in events:
            seq += 1
            await store.append(run_id, seq, event.model_dump_json())
    finally:
        await store.finish(run_id)


async def start_run(
    store: RunStore, user_id: UUID, key: str, events: AsyncIterator[BaseModel]
) -> str:
    """Open a run of the user's for key and write its events to the store in the
    background, whoever reads it; Conflict while key's last run is still going"""
    run_id = await store.start(user_id, key)
    task = asyncio.create_task(_pump(store, run_id, events))
    _PUMPS.add(task)
    task.add_done_callback(_PUMPS.discard)
    return run_id
