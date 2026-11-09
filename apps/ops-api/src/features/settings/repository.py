from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.features.settings.models import UserSettings


class SettingsRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, user_id: UUID) -> UserSettings | None:
        return await self._session.get(UserSettings, user_id)

    async def add(self, settings: UserSettings) -> UserSettings:
        self._session.add(settings)
        await self._session.flush()
        return settings


__all__ = ["SettingsRepository"]
