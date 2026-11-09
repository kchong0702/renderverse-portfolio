from __future__ import annotations

from uuid import UUID

from src.db.repository import Repository
from src.features.google.models import GoogleAccount


class GoogleRepository(Repository):
    async def get(self, user_id: UUID) -> GoogleAccount | None:
        """The user's connected Google account, if any"""
        return await self._session.get(GoogleAccount, user_id)


__all__ = ["GoogleRepository"]
