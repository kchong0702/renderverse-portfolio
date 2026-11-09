from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.profile.models import Profile, ProfileEntry, ProfileSkill


class ProfileRepository:
    def __init__(self, session: AsyncSession):
        """Run every query on the request's session"""
        self._session = session

    async def profile(self, user_id: UUID) -> Profile | None:
        """The user's profile row, if it exists yet"""
        return await self._session.get(Profile, user_id)

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

    async def entry(self, user_id: UUID, entry_id: UUID) -> ProfileEntry | None:
        """One of the user's entries, or None when it is not theirs"""
        entry = await self._session.get(ProfileEntry, entry_id)
        return entry if entry is not None and entry.user_id == user_id else None

    async def skills(self, user_id: UUID) -> Sequence[ProfileSkill]:
        """The user's skills by group, then name"""
        return (
            await self._session.scalars(
                select(ProfileSkill)
                .where(ProfileSkill.user_id == user_id)
                .order_by(ProfileSkill.group, ProfileSkill.name)
            )
        ).all()

    async def skill(self, user_id: UUID, skill_id: UUID) -> ProfileSkill | None:
        """One of the user's skills, or None when it is not theirs"""
        skill = await self._session.get(ProfileSkill, skill_id)
        return skill if skill is not None and skill.user_id == user_id else None

    async def add[T: Profile | ProfileEntry | ProfileSkill](self, row: T) -> T:
        """Insert a row and flush it so its defaults are filled in"""
        self._session.add(row)
        await self._session.flush()
        return row

    async def delete(self, row: ProfileEntry | ProfileSkill) -> None:
        """Remove a row"""
        await self._session.delete(row)
        await self._session.flush()


__all__ = ["ProfileRepository"]
