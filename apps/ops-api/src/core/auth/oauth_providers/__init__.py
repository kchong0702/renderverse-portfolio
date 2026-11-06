from __future__ import annotations

from src.core.auth.oauth_providers.base import (
    AuthlibAdapter,
    OAuthIdentity,
    Provider,
)
from src.core.auth.oauth_providers.factory import build_providers
from src.core.auth.oauth_providers.github import GitHubAdapter
from src.core.auth.oauth_providers.google import GoogleAdapter

__all__ = [
    "AuthlibAdapter",
    "GitHubAdapter",
    "GoogleAdapter",
    "OAuthIdentity",
    "Provider",
    "build_providers",
]
