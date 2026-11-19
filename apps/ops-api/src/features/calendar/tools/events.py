from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.google import GoogleClient
from src.core.agent_runner import ToolError
from src.core.config import GoogleSettings
from src.core.exceptions import ServiceException
from src.features.calendar.schemas import Events
from src.features.calendar.service import token_events
from src.features.google import GoogleService
from src.features.settings.repository import SettingsRepository


class EventsRequest(BaseModel):
    execute_tool: Literal["events"]
    """A paused run asks for the events on the user's calendar"""

    days: int = Field(ge=1, le=31)
    """How many days from the start of today to look in"""


async def events(
    factory: async_sessionmaker[AsyncSession],
    client: GoogleClient,
    config: GoogleSettings,
    user_id: UUID,
    request: EventsRequest,
) -> Events | ToolError:
    """The events on the user's calendar in the days asked; its session is closed
    before Google is called"""
    try:
        async with factory() as session, session.begin():
            settings = await SettingsRepository(session).get(user_id)
            refresh_token = await GoogleService(session, client, config).refresh_token(
                user_id
            )
        result = await token_events(
            client,
            await client.refresh(refresh_token),
            settings.timezone if settings else None,
            request.days,
        )
    except ServiceException as error:
        result = ToolError(error=error.message)
    return result


__all__ = ["EventsRequest", "events"]
