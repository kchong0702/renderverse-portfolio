from __future__ import annotations

from enum import StrEnum


class ApplicationStage(StrEnum):
    DRAFT = "draft"
    """Being prepared, not sent yet"""

    APPLIED = "applied"
    """Sent, waiting to hear back"""

    REPLIED = "replied"
    """The employer answered"""

    INTERVIEW = "interview"
    """Interviews are booked or under way"""

    OFFER = "offer"
    """An offer is on the table"""

    CLOSED = "closed"
    """Rejected, withdrawn or turned down"""


class NextStepFormat(StrEnum):
    VIDEO = "video"
    """A video call"""

    PHONE = "phone"
    """A phone call"""

    ON_SITE = "on_site"
    """In person at the employer"""


__all__ = ["ApplicationStage", "NextStepFormat"]
