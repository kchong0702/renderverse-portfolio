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


class StepKind(StrEnum):
    INTERVIEW = "interview"
    """An interview at a set time"""

    FOLLOW_UP = "follow_up"
    """A nudge to send the employer"""

    TAKE_HOME = "take_home"
    """An assignment to hand in"""

    OFFER_DEADLINE = "offer_deadline"
    """The day an offer must be answered by"""


class StepStatus(StrEnum):
    OPEN = "open"
    """Still to happen or be done"""

    DONE = "done"
    """Happened or handed in"""

    CANCELLED = "cancelled"
    """Called off"""


__all__ = ["ApplicationStage", "NextStepFormat", "StepKind", "StepStatus"]
