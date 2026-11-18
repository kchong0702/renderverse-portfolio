from __future__ import annotations

from src.adapters.oauth_providers.base import OAuthProvider
from src.adapters.oauth_providers.github import GitHubProvider
from src.adapters.oauth_providers.oidc import OIDCProvider
from src.core.config import AuthSettings


def build_providers(settings: AuthSettings) -> dict[str, OAuthProvider]:
    """The providers with credentials configured, keyed by the name in their URLs"""
    providers: dict[str, OAuthProvider] = {
        name: OIDCProvider(name, oidc)
        for name, oidc in settings.oidc.items()
        if oidc.configured
    }
    if settings.github.configured:
        providers["github"] = GitHubProvider(settings.github)
    return providers


__all__ = ["build_providers"]
