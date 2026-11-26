from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.agent_runner import ToolError
from src.core.exceptions import Conflict, NotFound
from src.features.documents import document_service
from src.features.documents.repository import DocumentRepository
from src.features.jobs.router import job_service
from src.features.jobs.schemas import CopiedForJob, CopyForJobRequest, TargetJob

if TYPE_CHECKING:
    from src.app.container import Container


async def copy_for_job(
    container: Container,
    session: AsyncSession,
    user_id: UUID,
    request: CopyForJobRequest,
) -> CopiedForJob | ToolError:
    """The job's copy of the user's document's kind, made or reset once per copy_id,
    with the posting; ToolError when the document or job is missing, or on a conflict"""
    try:
        job = await job_service(session, container).job(user_id, request.job_id)
        copy, rejected = await document_service(session, container).copy_to_job(
            user_id,
            request.document_id,
            job.id,
            job.company or job.title,
            request.copy_id,
            request.start_over,
        )
    except (NotFound, Conflict) as error:
        return ToolError(error=error.message)
    return CopiedForJob(
        title=copy.title,
        document_id=copy.id,
        document=copy.body,
        pdf_lines=await DocumentRepository(session).lines(copy),
        job_id=copy.job_id,
        job=TargetJob(
            title=job.title,
            company=job.company,
            location=job.location,
            url=job.url,
            requirements=job.analysis.requirements if job.analysis else [],
        ),
        made=copy.id == request.copy_id,
        rejected_changeset=rejected,
    )


__all__ = ["copy_for_job"]
