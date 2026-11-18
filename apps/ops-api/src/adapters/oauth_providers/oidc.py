from __future__ import annotations

from typing import override

from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request

from src.adapters.oauth_providers.base import OAuthIdentity, OAuthProvider
from src.adapters.oauth_providers.exceptions import OAuthFailed
from src.core.config import OIDCSettings


class OIDCProvider(OAuthProvider):
    """Sign in with any OpenID Connect provider: PKCE and a nonce, the account read
    from the ID token"""

    def __init__(self, name: str, settings: OIDCSettings):
        """The provider at settings.config_url, registered with Authlib as name"""
        oauth = OAuth()
        oauth.register(
            name,
            client_id=settings.client_id,
            client_secret=settings.client_secret.get_secret_value(),
            server_metadata_url=settings.config_url,
            client_kwargs={"scope": settings.scope, "code_challenge_method": "S256"},
        )
        super().__init__(oauth.create_client(name))

    @override
    async def fetch_identity(self, request: Request) -> OAuthIdentity:
        userinfo = (await self.fetch_token(request)).get("userinfo") or {}
        subject, email = userinfo.get("sub"), userinfo.get("email")
        if not subject:
            raise OAuthFailed("The ID token has no subject")
        emails = (
            [email.lower()]
            if isinstance(email, str) and userinfo.get("email_verified") is True
            else []
        )
        return OAuthIdentity(subject=str(subject), emails=emails)


__all__ = ["OIDCProvider"]
