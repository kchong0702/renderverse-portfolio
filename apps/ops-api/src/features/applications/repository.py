from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from src.db.repository import Repository
from src.features.applications.models import Application, ApplicationStep


class ApplicationRepository(Repository):
    async def applications(self, user_id: UUID) -> Sequence[Application]:
        """The user's applications with their jobs, newest first"""
        return (
            await self._session.scalars(
                select(Application)
                .where(Application.user_id == user_id)
                .order_by(Application.created_at.desc())
            )
        ).all()

    async def steps(
        self, user_id: UUID, application_ids: list[UUID]
    ) -> Sequence[ApplicationStep]:
        """The user's steps of these applications"""
        return (
            await self._session.scalars(
                select(ApplicationStep).where(
                    ApplicationStep.user_id == user_id,
                    ApplicationStep.application_id.in_(application_ids),
                )
            )
        ).all()

    async def steps_between(
        self, user_id: UUID, start: datetime, end: datetime
    ) -> Sequence[ApplicationStep]:
        """The user's steps that start from start until end, soonest first"""
        return (
            await self._session.scalars(
                select(ApplicationStep)
                .where(
                    ApplicationStep.user_id == user_id,
                    ApplicationStep.starts_at >= start,
                    ApplicationStep.starts_at < end,
                )
                .order_by(ApplicationStep.starts_at)
            )
        ).all()


__all__ = ["ApplicationRepository"]
