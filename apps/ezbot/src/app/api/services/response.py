from __future__ import annotations

import asyncio
import secrets
import time
from collections.abc import AsyncIterator, Callable

from fastapi.sse import ServerSentEvent

from src.app.api.schemas.chat import ResponseEvent


class Response:
    def __init__(
        self,
        retry_ms: int,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.id = secrets.token_hex(8)
        self._retry_ms = retry_ms
        self._clock = clock
        self._events: list[ServerSentEvent] = []
        self._changed = asyncio.Event()
        self.task: asyncio.Task[None] | None = None
        self.finished_at: float | None = None

    @property
    def done(self) -> bool:
        return self.finished_at is not None

    def publish(self, data: ResponseEvent) -> None:
        """Buffer an event, named after its `type`, and wake every open stream"""
        seq = len(self._events) + 1
        self._events.append(
            ServerSentEvent(
                event=data.type,
                data=data,
                id=f"{self.id}:{seq}",
                retry=self._retry_ms if seq == 1 else None,
            )
        )
        self._notify()

    def finish(self) -> None:
        """Mark the response complete; open streams drain the buffer and end"""
        if self.finished_at is None:
            self.finished_at = self._clock()
            self._notify()

    def stop(self) -> None:
        """Cancel the generation; it publishes its own closing events"""
        if self.task is not None and not self.task.done():
            self.task.cancel()

    def _notify(self) -> None:
        changed, self._changed = self._changed, asyncio.Event()
        changed.set()

    def resumable(self, replay_ttl_s: float) -> bool:
        """Whether a client may still resume this response"""
        return (
            self.finished_at is None or self._clock() - self.finished_at < replay_ttl_s
        )

    def resume_point(self, last_event_id: str | None) -> int | None:
        """How many events a reconnecting client already has, read from its
        `Last-Event-ID` header (`<response_id>:<seq>`).

        Returns 0 when there is no header, so the client gets the whole response,
        `seq` (capped at the events sent so far) when the id is from this response,
        and None when it is from another response or malformed.
        """
        if not last_event_id:
            return 0
        response_id, _, seq = last_event_id.partition(":")
        if response_id != self.id or not seq.isdigit():
            return None
        return min(int(seq), len(self._events))

    async def stream(self, after: int = 0) -> AsyncIterator[ServerSentEvent]:
        """Send this response's events to one client connection.

        Skips the first `after` events, which the client already has (see
        `resume_point`), sends the rest of those published so far, then waits
        for and sends each new one until the response finishes.
        """
        sent = after
        while True:
            changed = self._changed
            while sent < len(self._events):
                yield self._events[sent]
                sent += 1
            if self.done:
                return
            await changed.wait()


__all__ = ["Response"]
