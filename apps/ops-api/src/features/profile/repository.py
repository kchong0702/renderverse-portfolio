from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql, sqlite

from src.db.repository import Repository
from src.features.imports import Import, ImportStatus
from src.features.profile.models import (
    Networking,
    Profile,
    ProfileChange,
    ProfileEntry,
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

    async def lock(self, user_id: UUID) -> None:
        """Hold the user's profile against other transactions until this one ends;
        only Postgres locks"""
        if self._session.get_bind().dialect.name == "postgresql":
            await self._session.execute(
                select(
                    func.pg_advisory_xact_lock(func.hashtextextended(str(user_id), 0))
                )
            )

    async def imported(self, user_id: UUID, file_id: UUID, import_id: UUID) -> bool:
        """Whether another import of the user's file is done already"""
        return (
            await self._session.scalar(
                select(Import.id)
                .where(
                    Import.user_id == user_id,
                    Import.file_id == file_id,
                    Import.status == ImportStatus.DONE,
                    Import.id != import_id,
                )
                .limit(1)
            )
            is not None
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
