from functools import partial

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.google import GoogleClient
from src.core.agent_runner import Tool, Tools
from src.core.config import GoogleSettings
from src.features.inbox.tools.free_slots import FreeSlotsRequest, free_slots
from src.features.inbox.tools.thread import ThreadRequest, thread
from src.features.inbox.tools.threads import ThreadsRequest, threads


def inbox_tools(
    factory: async_sessionmaker[AsyncSession],
    client: GoogleClient,
    config: GoogleSettings,
) -> Tools:
    """The inbox's tools"""
    return {
        "thread": Tool(ThreadRequest, partial(thread, factory, client, config)),
        "threads": Tool(ThreadsRequest, partial(threads, factory, client, config)),
        "free_slots": Tool(
            FreeSlotsRequest, partial(free_slots, factory, client, config)
        ),
    }


__all__ = ["inbox_tools"]
