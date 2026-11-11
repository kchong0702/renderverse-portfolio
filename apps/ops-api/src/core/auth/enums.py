from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    """Uses everything, the portfolio included"""

    USER = "user"
    """Uses everything but the portfolio"""


__all__ = ["Role"]
