from __future__ import annotations

from typing import Literal
from uuid import UUID

from document_schema import DocumentKind
from pydantic import BaseModel
from rapidfuzz import fuzz, process, utils
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import DocumentsSettings
from src.db.session import session_scope
from src.features.documents.repository import DocumentRepository
from src.features.documents.schemas import DocumentMatch, DocumentsAnswer


class DocumentsRequest(BaseModel):
    execute_tool: Literal["documents"]
    """A paused run asks for the user's documents"""

    name: str | None = None
    """Words of the title the user used, such as nortwind; None lists them all"""

    kind: DocumentKind | None = None
    """Only documents of this kind; every kind when None"""


async def documents(
    factory: async_sessionmaker[AsyncSession],
    limits: DocumentsSettings,
    user_id: UUID,
    request: DocumentsRequest,
) -> DocumentsAnswer:
    """The user's documents of the kind asked, the best match for a name first, on a
    session of its own"""
    async for session in session_scope(factory):
        found = [
            d
            for d in await DocumentRepository(session).documents(user_id)
            if request.kind is None or d.kind is request.kind
        ]
        if request.name:
            found = [
                found[index]
                for _, _, index in process.extract(
                    request.name,
                    [f"{d.title} {d.kind.value.replace('_', ' ')}" for d in found],
                    scorer=fuzz.partial_token_sort_ratio,
                    processor=utils.default_process,
                    score_cutoff=limits.match_cutoff,
                    limit=None,
                )
            ]
        result = DocumentsAnswer(
            documents=[
                DocumentMatch.model_validate(d, from_attributes=True) for d in found
            ]
        )
    return result


__all__ = ["DocumentsRequest", "documents"]
