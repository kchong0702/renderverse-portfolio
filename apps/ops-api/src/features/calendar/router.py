from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import AwareDatetime

from src.core.auth import CurrentUserDep
from src.features.calendar.schemas import CalendarEvent
from src.features.calendar.service import CalendarService
from src.features.google import GoogleServiceDep

router = APIRouter(prefix="/calendar", tags=["calendar"])


def get_calendar_service(google: GoogleServiceDep, request: Request) -> CalendarService:
    """The calendar service, reading Google Calendar"""
    return CalendarService(google, request.app.state.google)


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
