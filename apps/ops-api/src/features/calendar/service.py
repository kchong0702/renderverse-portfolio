from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from src.clients.google import (
    EventMove,
    EventTime,
    ExtendedProperties,
    GoogleClient,
    GoogleEvent,
    NewEvent,
)
from src.core.config import GoogleSettings
from src.core.exceptions import InvalidInput, NotFound
from src.db.base import utcnow
from src.features.calendar.schemas import CalendarEvent, EventCreate, FreeSlots, Slot
from src.features.google import GoogleService
from src.features.settings.schemas import Scheduling

_INTERVIEW = {"ops": "interview"}


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
        interview=_INTERVIEW.items() <= event.extended_properties.private.items(),
    )


async def token_free_slots(
    client: GoogleClient,
    settings: GoogleSettings,
    token: str,
    scheduling: Scheduling,
    days: int,
) -> FreeSlots:
    """Free time in the token's calendar's weekday work hours from tomorrow, in the
    user's time zone or its own, an interview long with the meeting gap clear"""
    now = utcnow()
    found = await client.events(token, now, now + timedelta(days=days + 1))
    timezone = scheduling.timezone or found.time_zone
    zone = ZoneInfo(timezone)
    gap = timedelta(minutes=scheduling.meeting_gap_minutes)
    busy = sorted(
        (event.start.date_time - gap, event.end.date_time + gap)
        for event in found.items
        if event.start.date_time
        and event.end.date_time
        and event.status != "cancelled"
        and event.transparency != "transparent"
    )
    shortest = timedelta(minutes=settings.interview_minutes)
    today = now.astimezone(zone).date()
    slots = []
    for day in (today + timedelta(days=n) for n in range(1, days + 1)):
        if day.weekday() >= 5:
            continue
        free_from = datetime.combine(day, scheduling.work_day_start, zone)
        close = datetime.combine(day, scheduling.work_day_end, zone)
        for busy_from, busy_to in [*busy, (close, close)]:
            free_to = min(busy_from, close)
            if free_to - free_from >= shortest:
                slots.append(Slot(start=free_from, end=free_to.astimezone(zone)))
            free_from = max(free_from, busy_to.astimezone(zone))
            if free_from >= close:
                break
    return FreeSlots(free_slots=slots, timezone=timezone)


class CalendarService:
    def __init__(
        self, google: GoogleService, client: GoogleClient, settings: GoogleSettings
    ):
        """Read Google Calendar with the user's token, within the configured range"""
        self._google = google
        self._client = client
        self._settings = settings

    async def events(
        self, user_id: UUID, start: datetime, end: datetime
    ) -> list[CalendarEvent]:
        """Events on the primary calendar that overlap the range, earliest first"""
        days = self._settings.calendar_max_days
        if not start < end <= start + timedelta(days=days):
            raise InvalidInput(
                f"The range must end after it starts, within {days} days"
            )
        token = await self._google.access_token(user_id)
        found = await self._client.events(token, start, end)
        return [_event(event) for event in found.items if event.status != "cancelled"]

    async def create(
        self, user_id: UUID, event: EventCreate, event_id: str | None = None
    ) -> CalendarEvent:
        """Add an interview to the primary calendar, under event_id when given"""
        if event.end <= event.start:
            raise InvalidInput("The event must end after it starts")
        token = await self._google.access_token(user_id)
        created = await self._client.create_event(
            token,
            NewEvent(
                id=event_id,
                summary=event.title,
                start=EventTime(date_time=event.start),
                end=EventTime(date_time=event.end),
                description=event.description,
                location=event.location,
                extended_properties=ExtendedProperties(private=_INTERVIEW),
            ),
        )
        return _event(created)

    async def move(
        self, user_id: UUID, event_id: str, start: datetime, end: datetime | None
    ) -> None:
        """Move an event to start, ending at end or an interview's length later; one
        Google no longer has is skipped"""
        token = await self._google.access_token(user_id)
        with suppress(NotFound):
            await self._client.move_event(
                token,
                event_id,
                EventMove(
                    start=EventTime(date_time=start),
                    end=EventTime(
                        date_time=end
                        or start + timedelta(minutes=self._settings.interview_minutes)
                    ),
                ),
            )

    async def delete(self, user_id: UUID, event_id: str) -> None:
        """Remove an event from the primary calendar"""
        await self._client.delete_event(
            await self._google.access_token(user_id), event_id
        )

    async def free_slots(
        self, user_id: UUID, scheduling: Scheduling, days: int
    ) -> FreeSlots:
        """The user's free time in their work hours from tomorrow, read with a fresh
        access token"""
        return await token_free_slots(
            self._client,
            self._settings,
            await self._google.access_token(user_id),
            scheduling,
            days,
        )


__all__ = ["CalendarService", "token_free_slots"]
