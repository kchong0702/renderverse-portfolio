from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import exists, select

from src.db.repository import Repository
from src.features.jobs.enums import RunStatus, RunTrigger
from src.features.jobs.models import Job, JobRun
from src.features.jobs.schemas import JobSearch


class JobRepository(Repository):
    async def jobs(self, user_id: UUID) -> Sequence[Job]:
        """The user's jobs, best fit first; unanalysed ones last, newest posting first"""
        return (
            await self._session.scalars(
                select(Job)
                .where(Job.user_id == user_id)
                .order_by(
                    Job.analysis["fit"].as_integer().desc().nulls_last(),
                    Job.posted_at.desc().nulls_last(),
                    Job.created_at.desc(),
                )
            )
        ).all()

    async def job_at_source(self, user_id: UUID, external_id: str) -> Job | None:
        """The user's job with this id at its source, if stored"""
        return await self._session.scalar(
            select(Job).where(Job.user_id == user_id, Job.external_id == external_id)
        )

    async def latest_run(self, user_id: UUID) -> JobRun | None:
        """The user's most recently queued run, if any"""
        return await self._session.scalar(
            select(JobRun)
            .where(JobRun.user_id == user_id)
            .order_by(JobRun.created_at.desc())
            .limit(1)
        )

    async def running(self, user_id: UUID) -> bool:
        """Whether a worker is running one of the user's runs"""
        return bool(
            await self._session.scalar(
                select(
                    exists().where(
                        JobRun.user_id == user_id, JobRun.status == RunStatus.RUNNING
                    )
                )
            )
        )

    async def queue_run(
        self,
        user_id: UUID,
        trigger: RunTrigger,
        search: JobSearch | None,
        run_after: datetime | None,
    ) -> JobRun:
        """Insert a queued run inside a savepoint, starting now unless run_after is set"""
        async with self._session.begin_nested():
            run = JobRun(user_id=user_id, trigger=trigger, search=search)
            if run_after is not None:
                run.run_after = run_after
            return await self.add(run)


__all__ = ["JobRepository"]
