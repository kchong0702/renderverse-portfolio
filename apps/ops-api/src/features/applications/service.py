from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import Conflict, NotFound
from src.features.applications.models import Application
from src.features.applications.repository import ApplicationRepository
from src.features.applications.schemas import (
    ApplicationRead,
    ApplicationUpdate,
    ApplicationWrite,
    JobApplicationCreate,
    ManualApplicationCreate,
)
from src.features.jobs import JobRead, JobService
from src.features.jobs.enums import JobStatus
from src.features.jobs.schemas import JobCreate, JobUpdate


def _to_read(application: Application, job: JobRead) -> ApplicationRead:
    """The application as the API returns it, with its job's company, role and fit"""
    return ApplicationRead(
        **ApplicationWrite.model_validate(
            application, from_attributes=True
        ).model_dump(),
        id=application.id,
        job_id=application.job_id,
        company=job.company,
        role=job.title,
        by_hand=job.source == "manual",
        fit=job.analysis.fit if job.analysis else None,
    )


class ApplicationService:
    def __init__(self, session: AsyncSession, jobs: JobService):
        """Read and write applications through a repository on the session, and
        their jobs through the job service"""
        self._repository = ApplicationRepository(session)
        self._jobs = jobs

    async def applications(self, user_id: UUID) -> list[ApplicationRead]:
        """Every application, soonest next step first"""
        return [
            _to_read(
                application,
                JobRead.model_validate(application.job, from_attributes=True),
            )
            for application in await self._repository.applications(user_id)
        ]

    async def add(
        self, user_id: UUID, application: JobApplicationCreate | ManualApplicationCreate
    ) -> ApplicationRead:
        """Track an application for one of the user's jobs, or for a new saved job
        made from the company and role; Conflict when the job has one already"""
        match application:
            case JobApplicationCreate(job_id=job_id):
                job = await self._jobs.job(user_id, job_id)
            case ManualApplicationCreate():
                added, _ = await self._jobs.add(
                    user_id,
                    JobCreate(
                        source="manual",
                        title=application.role,
                        company=application.company,
                        url=application.url,
                        location=application.location,
                    ),
                )
                job = await self._jobs.update(
                    user_id, added.id, JobUpdate(status=JobStatus.SAVED)
                )
        try:
            row = await self._repository.add(
                Application(
                    user_id=user_id,
                    job_id=job.id,
                    **application.model_dump(
                        include=set(ApplicationWrite.model_fields)
                    ),
                )
            )
        except IntegrityError as error:
            raise Conflict("This job already has an application") from error
        return _to_read(row, job)

    async def replace(
        self, user_id: UUID, application_id: UUID, application: ApplicationUpdate
    ) -> ApplicationRead:
        """Overwrite every field of an application, and the company and role of a job
        added by hand"""
        row = await self._repository.owned(Application, user_id, application_id)
        if row is None:
            raise NotFound("No such application")
        for field, value in application.model_dump(
            include=set(ApplicationWrite.model_fields)
        ).items():
            setattr(row, field, value)
        job = await self._jobs.update(
            user_id,
            row.job_id,
            JobUpdate(company=application.company, title=application.role),
        )
        return _to_read(row, job)

    async def delete(self, user_id: UUID, application_id: UUID) -> None:
        """Stop tracking an application, and delete its job when it was tracked by
        hand"""
        row = await self._repository.owned(Application, user_id, application_id)
        if row is None:
            raise NotFound("No such application")
        job = await self._jobs.job(user_id, row.job_id)
        await self._repository.delete(row)
        if job.source == "manual":
            await self._jobs.delete(user_id, job.id)


__all__ = ["ApplicationService"]
