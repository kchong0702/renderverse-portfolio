from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class MessageLimitExceeded(BaseModel):
    model_config = ConfigDict(frozen=True)

    retry_after: float
    """Seconds until a message is allowed again"""

    limit: Literal["daily", "burst"]
    """Which limit was reached: the IP's rolling daily limit or a burst window"""


__all__ = ["MessageLimitExceeded"]
