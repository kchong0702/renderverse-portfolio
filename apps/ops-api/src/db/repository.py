from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import Base
from src.db.mixins import UserScopedMixin


class Repository:
    def __init__(self, session: AsyncSession):
        """Run every query on the session the service holds"""
        self._session = session

    async def add[T: Base](self, row: T) -> T:
        """Insert a row and flush it so its defaults are filled in"""
        self._session.add(row)
        await self._session.flush()
        return row

    async def delete(self, row: Base) -> None:
        """Remove a row"""
        await self._session.delete(row)
        await self._session.flush()

    async def owned[T: UserScopedMixin](
        self, model: type[T], user_id: UUID, row_id: UUID
    ) -> T | None:
        """The row with this id, or None when it is missing or not the user's"""
        row = await self._session.get(model, row_id)
        return row if row is not None and row.user_id == user_id else None


__all__ = ["Repository"]
