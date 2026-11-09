from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


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


__all__ = ["CalendarEvent"]
