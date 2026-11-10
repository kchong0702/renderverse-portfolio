from __future__ import annotations

import asyncio
import secrets
import time
from collections.abc import AsyncIterator

from fastapi.sse import ServerSentEvent
from pydantic import BaseModel


class RunStream:
    def __init__(self, events: AsyncIterator[BaseModel], retry_ms: int):
        """Read a run's events in the background, buffering each so a client that
        lost its connection can resume"""
        self.id = secrets.token_hex(8)
        self._retry_ms = retry_ms
        self._events: list[ServerSentEvent] = []
        self._changed = asyncio.Event()
        self.finished_at: float | None = None
        self.task = asyncio.create_task(self._pump(events))

    @property
    def done(self) -> bool:
        """Whether the run has ended and every event is buffered"""
        return self.finished_at is not None

    def _notify(self) -> None:
        """Wake every open stream"""
        changed, self._changed = self._changed, asyncio.Event()
        changed.set()

    async def _pump(self, events: AsyncIterator[BaseModel]) -> None:
        """Buffer each event with the id <run id>:<seq>, then mark the run done"""
        try:
            async for event in events:
                seq = len(self._events) + 1
                self._events.append(
                    ServerSentEvent(
                        data=event,
                        id=f"{self.id}:{seq}",
                        retry=self._retry_ms if seq == 1 else None,
                    )
                )
                self._notify()
        finally:
            self.finished_at = time.monotonic()
            self._notify()

    def resumable(self, replay_ttl_seconds: float) -> bool:
        """Whether a client may still resume this run"""
        return (
            self.finished_at is None
            or time.monotonic() - self.finished_at < replay_ttl_seconds
        )

    def resume_point(self, last_event_id: str | None) -> int | None:
        """How many events a reconnecting client already has, from its Last-Event-ID;
        0 without one, None when the id is from another run or malformed"""
        if not last_event_id:
            return 0
        run_id, _, seq = last_event_id.partition(":")
        if run_id != self.id or not seq.isdigit():
            return None
        return min(int(seq), len(self._events))

    async def stream(self, after: int = 0) -> AsyncIterator[ServerSentEvent]:
        """Send one client the events after the first `after`, then each new one
        until the run ends"""
        sent = after
        while True:
            changed = self._changed
            while sent < len(self._events):
                yield self._events[sent]
                sent += 1
            if self.done:
                return
            await changed.wait()


__all__ = ["RunStream"]
