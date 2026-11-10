from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFound
from src.features.jobs.models import Job
from src.features.jobs.repository import JobRepository
from src.features.jobs.schemas import FitAnalysis, JobCreate, JobRead, JobUpdate


class JobService:
    def __init__(self, session: AsyncSession):
        """Read and write jobs through a repository on the session"""
        self._repository = JobRepository(session)

    async def jobs(self, user_id: UUID) -> list[JobRead]:
        """Every job, best fit first; unanalysed ones last, newest first"""
        return [
            JobRead.model_validate(job, from_attributes=True)
            for job in await self._repository.jobs(user_id)
        ]

    async def job(self, user_id: UUID, job_id: UUID) -> JobRead:
        """One of the user's jobs; NotFound when it is not theirs"""
        row = await self._repository.owned(Job, user_id, job_id)
        if row is None:
            raise NotFound("No such job")
        return JobRead.model_validate(row, from_attributes=True)

    async def add(self, user_id: UUID, job: JobCreate) -> tuple[JobRead, bool]:
        """Store a posting, and whether it is new; one already stored under its
        external_id is refreshed in place and keeps its status"""
        stored = (
            await self._repository.job_at_source(user_id, job.external_id)
            if job.external_id
            else None
        )
        row = stored or Job(user_id=user_id)
        for field, value in job.model_dump(exclude={"analysis"}).items():
            setattr(row, field, value)
        row.analysis = job.analysis
        await self._repository.add(row)
        return JobRead.model_validate(row, from_attributes=True), stored is None

    async def update(self, user_id: UUID, job_id: UUID, patch: JobUpdate) -> JobRead:
        """Save, dismiss or return a job to the picks"""
        row = await self._repository.owned(Job, user_id, job_id)
        if row is None:
            raise NotFound("No such job")
        row.status = patch.status
        return JobRead.model_validate(row, from_attributes=True)

    async def analyse(
        self, user_id: UUID, job_id: UUID, analysis: FitAnalysis
    ) -> JobRead:
        """Replace how a job fits the profile"""
        row = await self._repository.owned(Job, user_id, job_id)
        if row is None:
            raise NotFound("No such job")
        row.analysis = analysis
        return JobRead.model_validate(row, from_attributes=True)


__all__ = ["JobService"]
