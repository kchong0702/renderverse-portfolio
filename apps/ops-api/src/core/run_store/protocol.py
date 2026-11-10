from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from fastapi.sse import ServerSentEvent


class RunStore(Protocol):
    async def start(self, user_id: UUID, key: str) -> str:
        """Open a new run of the user's for key, such as their chat, and return its id;
        Conflict while key's last run is still going"""
        ...

    async def append(self, run_id: str, seq: int, data: str) -> None:
        """Keep the run's event number seq, its JSON data, and wake its readers"""
        ...

    async def finish(self, run_id: str) -> None:
        """Mark the run ended and wake its readers"""
        ...

    async def resume(self, key: str, last_event_id: str | None) -> tuple[str, int]:
        """Key's run a client may resume and how many of its events the client has,
        from its Last-Event-ID; NotFound when there is none"""
        ...

    def read(self, run_id: str, after: int) -> AsyncIterator[ServerSentEvent]:
        """The run's events after the first `after`, then each new one until it ends"""
        ...

    async def aclose(self) -> None:
        """Release what the store holds open"""
        ...
