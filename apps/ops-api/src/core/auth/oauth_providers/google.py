from __future__ import annotations

from typing import override

from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request

from src.core.auth.errors import OAuthFailed
from src.core.auth.oauth_providers.base import (
    AuthlibAdapter,
    OAuthIdentity,
)
from src.core.config import GoogleOAuthSettings


class GoogleAdapter(AuthlibAdapter):
    """Sign in with Google: OpenID Connect with PKCE and a nonce"""

    def __init__(self, settings: GoogleOAuthSettings):
        oauth = OAuth()
        oauth.register(
            "google",
            client_id=settings.client_id,
            client_secret=settings.client_secret.get_secret_value(),
            server_metadata_url=settings.discovery_url,
            client_kwargs={"scope": settings.scope, "code_challenge_method": "S256"},
        )
        super().__init__(oauth.create_client("google"))

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


__all__ = ["GoogleAdapter"]
