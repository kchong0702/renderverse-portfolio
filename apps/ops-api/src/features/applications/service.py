from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFound
from src.features.applications.models import Application
from src.features.applications.repository import ApplicationRepository
from src.features.applications.schemas import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationWrite,
)
from src.features.jobs import FitAnalysis, JobService


def _to_read(application: Application, analysis: FitAnalysis | None) -> ApplicationRead:
    """The application as the API returns it, with its job's fit"""
    return ApplicationRead.model_validate(application, from_attributes=True).model_copy(
        update={"fit": analysis.fit if analysis else None}
    )


class ApplicationService:
    def __init__(self, session: AsyncSession, jobs: JobService):
        """Write applications through a repository on the session, and read fits
        from the jobs service"""
        self._repository = ApplicationRepository(session)
        self._jobs = jobs

    async def applications(self, user_id: UUID) -> list[ApplicationRead]:
        """Every application, soonest next step first"""
        return [
            _to_read(application, analysis)
            for application, analysis in await self._repository.applications(user_id)
        ]

    async def add(
        self, user_id: UUID, application: ApplicationCreate
    ) -> ApplicationRead:
        """Track a new application, for one of the user's jobs or none"""
        job = (
            await self._jobs.job(user_id, application.job_id)
            if application.job_id
            else None
        )
        row = await self._repository.add(
            Application(user_id=user_id, **application.model_dump())
        )
        return _to_read(row, job.analysis if job else None)

    async def replace(
        self, user_id: UUID, application_id: UUID, application: ApplicationWrite
    ) -> ApplicationRead:
        """Overwrite every field of an application but its job"""
        row = await self._repository.owned(Application, user_id, application_id)
        if row is None:
            raise NotFound("No such application")
        for field, value in application.model_dump().items():
            setattr(row, field, value)
        job = await self._jobs.job(user_id, row.job_id) if row.job_id else None
        return _to_read(row, job.analysis if job else None)

    async def delete(self, user_id: UUID, application_id: UUID) -> None:
        """Stop tracking an application"""
        row = await self._repository.owned(Application, user_id, application_id)
        if row is None:
            raise NotFound("No such application")
        await self._repository.delete(row)


__all__ = ["ApplicationService"]
