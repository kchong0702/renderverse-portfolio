from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update

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

    async def thread_steps(
        self, user_id: UUID, email_thread_ids: list[UUID]
    ) -> Sequence[ApplicationStep]:
        """The user's steps that triage found in these email threads"""
        return (
            await self._session.scalars(
                select(ApplicationStep).where(
                    ApplicationStep.user_id == user_id,
                    ApplicationStep.email_thread_id.in_(email_thread_ids),
                )
            )
        ).all()

    async def link_thread_steps(
        self, email_thread_id: UUID, application_id: UUID
    ) -> None:
        """Put the steps found in the email thread on the application"""
        await self._session.execute(
            update(ApplicationStep)
            .where(ApplicationStep.email_thread_id == email_thread_id)
            .values(application_id=application_id)
        )

    async def claim_event(self, step: ApplicationStep, event_id: str) -> bool:
        """Set the step's event if it has none; True if this call set it"""
        return (
            await self._session.scalar(
                update(ApplicationStep)
                .where(
                    ApplicationStep.id == step.id, ApplicationStep.event_id.is_(None)
                )
                .values(event_id=event_id)
                .returning(ApplicationStep.id)
            )
            is not None
        )


__all__ = ["ApplicationRepository"]
