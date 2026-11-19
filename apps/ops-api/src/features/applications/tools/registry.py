from functools import partial

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.agent_runner import Tool, Tools
from src.features.applications.tools.applications import (
    ApplicationsRequest,
    applications,
)


def application_tools(factory: async_sessionmaker[AsyncSession]) -> Tools:
    """The applications' tools"""
    return {"applications": Tool(ApplicationsRequest, partial(applications, factory))}


__all__ = ["application_tools"]
