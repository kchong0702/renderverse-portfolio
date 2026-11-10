from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import AwareDatetime

from src.core.auth import CurrentUserDep
from src.core.config import get_settings
from src.features.calendar.schemas import CalendarEvent, EventCreate
from src.features.calendar.service import CalendarService
from src.features.google import GoogleServiceDep

router = APIRouter(prefix="/calendar", tags=["calendar"])


def get_calendar_service(google: GoogleServiceDep, request: Request) -> CalendarService:
    """The calendar service, reading Google Calendar"""
    return CalendarService(google, request.app.state.google, get_settings().google)


CalendarServiceDep = Annotated[CalendarService, Depends(get_calendar_service)]


@router.get("")
async def list_events(
    start: Annotated[AwareDatetime, Query(alias="from")],
    end: Annotated[AwareDatetime, Query(alias="to")],
    user: CurrentUserDep,
    service: CalendarServiceDep,
) -> list[CalendarEvent]:
    """Events on the user's primary Google Calendar between from and to"""
    return await service.events(user.id, start, end)


@router.post("/events", status_code=status.HTTP_201_CREATED)
async def create_event(
    event: EventCreate, user: CurrentUserDep, service: CalendarServiceDep
) -> CalendarEvent:
    """Add an event to the user's primary Google Calendar, such as an interview"""
    return await service.create(user.id, event)
