from __future__ import annotations

from contextlib import suppress
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.google import RECONNECT, GoogleClient
from src.core.config import GoogleSettings
from src.core.exceptions import Conflict, InvalidInput, ServiceUnavailable
from src.features.connections import ConnectionService, GoogleDetails, Provider


class GoogleService:
    def __init__(
        self,
        session: AsyncSession,
        client: GoogleClient,
        settings: GoogleSettings,
    ):
        """Keep the Google connection through the connection service on the session,
        and keep the Google client and the OAuth settings"""
        self._connections = ConnectionService(
            session, Provider.GOOGLE, settings.encryption_key, "Google", RECONNECT
        )
        self._client = client
        self._settings = settings

    @property
    def configured(self) -> bool:
        """Whether the server has the OAuth client and encryption key to connect"""
        return self._settings.configured

    def _require_configured(self) -> None:
        """Raise ServiceUnavailable, naming what to set, until Google is set up"""
        if not self.configured:
            raise ServiceUnavailable(
                "Google is not set up on the server: set OPS_API_GOOGLE__CLIENT_ID, "
                "OPS_API_GOOGLE__CLIENT_SECRET and OPS_API_GOOGLE__ENCRYPTION_KEY"
            )

    async def email(self, user_id: UUID) -> str | None:
        """The connected Gmail address, or None when Google is not connected"""
        connection = await self._connections.get(user_id)
        return connection.account if connection is not None else None

    async def has_scopes(self, user_id: UUID) -> bool:
        """Whether the stored grant allows every scope Ops now asks Google for"""
        connection = await self._connections.get(user_id)
        return (
            connection is not None
            and isinstance(connection.details, GoogleDetails)
            and set(self._settings.scopes) <= set(connection.details.scopes)
        )

    def authorize_url(self, state: str) -> str:
        """Google's consent page, carrying the state the callback must echo"""
        self._require_configured()
        return self._client.authorize_url(state)

    async def connect(self, user_id: UUID, code: str) -> None:
        """Exchange the callback's code and store the refresh token, encrypted;
        InvalidInput when the user did not allow every scope Ops asks for"""
        self._require_configured()
        tokens = await self._client.exchange_code(code)
        if not set(self._settings.scopes) <= set(tokens.scope.split()):
            raise InvalidInput(
                "Allow every Gmail and Calendar permission Google asks for to connect"
            )
        if tokens.refresh_token is None:
            raise ServiceUnavailable("Google sent no refresh token; connect again")

        await self._connections.connect(
            user_id,
            tokens.refresh_token,
            account=await self._client.email(tokens.access_token),
            scopes=tokens.scope.split(),
        )

    async def disconnect(self, user_id: UUID) -> None:
        """Revoke Ops's access at Google when the token is readable, then forget it; a
        no-op if not connected"""
        connection = await self._connections.get(user_id)
        if connection is None:
            return
        if self.configured:
            with suppress(Conflict):
                await self._client.revoke(self._connections.secret(connection))
        await self._connections.disconnect(user_id)

    async def refresh_token(self, user_id: UUID) -> str:
        """The user's stored refresh token in plain text; Conflict when Google is not
        connected or the token is unreadable"""
        connection = await self._connections.get(user_id)
        if connection is None:
            raise Conflict("Connect a Google account in Settings first")
        self._require_configured()
        return self._connections.secret(connection)

    async def access_token(self, user_id: UUID) -> str:
        """A fresh access token for the user's Gmail and Calendar;
        Conflict when Google is not connected or the grant no longer works"""
        return await self._client.refresh(await self.refresh_token(user_id))


__all__ = ["GoogleService"]
