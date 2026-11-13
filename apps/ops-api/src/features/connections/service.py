from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import Conflict, ServiceUnavailable
from src.db.base import utcnow
from src.features.connections.enums import Provider
from src.features.connections.models import Connection
from src.features.connections.repository import ConnectionRepository
from src.features.connections.schemas import GoogleDetails, JSearchDetails


class ConnectionService:
    def __init__(
        self,
        session: AsyncSession,
        provider: Provider,
        key: SecretStr,
        label: str,
        unreadable: str,
    ):
        """Keep the user's connections to one provider, named by label, through a
        repository on the session, encrypting secrets with the provider's Fernet key"""
        self._repository = ConnectionRepository(session)
        self._provider = provider
        self._key = key
        self._label = label
        self._unreadable = unreadable

    def _fernet(self) -> Fernet:
        """The cipher for the provider's secrets; ServiceUnavailable without a key"""
        if not self._key.get_secret_value():
            raise ServiceUnavailable(
                f"{self._label} keys are not set up on the server: set "
                f"OPS_API_{self._provider.name}__ENCRYPTION_KEY"
            )
        return Fernet(self._key.get_secret_value())

    async def get(self, user_id: UUID) -> Connection | None:
        """The user's connection, or None when not connected"""
        return await self._repository.get(user_id, self._provider)

    def secret(self, connection: Connection) -> str:
        """The connection's secret in plain text; Conflict with the unreadable message
        when the key has changed"""
        try:
            return self._fernet().decrypt(connection.secret).decode()
        except InvalidToken as error:
            raise Conflict(self._unreadable) from error

    async def connect(
        self,
        user_id: UUID,
        secret: str,
        account: str = "",
        scopes: Sequence[str] = (),
    ) -> None:
        """Store the secret, encrypted, in place of any earlier one, whose quota no
        longer applies"""
        ciphertext = self._fernet().encrypt(secret.encode())
        connection = await self.get(user_id) or Connection(
            user_id=user_id, provider=self._provider
        )
        connection.account = account
        connection.secret = ciphertext
        match self._provider:
            case Provider.GOOGLE:
                connection.details = GoogleDetails(scopes=list(scopes))
            case Provider.JSEARCH:
                connection.details = JSearchDetails()
        connection.connected_at = utcnow()
        await self._repository.add(connection)

    async def record_quota(
        self, user_id: UUID, remaining: int | None, limit: int | None
    ) -> None:
        """Keep the quota a run read on the user's secret; a no-op when not connected"""
        await self._repository.record_quota(user_id, self._provider, remaining, limit)

    async def disconnect(self, user_id: UUID) -> None:
        """Forget the user's secret and its quota; a no-op when not connected"""
        connection = await self.get(user_id)
        if connection is not None:
            await self._repository.delete(connection)


def api_key_connections(
    session: AsyncSession, provider: Provider, key: SecretStr, label: str
) -> ConnectionService:
    """The users' API keys to the provider, named by label, on the session, encrypted
    with key"""
    return ConnectionService(
        session,
        provider,
        key,
        label,
        f"Ops can no longer read your {label} key; change it in Settings",
    )


__all__ = ["ConnectionService", "api_key_connections"]
