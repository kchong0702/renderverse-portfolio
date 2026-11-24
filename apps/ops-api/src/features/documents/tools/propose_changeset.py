from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.agent_runner import ToolError
from src.core.exceptions import InvalidInput, NotFound
from src.features.documents.repository import DocumentRepository
from src.features.documents.schemas import ChangesetStored, ProposeChangesetRequest
from src.features.documents.service import load_document, propose


async def propose_changeset(
    session: AsyncSession, user_id: UUID, request: ProposeChangesetRequest
) -> ChangesetStored | ToolError:
    """Store an agent's edits for review, merged into the pending changeset;
    ToolError when the document is not theirs or the edits don't fit it"""
    repository = DocumentRepository(session)
    try:
        row = await propose(
            repository,
            await load_document(repository, user_id, request.document_id),
            request.changeset,
        )
    except (NotFound, InvalidInput) as error:
        return ToolError(error=error.message)
    return ChangesetStored(changeset_id=row.id)


__all__ = ["propose_changeset"]
