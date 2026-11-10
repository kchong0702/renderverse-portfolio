from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from src.db.repository import Repository
from src.features.jobs.models import Job


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


__all__ = ["JobRepository"]
