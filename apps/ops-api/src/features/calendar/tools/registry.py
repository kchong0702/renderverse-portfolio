from functools import partial

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.google import GoogleClient
from src.core.agent_runner import Tool, Tools
from src.core.config import GoogleSettings
from src.features.calendar.tools.events import EventsRequest, events


def calendar_tools(
    factory: async_sessionmaker[AsyncSession],
    client: GoogleClient,
    config: GoogleSettings,
) -> Tools:
    """The calendar's tools"""
    return {"events": Tool(EventsRequest, partial(events, factory, client, config))}


__all__ = ["calendar_tools"]
