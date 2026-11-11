from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select

from src.db.repository import Repository
from src.features.portfolio.models import Asset, PortfolioRelease


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

    async def lately_live(self, user_id: UUID) -> Sequence[PortfolioRelease]:
        """The 3 releases live most recently; only going live or off changes one"""
        return (
            await self._session.scalars(
                select(PortfolioRelease)
                .where(PortfolioRelease.user_id == user_id)
                .order_by(PortfolioRelease.updated_at.desc())
                .limit(3)
            )
        ).all()

    async def lock(self, user_id: UUID) -> None:
        """Wait for the user's other publish or roll back to commit; none on SQLite"""
        if self._session.get_bind().dialect.name == "postgresql":
            await self._session.execute(
                select(
                    func.pg_advisory_xact_lock(func.hashtext(f"portfolio:{user_id}"))
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

    async def assets(self, user_id: UUID) -> Sequence[Asset]:
        """The user's files, latest first"""
        return (
            await self._session.scalars(
                select(Asset)
                .where(Asset.user_id == user_id)
                .order_by(Asset.created_at.desc())
            )
        ).all()

    async def asset(self, user_id: UUID, sha256: str) -> Asset | None:
        """The user's file with this SHA-256, if uploaded"""
        return await self._session.scalar(
            select(Asset).where(Asset.user_id == user_id, Asset.sha256 == sha256)
        )


__all__ = ["PortfolioRepository"]
