from __future__ import annotations

from collections import Counter
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.session import session_scope
from src.features.jobs.enums import JobStatus
from src.features.jobs.repository import JobRepository
from src.features.jobs.schemas import JobRead, SavedJob, SavedJobsAnswer


class SavedJobsRequest(BaseModel):
    execute_tool: Literal["saved_jobs"]
    """A paused run asks for the jobs on the user's Jobs page"""

    company: str | None = None
    """Only jobs at a company whose name contains this; every company when None"""

    status: JobStatus | None = None
    """Only jobs with this status; picked and saved ones, as the Jobs page shows,
    when None"""


async def saved_jobs(
    factory: async_sessionmaker[AsyncSession], user_id: UUID, request: SavedJobsRequest
) -> SavedJobsAnswer:
    """The user's jobs at the company asked, counted by status, and those with the
    status asked, on a session of its own"""
    async for session in session_scope(factory):
        found = [
            JobRead.model_validate(job, from_attributes=True)
            for job in await JobRepository(session).jobs(user_id)
            if request.company is None
            or request.company.casefold() in job.company.casefold()
        ]
        counts = Counter(job.status for job in found)
        wanted = (
            {request.status} if request.status else {JobStatus.PICKED, JobStatus.SAVED}
        )
        result = SavedJobsAnswer(
            by_status={status: counts[status] for status in JobStatus},
            jobs=[
                SavedJob(
                    **job.model_dump(
                        include={
                            "id",
                            "title",
                            "company",
                            "location",
                            "salary",
                            "url",
                            "posted_at",
                            "status",
                        }
                    ),
                    fit=job.analysis.fit if job.analysis else None,
                )
                for job in found
                if job.status in wanted
            ],
        )
    return result


__all__ = ["SavedJobsRequest", "saved_jobs"]
