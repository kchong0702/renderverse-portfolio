from __future__ import annotations

from datetime import date, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.google import GoogleClient
from src.core.config import GoogleSettings
from src.core.exceptions import ServiceException
from src.core.runner import ToolError
from src.db.session import session_scope
from src.features.google import GoogleService
from src.features.inbox.schemas import ThreadsAnswer, ThreadSummary


class ThreadsRequest(BaseModel):
    execute_tool: Literal["threads"]
    """A paused run searches the user's email threads"""

    since: date | None = None
    """Earliest day a message was sent; None for any"""

    until: date | None = None
    """Latest day a message was sent; None for any"""

    keyword: str | None = Field(default=None, pattern=r'^[^"]{1,200}$')
    """Words the subject or a message contains; None for any"""

    sender: str | None = Field(default=None, pattern=r"^[\w .@+'&-]{1,200}$")
    """A sender's name, address or domain; None for anyone"""

    has_attachment: bool | None = None
    """Only threads with an attachment, or only those without; None for both"""

    limit: int = Field(ge=1)
    """The most threads to send back"""


def _search(request: ThreadsRequest) -> str:
    """The Gmail search for a run's thread search, each value quoted so it adds no
    operator; before: is exclusive, so it names the day after until"""
    terms = []
    if request.since:
        terms.append(f"after:{request.since:%Y/%m/%d}")
    if request.until:
        terms.append(f"before:{request.until + timedelta(days=1):%Y/%m/%d}")
    if request.sender:
        terms.append(f'from:"{request.sender}"')
    if request.has_attachment is not None:
        terms.append("has:attachment" if request.has_attachment else "-has:attachment")
    terms += [f'"{word}"' for word in (request.keyword or "").split()]
    return " ".join(terms)


async def threads(
    factory: async_sessionmaker[AsyncSession],
    client: GoogleClient,
    config: GoogleSettings,
    user_id: UUID,
    request: ThreadsRequest,
) -> ThreadsAnswer | ToolError:
    """The user's email threads a search finds, on a session of its own"""
    async for session in session_scope(factory):
        google = GoogleService(session, client, config)
        try:
            found, total = await client.threads(
                await google.access_token(user_id),
                _search(request),
                min(request.limit, config.thread_search_limit),
            )
            result = ThreadsAnswer(
                threads=[
                    ThreadSummary(
                        id=thread.id,
                        subject=thread.messages[0].payload.header("Subject"),
                        sender=thread.messages[-1].payload.header("From"),
                        last_sent_at=thread.messages[-1].internal_date,
                        message_count=len(thread.messages),
                        has_attachment=any(
                            m.payload.has_attachment() for m in thread.messages
                        ),
                    )
                    for thread in found
                ],
                total=total,
            )
        except ServiceException as error:
            result = ToolError(error=error.message)
    return result


__all__ = ["ThreadsRequest", "threads"]
