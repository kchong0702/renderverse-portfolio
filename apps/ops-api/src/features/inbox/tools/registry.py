from functools import partial

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.ezcareer import EzcareerClient
from src.clients.google import GoogleClient
from src.core.config import GoogleSettings
from src.core.runner import Tool, Tools
from src.features.inbox.tools.free_slots import FreeSlotsRequest, free_slots
from src.features.inbox.tools.thread import ThreadRequest, thread
from src.features.inbox.tools.threads import ThreadsRequest, threads


def inbox_tools(
    factory: async_sessionmaker[AsyncSession],
    client: GoogleClient,
    config: GoogleSettings,
    ezcareer: EzcareerClient,
) -> Tools:
    """The inbox's tools"""
    return {
        "thread": Tool(ThreadRequest, partial(thread, factory, client, config)),
        "threads": Tool(ThreadsRequest, partial(threads, factory, client, config)),
        "free_slots": Tool(
            FreeSlotsRequest, partial(free_slots, factory, client, config, ezcareer)
        ),
    }


__all__ = ["inbox_tools"]
