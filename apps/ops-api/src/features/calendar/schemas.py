from __future__ import annotations

from datetime import date, datetime

from pydantic import AwareDatetime, BaseModel, Field


class CalendarEvent(BaseModel):
    id: str
    """Google Calendar's event id"""

    title: str
    """The event's title; empty when its details are private"""

    start: datetime | date
    """When it starts; a date for an all-day event"""

    end: datetime | date
    """When it ends; for an all-day event the day after the last one"""

    all_day: bool
    """Whether it spans whole days rather than a time"""

    location: str
    """Where it takes place, as typed"""

    url: str
    """The event in Google Calendar"""

    interview: bool
    """Whether Ops added it as an interview"""


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    """The event's title, such as Lumen Pay technical interview"""

    start: AwareDatetime
    """When it starts"""

    end: AwareDatetime
    """When it ends; must be after start"""

    description: str | None = Field(default=None, max_length=8000)
    """Notes on the event, such as who to meet"""

    location: str | None = Field(default=None, max_length=500)
    """Where it takes place, such as a video link"""


class Slot(BaseModel):
    start: datetime
    """When the free time starts"""

    end: datetime
    """When it ends"""


class FreeSlots(BaseModel):
    free_slots: list[Slot]
    """Free time in work hours, earliest first"""

    timezone: str
    """The time zone the slots are in: the user's, or the calendar's until they choose
    one"""


__all__ = ["CalendarEvent", "EventCreate", "FreeSlots", "Slot"]
