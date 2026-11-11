from __future__ import annotations

from enum import StrEnum


class AgentRunStatus(StrEnum):
    RUNNING = "running"
    """The run is still writing events"""

    COMPLETED = "completed"
    """The run finished with a reply"""

    INPUT_REQUIRED = "input_required"
    """The run paused to ask the user something"""

    FAILED = "failed"
    """The run stopped without a reply"""

    CANCELLED = "cancelled"
    """The user or a shutdown stopped the run"""


__all__ = ["AgentRunStatus"]
