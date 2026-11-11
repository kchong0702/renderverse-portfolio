from __future__ import annotations

from uuid import UUID

from sqlalchemy.dialects import postgresql, sqlite

from src.db.repository import Repository
from src.features.settings.models import UserSettings


class SettingsRepository(Repository):
    async def get(self, user_id: UUID) -> UserSettings | None:
        return await self._session.get(UserSettings, user_id)

    async def create(self, user_id: UUID) -> UserSettings:
        """Insert the defaults unless the user has a row, and return the user's row"""
        dialect = self._session.get_bind().dialect.name
        insert = postgresql.insert if dialect == "postgresql" else sqlite.insert
        await self._session.execute(
            insert(UserSettings).values(user_id=user_id).on_conflict_do_nothing()
        )
        return await self._session.get_one(UserSettings, user_id)


__all__ = ["SettingsRepository"]
