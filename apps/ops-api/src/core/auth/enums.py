from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    """Uses everything, the portfolio included"""

    USER = "user"
    """Uses everything but the portfolio"""


class AttemptScope(StrEnum):
    EMAIL = "email"
    """Password sign-ins for one typed email"""

    IP = "ip"
    """Password sign-ins from one client address"""


__all__ = ["AttemptScope", "Role"]
