from __future__ import annotations

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, ConfigDict, Field

from src.shared.protocol import Interruptible


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


__all__ = ["Session"]
