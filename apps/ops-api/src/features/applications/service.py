from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, time
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import Conflict, NotFound
from src.db.base import as_utc, utcnow
from src.features.applications.enums import StepKind, StepStatus
from src.features.applications.models import Application, ApplicationStep
from src.features.applications.repository import ApplicationRepository
from src.features.applications.schemas import (
    ApplicationRead,
    ApplicationUpdate,
    ApplicationWrite,
    JobApplicationCreate,
    ManualApplicationCreate,
    StepRead,
    StepWrite,
)
from src.features.jobs import JobRead, JobService
from src.features.jobs.enums import JobStatus
from src.features.jobs.schemas import JobCreate, JobUpdate
from src.features.settings import SettingsService


def _at(step: ApplicationStep | StepRead, zone: ZoneInfo) -> datetime:
    """When the step happens: its start, or else the end of its due day in the zone"""
    return (
        as_utc(step.starts_at)
        if step.starts_at
        else datetime.combine(step.due_on, time.max, zone)
    )


def _to_read(
    application: Application,
    job: JobRead,
    steps: Sequence[ApplicationStep],
    zone: ZoneInfo,
) -> ApplicationRead:
    """The application as the API returns it, with its job and its step summary,
    days counted in the zone"""
    now = utcnow()
    open_steps = [step for step in steps if step.status is StepStatus.OPEN]
    next_step = min(
        (s for s in open_steps if _at(s, zone) > now),
        key=lambda s: _at(s, zone),
        default=None,
    )
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
        next_step=StepRead.model_validate(next_step, from_attributes=True)
        if next_step
        else None,
        overdue=[
            StepRead.model_validate(step, from_attributes=True)
            for step in sorted(open_steps, key=lambda s: s.due_on or date.max)
            if step.due_on and step.due_on < now.astimezone(zone).date()
        ],
        offer_deadline=min(
            (
                s.due_on
                for s in open_steps
                if s.kind is StepKind.OFFER_DEADLINE and s.due_on
            ),
            default=None,
        ),
    )


class ApplicationService:
    def __init__(
        self, session: AsyncSession, jobs: JobService, settings: SettingsService
    ):
        """Read and write the user's applications, their steps and their jobs"""
        self._repository = ApplicationRepository(session)
        self._jobs = jobs
        self._settings = settings

    async def _zone(self, user_id: UUID) -> ZoneInfo:
        """The user's time zone, UTC until they choose one"""
        return ZoneInfo(await self._settings.timezone(user_id) or "UTC")

    async def _owned(self, user_id: UUID, application_id: UUID) -> Application:
        """The user's application; NotFound when it is not theirs"""
        row = await self._repository.owned(Application, user_id, application_id)
        if row is None:
            raise NotFound("No such application")
        return row

    async def _owned_step(
        self, user_id: UUID, application_id: UUID, step_id: UUID
    ) -> ApplicationStep:
        """The user's step of the application; NotFound when it is not one"""
        step = await self._repository.owned(ApplicationStep, user_id, step_id)
        if step is None or step.application_id != application_id:
            raise NotFound("No such step")
        return step

    async def applications(self, user_id: UUID) -> list[ApplicationRead]:
        """Every application: those with an overdue step first, oldest overdue
        first, then soonest next step first, then newest first"""
        zone = await self._zone(user_id)
        applications = await self._repository.applications(user_id)
        steps = await self._repository.steps(user_id, [a.id for a in applications])
        reads = [
            _to_read(
                a,
                JobRead.model_validate(a.job, from_attributes=True),
                [s for s in steps if s.application_id == a.id],
                zone,
            )
            for a in applications
        ]
        return sorted(
            reads,
            key=lambda read: (
                read.overdue[0].due_on if read.overdue else date.max,
                _at(read.next_step, zone)
                if read.next_step
                else datetime.max.replace(tzinfo=UTC),
            ),
        )

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
        return _to_read(row, job, [], await self._zone(user_id))

    async def replace(
        self, user_id: UUID, application_id: UUID, application: ApplicationUpdate
    ) -> ApplicationRead:
        """Overwrite every field of an application, and the company and role of a job
        added by hand"""
        row = await self._owned(user_id, application_id)
        for field, value in application.model_dump(
            include=set(ApplicationWrite.model_fields)
        ).items():
            setattr(row, field, value)
        job = await self._jobs.update(
            user_id,
            row.job_id,
            JobUpdate(company=application.company, title=application.role),
        )
        return _to_read(
            row,
            job,
            await self._repository.steps(user_id, [row.id]),
            await self._zone(user_id),
        )

    async def delete(self, user_id: UUID, application_id: UUID) -> None:
        """Stop tracking an application, and delete its job when it was tracked by
        hand"""
        row = await self._owned(user_id, application_id)
        job = await self._jobs.job(user_id, row.job_id)
        await self._repository.delete(row)
        if job.source == "manual":
            await self._jobs.delete(user_id, job.id)

    async def steps_between(
        self, user_id: UUID, start: datetime, end: datetime
    ) -> list[StepRead]:
        """The user's steps that start from start until end, soonest first"""
        return [
            StepRead.model_validate(step, from_attributes=True)
            for step in await self._repository.steps_between(user_id, start, end)
        ]

    async def steps(self, user_id: UUID, application_id: UUID) -> list[StepRead]:
        """The application's steps, soonest first"""
        await self._owned(user_id, application_id)
        zone = await self._zone(user_id)
        return [
            StepRead.model_validate(step, from_attributes=True)
            for step in sorted(
                await self._repository.steps(user_id, [application_id]),
                key=lambda s: _at(s, zone),
            )
        ]

    async def add_step(
        self, user_id: UUID, application_id: UUID, step: StepWrite
    ) -> StepRead:
        """Add a step to the application"""
        await self._owned(user_id, application_id)
        row = await self._repository.add(
            ApplicationStep(
                user_id=user_id, application_id=application_id, **step.model_dump()
            )
        )
        return StepRead.model_validate(row, from_attributes=True)

    async def replace_step(
        self, user_id: UUID, application_id: UUID, step_id: UUID, step: StepWrite
    ) -> StepRead:
        """Overwrite every field of a step, such as its time after a reschedule or
        its status once done or cancelled"""
        row = await self._owned_step(user_id, application_id, step_id)
        for field, value in step.model_dump().items():
            setattr(row, field, value)
        return StepRead.model_validate(row, from_attributes=True)

    async def delete_step(
        self, user_id: UUID, application_id: UUID, step_id: UUID
    ) -> None:
        """Remove a step"""
        await self._repository.delete(
            await self._owned_step(user_id, application_id, step_id)
        )


__all__ = ["ApplicationService"]
