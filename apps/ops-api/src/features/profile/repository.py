from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql, sqlite

from src.db.repository import Repository
from src.features.profile.models import Profile, ProfileEntry, ProfileSkill


class ProfileRepository(Repository):
    async def profile(self, user_id: UUID) -> Profile | None:
        """The user's profile row, if it exists yet"""
        return await self._session.get(Profile, user_id)

    async def create(self, user_id: UUID) -> Profile:
        """Insert an empty profile unless the user has one, and return the user's row"""
        dialect = self._session.get_bind().dialect.name
        insert = postgresql.insert if dialect == "postgresql" else sqlite.insert
        await self._session.execute(
            insert(Profile).values(user_id=user_id).on_conflict_do_nothing()
        )
        return await self._session.get_one(Profile, user_id)

    async def entries(self, user_id: UUID) -> Sequence[ProfileEntry]:
        """The user's entries, latest first; "present" sorts above any YYYY-MM,
        so ongoing ones lead"""
        return (
            await self._session.scalars(
                select(ProfileEntry)
                .where(ProfileEntry.user_id == user_id)
                .order_by(
                    func.coalesce(ProfileEntry.end, ProfileEntry.start)
                    .desc()
                    .nulls_last(),
                    ProfileEntry.start.desc().nulls_last(),
                    ProfileEntry.title,
                )
            )
        ).all()

    async def skills(self, user_id: UUID) -> Sequence[ProfileSkill]:
        """The user's skills by group, then name"""
        return (
            await self._session.scalars(
                select(ProfileSkill)
                .where(ProfileSkill.user_id == user_id)
                .order_by(ProfileSkill.group, ProfileSkill.name)
            )
        ).all()


__all__ = ["ProfileRepository"]
