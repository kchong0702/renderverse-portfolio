from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.google import GoogleClient
from src.core.agent_runner import ToolError
from src.core.config import GoogleSettings, get_settings
from src.core.exceptions import ServiceException
from src.db.session import session_scope
from src.features.calendar import CalendarService
from src.features.calendar.schemas import FreeSlots
from src.features.google import GoogleService
from src.features.settings import SettingsService


class FreeSlotsRequest(BaseModel):
    execute_tool: Literal["free_slots"]
    """A paused run asks for the times the user is free"""

    days: int = Field(ge=1, le=30)
    """How many days from tomorrow to look in"""


async def free_slots(
    factory: async_sessionmaker[AsyncSession],
    client: GoogleClient,
    config: GoogleSettings,
    user_id: UUID,
    request: FreeSlotsRequest,
) -> FreeSlots | ToolError:
    """The times the user is free in the days asked, none when they don't offer free
    slots, on a session of its own"""
    async for session in session_scope(factory):
        google = GoogleService(session, client, config)
        try:
            settings = await SettingsService(
                session, google, get_settings().jsearch
            ).get(user_id)
            free = await CalendarService(google, client, config).free_slots(
                user_id, settings.scheduling, request.days
            )
            result = (
                free
                if settings.automation.offer_free_slots
                else free.model_copy(update={"free_slots": []})
            )
        except ServiceException as error:
            result = ToolError(error=error.message)
    return result


__all__ = ["FreeSlotsRequest", "free_slots"]
