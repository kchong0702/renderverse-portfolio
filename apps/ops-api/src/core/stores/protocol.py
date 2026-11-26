from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.core.stores.enums import AgentRunStatus


@dataclass(frozen=True)
class RunRecord:
    id: str
    """The run's id"""

    user_id: UUID
    """Who the run is for"""

    thread_id: str
    """The A2A context_id the run belongs to"""

    agent: str
    """The harness agent the run calls"""

    task_id: str | None
    """The A2A task the run follows; None until the harness made it"""

    started_at: datetime
    """When the run was opened"""

    events: int
    """How many events it kept so far"""


class RunStore(Protocol):
    async def create(self, user_id: UUID, thread_id: str, agent: str) -> str:
        """Open a running run of the user's agent on thread_id, owned by this process,
        and return its id; Conflict while thread_id's last run is still going"""
        ...

    async def append(self, run_id: str, seq: int, data: dict[str, Any]) -> None:
        """Keep the run's event number seq and wake its readers; RunLost once another
        process took the run over"""
        ...

    async def set_task(self, run_id: str, task_id: str) -> None:
        """Keep the A2A task the run follows for a process that takes it over; RunLost
        once another process took the run over"""
        ...

    async def finish(
        self, run_id: str, status: AgentRunStatus, task_id: str | None
    ) -> None:
        """Mark the run ended with status and the A2A task it ran, and wake its readers;
        RunLost once another process took the run over"""
        ...

    async def latest(self, thread_id: str) -> tuple[str, int]:
        """thread_id's run a client may still read and how many events it has;
        NotFound when there is none"""
        ...

    async def paused(self, thread_id: str) -> tuple[str, str] | None:
        """The task thread_id's last run paused on and the status of its last event;
        None unless that run ended asking the user"""
        ...

    async def abandoned(
        self, thread_id: str
    ) -> tuple[str, str | None, datetime] | None:
        """The id, A2A task if known and start of thread_id's last run when ops-api gave
        up following it; None otherwise"""
        ...

    def read(self, run_id: str, after: int) -> AsyncIterator[dict[str, Any]]:
        """The run's events after the first `after`, then each new one until it ends"""
        ...

    async def heartbeat(self) -> set[str]:
        """Mark this process alive on every running run it owns and return their ids"""
        ...

    async def sweep(self) -> list[RunRecord]:
        """Take over every running run whose process missed its heartbeats"""
        ...

    async def release(self) -> None:
        """Let other processes take over this process's running runs at once"""
        ...

    async def aclose(self) -> None:
        """Release what the store holds open"""
        ...


__all__ = ["RunRecord", "RunStore"]
