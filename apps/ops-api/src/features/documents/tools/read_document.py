from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.agent_runner import ToolError
from src.core.exceptions import NotFound
from src.db.session import session_scope
from src.features.documents.repository import DocumentRepository
from src.features.documents.schemas import DocumentContent, ReadDocumentRequest
from src.features.documents.service import load_document


async def read_document(
    factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
    request: ReadDocumentRequest,
) -> DocumentContent | ToolError:
    """The user's document's title, draft and imported lines, on a session of its own;
    ToolError when the document is not theirs"""
    async for session in session_scope(factory):
        repository = DocumentRepository(session)
        try:
            document = await load_document(repository, user_id, request.document_id)
        except NotFound as error:
            return ToolError(error=error.message)
        result = DocumentContent(
            title=document.title,
            document=document.body,
            pdf_lines=await repository.lines(document),
            job_id=document.job_id,
        )
    return result


__all__ = ["read_document"]
