from __future__ import annotations

from enum import StrEnum


class ThreadState(StrEnum):
    NEEDS_REPLY = "needs_reply"
    """The employer is waiting on the user"""

    INTERVIEW = "interview"
    """It sets up or confirms an interview"""

    OFFER = "offer"
    """It makes an offer"""

    INFO = "info"
    """Nothing to act on"""


__all__ = ["ThreadState"]
