from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.agent_runner import ToolError
from src.core.exceptions import Conflict, InvalidInput, NotFound
from src.features.conversations.schemas import StartedTurns
from src.features.jobs.router import job_service

if TYPE_CHECKING:
    from src.app.container import Container


class TailorDocumentsRequest(BaseModel):
    execute_tool: Literal["tailor_documents"]
    """career-director asks to tailor the master résumé and cover letter to a job"""

    job_id: UUID
    """The job to tailor them to"""


async def tailor_documents(
    container: Container,
    session: AsyncSession,
    user_id: UUID,
    request: TailorDocumentsRequest,
) -> StartedTurns | ToolError:
    """Copy the masters for the job and start a turn tailoring each in the background,
    as the Jobs page does; ToolError when the job or a master résumé is missing"""
    try:
        return await job_service(session, container).tailor_documents(
            user_id, request.job_id
        )
    except (NotFound, Conflict, InvalidInput) as error:
        return ToolError(error=error.message)


__all__ = ["TailorDocumentsRequest", "tailor_documents"]
