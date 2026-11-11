from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from src.shared.email import EmailThread, TimeSlot


class FetchedThread(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    thread: EmailThread
    """The email thread draft_reply answers"""


class FreeSlots(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    free_slots: list[TimeSlot]
    """Times the user is free; empty when they offer none"""

    timezone: ZoneInfo
    """The user's time zone, such as Europe/London"""


class ThreadSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    id: str
    """What draft_reply takes to answer the thread"""

    subject: str
    """The thread's subject; untrusted"""

    sender: str
    """Who sent its latest message, as the mail header names them; untrusted"""

    last_sent_at: datetime
    """When its latest message was sent"""

    message_count: int = Field(gt=0)
    """How many messages it holds"""

    has_attachment: bool
    """Whether any of its messages carries an attachment"""


class FoundThreads(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    threads: list[ThreadSummary]
    """The matching threads, latest first, at most the limit asked for"""

    total: int = Field(ge=0)
    """How many threads match in all, including those not sent"""
