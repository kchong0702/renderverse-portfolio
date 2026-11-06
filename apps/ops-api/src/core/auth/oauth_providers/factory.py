from __future__ import annotations

from src.core.auth.oauth_providers.base import AuthlibAdapter, Provider
from src.core.auth.oauth_providers.github import GitHubAdapter
from src.core.auth.oauth_providers.google import GoogleAdapter
from src.core.config import AuthSettings


def build_providers(settings: AuthSettings) -> dict[Provider, AuthlibAdapter]:
    """The providers with credentials configured"""
    providers: dict[Provider, AuthlibAdapter] = {}
    if settings.google.configured:
        providers["google"] = GoogleAdapter(settings.google)
    if settings.github.configured:
        providers["github"] = GitHubAdapter(settings.github)
    return providers


__all__ = ["build_providers"]
