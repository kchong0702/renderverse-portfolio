from __future__ import annotations

from src.adapters.oauth_providers.base import (
    AuthlibAdapter,
    OAuthIdentity,
    Provider,
)
from src.adapters.oauth_providers.exceptions import OAuthFailed
from src.adapters.oauth_providers.factory import build_providers
from src.adapters.oauth_providers.github import GitHubAdapter
from src.adapters.oauth_providers.google import GoogleAdapter

__all__ = [
    "AuthlibAdapter",
    "GitHubAdapter",
    "GoogleAdapter",
    "OAuthFailed",
    "OAuthIdentity",
    "Provider",
    "build_providers",
]
