from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.agent_runner import ToolError
from src.core.exceptions import InvalidInput
from src.features.conversations.router import conversation_service
from src.features.conversations.schemas import EditDocumentsRequest, StartedTurns

if TYPE_CHECKING:
    from src.app.container import Container


async def edit_documents(
    container: Container,
    session: AsyncSession,
    user_id: UUID,
    request: EditDocumentsRequest,
) -> StartedTurns | ToolError:
    """Start career-consultant on each of the user's documents in the background;
    ToolError before the user wrote any message"""
    try:
        return await conversation_service(session, container).edit_documents(
            user_id, request.document_ids, request.instruction
        )
    except InvalidInput as error:
        return ToolError(error=error.message)


__all__ = ["edit_documents"]
