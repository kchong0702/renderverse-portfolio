import asyncio
import secrets
import time
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi.sse import ServerSentEvent
from pydantic import BaseModel, ConfigDict, Field

from src.core.config import EzcareerSettings
from src.core.exceptions import Conflict, NotFound


class _Run(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    """The run's id, the first half of each event id"""

    events: list[str] = Field(default_factory=list)
    """Each event's JSON data, in order"""

    finished_at: float | None = None
    """When the run ended, on the monotonic clock; None while it runs"""

    changed: asyncio.Event = Field(default_factory=asyncio.Event)
    """Set when an event arrives or the run ends, then replaced"""


class InMemoryRunStore:
    def __init__(self, settings: EzcareerSettings):
        """Keep runs in this process only, which suits one ops-api process and tests"""
        self._settings = settings
        """The retry hint and how long a finished run stays resumable"""

        self._runs: dict[str, _Run] = {}
        """Every run kept, by id"""

        self._current: dict[str, str] = {}
        """Each key's latest run id"""

    def _wake(self, run: _Run) -> None:
        """Wake every reader of the run"""
        changed, run.changed = run.changed, asyncio.Event()
        changed.set()

    async def start(self, user_id: UUID, key: str) -> str:
        """Open a new run for key and return its id, the key already naming the user;
        Conflict while key's last run is still going"""
        if (
            last := self._runs.get(self._current.get(key, ""))
        ) and last.finished_at is None:
            raise Conflict("Wait for the current reply to finish")
        if last:
            del self._runs[last.id]
        run = _Run(id=secrets.token_hex(8))
        self._runs[run.id] = run
        self._current[key] = run.id
        return run.id

    async def append(self, run_id: str, seq: int, data: str) -> None:
        """Keep the run's next event and wake its readers"""
        run = self._runs[run_id]
        run.events.append(data)
        self._wake(run)

    async def finish(self, run_id: str) -> None:
        """Mark the run ended and wake its readers"""
        run = self._runs[run_id]
        run.finished_at = time.monotonic()
        self._wake(run)

    async def resume(self, key: str, last_event_id: str | None) -> tuple[str, int]:
        """Key's run a client may resume and how many of its events it has; NotFound
        once it ended over replay_ttl_seconds ago, or for another run's event id"""
        run = self._runs.get(self._current.get(key, ""))
        if run is None or (
            run.finished_at is not None
            and time.monotonic() - run.finished_at >= self._settings.replay_ttl_seconds
        ):
            raise NotFound("There is no reply to resume")
        if not last_event_id:
            return run.id, 0
        run_id, _, seq = last_event_id.partition(":")
        if run_id != run.id or not seq.isdigit():
            raise NotFound("There is no reply to resume")
        return run.id, min(int(seq), len(run.events))

    async def read(self, run_id: str, after: int) -> AsyncIterator[ServerSentEvent]:
        """The run's events after the first `after`, then each new one until it ends"""
        run = self._runs[run_id]
        sent = after
        while True:
            changed = run.changed
            while sent < len(run.events):
                sent += 1
                yield ServerSentEvent(
                    raw_data=run.events[sent - 1],
                    id=f"{run.id}:{sent}",
                    retry=self._settings.stream_retry_ms if sent == 1 else None,
                )
            if run.finished_at is not None:
                return
            await changed.wait()

    async def aclose(self) -> None:
        """Nothing to release"""
