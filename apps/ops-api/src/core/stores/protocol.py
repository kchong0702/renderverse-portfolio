from collections.abc import AsyncIterator
from typing import Any, Protocol
from uuid import UUID

from src.core.stores.enums import AgentRunStatus


class RunStore(Protocol):
    async def create(self, user_id: UUID, thread_id: str, agent: str) -> str:
        """Open a running run of the user's agent on thread_id, such as their chat, and
        return its id; Conflict while thread_id's last run is still going"""
        ...

    async def append(self, run_id: str, seq: int, data: dict[str, Any]) -> None:
        """Keep the run's event number seq and wake its readers"""
        ...

    async def finish(
        self, run_id: str, status: AgentRunStatus, task_id: str | None
    ) -> None:
        """Mark the run ended with status and the A2A task it ran, and wake its
        readers"""
        ...

    async def latest(self, thread_id: str) -> tuple[str, int]:
        """thread_id's run a client may still read and how many events it has;
        NotFound when there is none"""
        ...

    def read(self, run_id: str, after: int) -> AsyncIterator[dict[str, Any]]:
        """The run's events after the first `after`, then each new one until it ends"""
        ...

    async def aclose(self) -> None:
        """Release what the store holds open"""
        ...


__all__ = ["RunStore"]
