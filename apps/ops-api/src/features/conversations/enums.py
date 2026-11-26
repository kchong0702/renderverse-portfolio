from __future__ import annotations

from enum import StrEnum


class ServedAgent(StrEnum):
    CAREER_DIRECTOR = "career-director"
    """The general chat in the dock"""

    CAREER_CONSULTANT = "career-consultant"
    """The document editor's chat"""


class MessageRole(StrEnum):
    USER = "user"
    """The user wrote it"""

    AGENT = "agent"
    """An agent answered with it"""


__all__ = ["MessageRole", "ServedAgent"]
