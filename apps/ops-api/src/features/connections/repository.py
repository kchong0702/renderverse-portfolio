from __future__ import annotations

from uuid import UUID

from sqlalchemy import JSON, func, literal, update
from sqlalchemy.dialects.postgresql import JSONB

from src.db.repository import Repository
from src.features.connections.enums import Provider
from src.features.connections.models import Connection


class ConnectionRepository(Repository):
    async def get(self, user_id: UUID, provider: Provider) -> Connection | None:
        """The user's connection to the provider, if any"""
        return await self._session.get(Connection, (user_id, provider))

    async def record_quota(
        self,
        user_id: UUID,
        provider: Provider,
        remaining: int | None,
        limit: int | None,
    ) -> None:
        """Merge the quota into the connection's details in one statement; no row
        changes when it is gone"""
        quota = {"quota_remaining": remaining, "quota_limit": limit}
        details = (
            Connection.details.op("||")(literal(quota, JSONB))
            if self._session.get_bind().dialect.name == "postgresql"
            else func.json_patch(Connection.details, literal(quota, JSON))
        )
        await self._session.execute(
            update(Connection)
            .where(Connection.user_id == user_id, Connection.provider == provider)
            .values(details=details)
        )


__all__ = ["ConnectionRepository"]
