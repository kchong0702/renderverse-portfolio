from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql, sqlite

from src.db.repository import Repository
from src.features.profile.models import (
    Networking,
    Profile,
    ProfileChange,
    ProfileEntry,
    ProfileImport,
    ProfileSkill,
)


class ProfileRepository(Repository):
    async def profile(self, user_id: UUID) -> Profile | None:
        """The user's profile row, if it exists yet"""
        return await self._session.get(Profile, user_id)

    async def networking(self, user_id: UUID) -> Networking | None:
        """The user's Networking copy row, if it exists yet"""
        return await self._session.get(Networking, user_id)

    async def create[T: (Profile, Networking)](
        self, model: type[T], user_id: UUID
    ) -> T:
        """Insert an empty row of the model unless the user has one, and return the
        user's row"""
        dialect = self._session.get_bind().dialect.name
        insert = postgresql.insert if dialect == "postgresql" else sqlite.insert
        await self._session.execute(
            insert(model).values(user_id=user_id).on_conflict_do_nothing()
        )
        return await self._session.get_one(model, user_id)

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

    async def imports(self, user_id: UUID) -> Sequence[ProfileImport]:
        """The user's imports, the latest first"""
        return (
            await self._session.scalars(
                select(ProfileImport)
                .where(ProfileImport.user_id == user_id)
                .order_by(ProfileImport.created_at.desc())
            )
        ).all()

    async def imported(self, user_id: UUID, digest: str) -> ProfileImport | None:
        """The user's earlier import of the file with this sha256, if any"""
        return await self._session.scalar(
            select(ProfileImport)
            .where(ProfileImport.user_id == user_id, ProfileImport.digest == digest)
            .limit(1)
        )

    async def changes(self, user_id: UUID) -> list[ProfileChange]:
        """The user's pending changes, the oldest first"""
        return list(
            (
                await self._session.scalars(
                    select(ProfileChange)
                    .where(ProfileChange.user_id == user_id)
                    .order_by(ProfileChange.created_at, ProfileChange.id)
                )
            ).all()
        )

    async def flush(self) -> None:
        """Write pending changes so defaults and updated_at are filled in"""
        await self._session.flush()


__all__ = ["ProfileRepository"]
