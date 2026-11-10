import asyncio
import secrets
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from uuid import UUID

from src.core.config import EzcareerSettings
from src.core.exceptions import Conflict, NotFound


@dataclass
class _Run:
    id: str
    """The run's id"""

    events: list[str] = field(default_factory=list)
    """Each event's JSON data, in order"""

    finished_at: float | None = None
    """When the run ended, on the monotonic clock; None while it runs"""

    changed: asyncio.Event = field(default_factory=asyncio.Event)
    """Set when an event arrives or the run ends, then replaced"""


class InMemoryRunStore:
    def __init__(self, settings: EzcareerSettings):
        """Keep runs in this process only, which suits one ops-api process and tests"""
        self._settings = settings
        """How long a finished run stays resumable"""

        self._runs: dict[str, _Run] = {}
        """Every run kept, by id"""

        self._current: dict[str, str] = {}
        """Each key's latest run id"""

    def _wake(self, run: _Run) -> None:
        """Wake every reader of the run"""
        changed, run.changed = run.changed, asyncio.Event()
        changed.set()

    async def create(self, user_id: UUID, key: str) -> str:
        """Open a new run for key and return its id; Conflict while key's last run is
        still going"""
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

    async def latest(self, key: str) -> tuple[str, int]:
        """Key's run a client may still read and how many events it has; NotFound once
        it ended over replay_ttl_seconds ago"""
        run = self._runs.get(self._current.get(key, ""))
        if run is None or (
            run.finished_at is not None
            and time.monotonic() - run.finished_at >= self._settings.replay_ttl_seconds
        ):
            raise NotFound("There is no reply to resume")
        return run.id, len(run.events)

    async def read(self, run_id: str, after: int) -> AsyncIterator[str]:
        """The JSON data of the run's events after the first `after`, then of each new
        one until it ends"""
        run = self._runs[run_id]
        sent = after
        while True:
            changed = run.changed
            while sent < len(run.events):
                sent += 1
                yield run.events[sent - 1]
            if run.finished_at is not None:
                return
            await changed.wait()

    async def aclose(self) -> None:
        """Nothing to release"""


__all__ = ["InMemoryRunStore"]
