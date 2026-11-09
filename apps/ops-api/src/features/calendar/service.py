from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from src.clients.google import GoogleClient, GoogleEvent
from src.core.exceptions import InvalidInput
from src.features.calendar.schemas import CalendarEvent
from src.features.google import GoogleService


def _event(event: GoogleEvent) -> CalendarEvent:
    """The API's view of a Google Calendar event"""
    return CalendarEvent(
        id=event.id,
        title=event.summary,
        start=event.start.date_time or event.start.day,
        end=event.end.date_time or event.end.day,
        all_day=event.start.date_time is None,
        location=event.location,
        url=event.html_link,
    )


class CalendarService:
    def __init__(self, google: GoogleService, client: GoogleClient):
        """Read Google Calendar with the user's token"""
        self._google = google
        self._client = client

    async def events(
        self, user_id: UUID, start: datetime, end: datetime
    ) -> list[CalendarEvent]:
        """Events on the primary calendar that overlap the range, earliest first"""
        if not start < end <= start + timedelta(days=62):
            raise InvalidInput("The range must end after it starts, within 62 days")
        token = await self._google.access_token(user_id)
        found = await self._client.events(token, start, end)
        return [_event(event) for event in found if event.status != "cancelled"]


__all__ = ["CalendarService"]
