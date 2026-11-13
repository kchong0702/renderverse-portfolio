from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.google import GoogleClient
from src.core.agent_runner import ToolError
from src.core.config import GoogleSettings
from src.core.exceptions import ServiceException
from src.features.google import GoogleService
from src.features.inbox.content import thread_content
from src.features.inbox.schemas import ThreadAnswer


class ThreadRequest(BaseModel):
    execute_tool: Literal["thread"]
    """A paused run asks for one of the user's email threads"""

    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    """The Gmail thread"""


async def thread(
    factory: async_sessionmaker[AsyncSession],
    client: GoogleClient,
    config: GoogleSettings,
    user_id: UUID,
    request: ThreadRequest,
) -> ThreadAnswer | ToolError:
    """One of the user's email threads, its session closed before Google is called"""
    try:
        async with factory() as session:
            refresh_token = await GoogleService(session, client, config).refresh_token(
                user_id
            )
        result = ThreadAnswer(
            thread=thread_content(
                await client.thread(await client.refresh(refresh_token), request.id)
            )
        )
    except ServiceException as error:
        result = ToolError(error=error.message)
    return result


__all__ = ["ThreadRequest", "thread"]
