from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from src.db.repository import Repository
from src.features.applications.models import Application


class ApplicationRepository(Repository):
    async def applications(self, user_id: UUID) -> Sequence[Application]:
        """The user's applications, soonest next step first"""
        return (
            await self._session.scalars(
                select(Application)
                .where(Application.user_id == user_id)
                .order_by(
                    Application.next_step_at.nulls_last(),
                    Application.created_at.desc(),
                )
            )
        ).all()


__all__ = ["ApplicationRepository"]
