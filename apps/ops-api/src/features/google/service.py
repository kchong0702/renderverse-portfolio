from __future__ import annotations

from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.google import RECONNECT, SCOPES, GoogleClient
from src.core.config import GoogleSettings
from src.core.exceptions import Conflict, InvalidInput, ServiceUnavailable
from src.features.google.models import GoogleAccount
from src.features.google.repository import GoogleRepository

_NOT_CONFIGURED = (
    "Google is not set up on the server: set OPS_API_GOOGLE__CLIENT_ID, "
    "OPS_API_GOOGLE__CLIENT_SECRET and OPS_API_GOOGLE__ENCRYPTION_KEY"
)


class GoogleService:
    def __init__(
        self,
        session: AsyncSession,
        client: GoogleClient,
        settings: GoogleSettings,
    ):
        """Read and write the Google account through a repository on the session, and
        keep the Google client and the OAuth settings"""
        self._repository = GoogleRepository(session)
        self._client = client
        self._settings = settings

    @property
    def configured(self) -> bool:
        """Whether the server has the OAuth client and encryption key to connect"""
        return self._settings.configured

    def _fernet(self) -> Fernet:
        """The cipher for refresh tokens; ServiceUnavailable until Google is set up"""
        if not self.configured:
            raise ServiceUnavailable(_NOT_CONFIGURED)
        return Fernet(self._settings.encryption_key.get_secret_value())

    def _refresh_token(self, account: GoogleAccount) -> str:
        """The stored refresh token; Conflict when the encryption key has changed"""
        try:
            return self._fernet().decrypt(account.ciphertext).decode()
        except InvalidToken as error:
            raise Conflict(RECONNECT) from error

    async def account(self, user_id: UUID) -> str | None:
        """The connected Gmail address, or None when Google is not connected"""
        account = await self._repository.get(user_id)
        return account.email if account is not None else None

    def authorize_url(self, state: str) -> str:
        """Google's consent page, carrying the state the callback must echo"""
        if not self.configured:
            raise ServiceUnavailable(_NOT_CONFIGURED)
        return self._client.authorize_url(state)

    async def connect(self, user_id: UUID, code: str) -> None:
        """Exchange the callback's code and store the refresh token, encrypted;
        InvalidInput when the user did not allow both Gmail and Calendar"""
        fernet = self._fernet()
        tokens = await self._client.exchange_code(code)
        if not set(SCOPES) <= set(tokens.scope.split()):
            raise InvalidInput("Allow both Gmail and Calendar access to connect")
        if tokens.refresh_token is None:
            raise ServiceUnavailable("Google sent no refresh token; connect again")

        email = await self._client.email(tokens.access_token)
        ciphertext = fernet.encrypt(tokens.refresh_token.encode())
        account = await self._repository.get(user_id)
        if account is None:
            await self._repository.add(
                GoogleAccount(user_id=user_id, email=email, ciphertext=ciphertext)
            )
        else:
            account.email = email
            account.ciphertext = ciphertext

    async def disconnect(self, user_id: UUID) -> None:
        """Revoke Ops's access at Google and forget the token; a no-op if not connected"""
        account = await self._repository.get(user_id)
        if account is None:
            return
        await self._client.revoke(self._refresh_token(account))
        await self._repository.delete(account)

    async def access_token(self, user_id: UUID) -> str:
        """A fresh access token for the user's Gmail and Calendar;
        Conflict when Google is not connected or the grant no longer works"""
        account = await self._repository.get(user_id)
        if account is None:
            raise Conflict("Connect a Google account in Settings first")
        return await self._client.refresh(self._refresh_token(account))


__all__ = ["GoogleService"]
