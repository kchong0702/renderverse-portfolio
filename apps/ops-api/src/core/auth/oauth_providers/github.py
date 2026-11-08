from __future__ import annotations

from typing import override

import httpx2
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request

from src.core.auth.exceptions import OAuthFailed
from src.core.auth.oauth_providers.base import (
    AuthlibAdapter,
    OAuthIdentity,
)
from src.core.config import GitHubOAuthSettings


class GitHubAdapter(AuthlibAdapter):
    """Sign in with GitHub: OAuth 2 with PKCE, emails from the user API"""

    def __init__(self, settings: GitHubOAuthSettings):
        oauth = OAuth()
        oauth.register(
            "github",
            client_id=settings.client_id,
            client_secret=settings.client_secret.get_secret_value(),
            authorize_url=settings.authorize_url,
            access_token_url=settings.access_token_url,
            api_base_url=settings.api_base_url,
            client_kwargs={"scope": settings.scope, "code_challenge_method": "S256"},
        )
        super().__init__(oauth.create_client("github"))

    @override
    async def fetch_identity(self, request: Request) -> OAuthIdentity:
        token = await self.fetch_token(request)
        try:
            user = await self._client.get("user", token=token)
            emails = await self._client.get("user/emails", token=token)
            user.raise_for_status()
            emails.raise_for_status()
        except httpx2.HTTPError as error:
            raise OAuthFailed(str(error)) from error

        verified = [e for e in emails.json() if e.get("verified")]
        verified.sort(key=lambda e: not e.get("primary"))
        return OAuthIdentity(
            subject=str(user.json()["id"]),
            emails=[e["email"].lower() for e in verified],
        )


__all__ = ["GitHubAdapter"]
