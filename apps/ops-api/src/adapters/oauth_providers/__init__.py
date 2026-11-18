from __future__ import annotations

from src.adapters.oauth_providers.base import OAuthIdentity, OAuthProvider
from src.adapters.oauth_providers.exceptions import OAuthFailed
from src.adapters.oauth_providers.factory import build_providers
from src.adapters.oauth_providers.github import GitHubProvider
from src.adapters.oauth_providers.oidc import OIDCProvider

__all__ = [
    "GitHubProvider",
    "OAuthFailed",
    "OAuthIdentity",
    "OAuthProvider",
    "OIDCProvider",
    "build_providers",
]
