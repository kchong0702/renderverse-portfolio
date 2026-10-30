from __future__ import annotations

from typing import Protocol, runtime_checkable

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, ConfigDict, Field


@runtime_checkable
class Interruptible(Protocol):
    """Work in progress that can be stopped, such as a bot response"""

    @property
    def done(self) -> bool:
        """Whether the work has finished"""
        ...

    def stop(self) -> None:
        """Cancel the work if it is still running"""
        ...


class Session(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    """Sent in the session header; each browser tab has its own session"""

    cookie: str
    """Token of the browser cookie that owns this session"""

    created_at: float
    """Monotonic clock time the session was created"""

    last_seen: float
    """Monotonic clock time of the last request, for the idle TTL"""

    history: list[BaseMessage] = Field(default_factory=list)
    """Recent conversation, sent to the model as context"""

    response: Interruptible | None = None
    """The response in progress or most recently finished, if any"""


__all__ = [
    "Interruptible",
    "Session",
]
