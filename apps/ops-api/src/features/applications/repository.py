from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Row, select

from src.db.repository import Repository
from src.features.applications.models import Application
from src.features.jobs import FitAnalysis
from src.features.jobs.models import Job


class ApplicationRepository(Repository):
    async def applications(
        self, user_id: UUID
    ) -> Sequence[Row[Application, FitAnalysis | None]]:
        """The user's applications with their job's analysis, soonest next step first"""
        return (
            await self._session.execute(
                select(Application, Job.analysis)
                .outerjoin(
                    Job, (Job.id == Application.job_id) & (Job.user_id == user_id)
                )
                .where(Application.user_id == user_id)
                .order_by(
                    Application.next_step_at.nulls_last(),
                    Application.created_at.desc(),
                )
            )
        ).all()


__all__ = ["ApplicationRepository"]
