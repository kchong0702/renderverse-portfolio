from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx2
from authlib.integrations.starlette_client import OAuthError, StarletteOAuth2App
from starlette.requests import Request
from starlette.responses import Response

from src.adapters.oauth_providers.exceptions import OAuthFailed


@dataclass(frozen=True)
class OAuthIdentity:
    subject: str
    """The provider's stable account id"""

    emails: list[str]
    """Verified emails, lowercased, primary first"""


class OAuthProvider(ABC):
    """Base for every sign-in provider: Authlib keeps the state, PKCE verifier and
    nonce in Starlette's session cookie between the redirect and the callback"""

    def __init__(self, client: StarletteOAuth2App):
        self._client = client

    async def authorize_redirect(self, request: Request, redirect_uri: str) -> Response:
        return await self._client.authorize_redirect(request, redirect_uri)

    async def fetch_token(self, request: Request) -> dict[str, Any]:
        try:
            return await self._client.authorize_access_token(request)
        except (OAuthError, httpx2.HTTPError) as error:
            raise OAuthFailed(str(error)) from error

    @abstractmethod
    async def fetch_identity(self, request: Request) -> OAuthIdentity:
        """The account behind the callback; raises OAuthFailed if there is none"""


__all__ = ["OAuthIdentity", "OAuthProvider"]
