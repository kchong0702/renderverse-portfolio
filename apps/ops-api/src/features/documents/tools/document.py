from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.agent_runner import ToolError
from src.db.session import session_scope
from src.features.documents.models import Document
from src.features.documents.repository import DocumentRepository
from src.features.documents.schemas import DocumentAnswer


class DocumentRequest(BaseModel):
    execute_tool: Literal["document"]
    """A paused run asks for one of the user's documents"""

    id: UUID
    """The document"""


async def document(
    factory: async_sessionmaker[AsyncSession], user_id: UUID, request: DocumentRequest
) -> DocumentAnswer | ToolError:
    """One of the user's documents with its imported lines, on a session of its own"""
    async for session in session_scope(factory):
        repository = DocumentRepository(session)
        row = await repository.owned(Document, user_id, request.id)
        result = (
            DocumentAnswer(document=row.body, lines=await repository.lines(row))
            if row
            else ToolError(error="No such document")
        )
    return result


__all__ = ["DocumentRequest", "document"]
