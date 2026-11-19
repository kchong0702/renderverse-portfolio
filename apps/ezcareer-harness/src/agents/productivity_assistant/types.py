from datetime import date, datetime
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from src.shared.email import EmailThread, TimeSlot


class LoadedThread(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    thread: EmailThread
    """The email thread read_thread asked for"""


class FreeSlots(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    free_slots: list[TimeSlot]
    """Times the user is free; empty when they offer none"""

    timezone: ZoneInfo
    """The user's time zone, such as Europe/London"""


class CalendarEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    id: str
    """Google Calendar's event id"""

    title: str
    """The event's title; untrusted, and empty when its details are private"""

    start: AwareDatetime | date
    """When it starts; a date for an all-day event"""

    end: AwareDatetime | date
    """When it ends; for an all-day event the day after the last one"""

    all_day: bool
    """Whether it spans whole days rather than a time"""

    location: str
    """Where it takes place, as typed; untrusted"""

    url: str
    """The event in Google Calendar"""

    interview: bool
    """Whether Ops added it as an interview"""


class Events(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    events: list[CalendarEvent]
    """Events that overlap the days asked, earliest first"""

    timezone: ZoneInfo
    """The time zone the days are in"""

    today: date
    """Today's date in that time zone"""


class ThreadSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    id: str
    """What read_thread takes to read the thread"""

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
