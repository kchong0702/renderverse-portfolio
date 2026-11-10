from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select

from src.db.repository import Repository
from src.features.portfolio.models import PortfolioRelease


class PortfolioRepository(Repository):
    async def releases(self, user_id: UUID) -> Sequence[PortfolioRelease]:
        """The user's releases, latest first"""
        return (
            await self._session.scalars(
                select(PortfolioRelease)
                .where(PortfolioRelease.user_id == user_id)
                .order_by(PortfolioRelease.number.desc())
            )
        ).all()

    async def live(self, user_id: UUID) -> PortfolioRelease | None:
        """The user's live release, if any is published"""
        return await self._session.scalar(
            select(PortfolioRelease).where(
                PortfolioRelease.user_id == user_id, PortfolioRelease.live
            )
        )

    async def last_number(self, user_id: UUID) -> int:
        """The user's highest release number, or 0 before the first"""
        return (
            await self._session.scalar(
                select(func.max(PortfolioRelease.number)).where(
                    PortfolioRelease.user_id == user_id
                )
            )
            or 0
        )


__all__ = ["PortfolioRepository"]
