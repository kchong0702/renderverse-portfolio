from __future__ import annotations

from uuid import UUID

from src.db.repository import Repository
from src.features.settings.models import UserSettings


class SettingsRepository(Repository):
    async def get(self, user_id: UUID) -> UserSettings | None:
        return await self._session.get(UserSettings, user_id)


__all__ = ["SettingsRepository"]
