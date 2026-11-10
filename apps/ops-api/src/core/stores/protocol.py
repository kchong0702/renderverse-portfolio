from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID


class RunStore(Protocol):
    async def create(self, user_id: UUID, key: str) -> str:
        """Open a new run of the user's for key, such as their chat, and return its id;
        Conflict while key's last run is still going"""
        ...

    async def append(self, run_id: str, seq: int, data: str) -> None:
        """Keep the run's event number seq, its JSON data, and wake its readers"""
        ...

    async def finish(self, run_id: str) -> None:
        """Mark the run ended and wake its readers"""
        ...

    async def latest(self, key: str) -> tuple[str, int]:
        """Key's run a client may still read and how many events it has; NotFound when
        there is none"""
        ...

    def read(self, run_id: str, after: int) -> AsyncIterator[str]:
        """The JSON data of the run's events after the first `after`, then of each new
        one until it ends"""
        ...

    async def aclose(self) -> None:
        """Release what the store holds open"""
        ...


__all__ = ["RunStore"]
