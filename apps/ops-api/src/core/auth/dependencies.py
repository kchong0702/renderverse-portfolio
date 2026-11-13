from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, Request

from src.app.actor import set_actor, user_actor
from src.core.auth.enums import Role
from src.core.auth.models import User
from src.core.auth.oauth_providers import AuthlibAdapter, Provider
from src.core.auth.service import AuthService
from src.core.config import get_settings
from src.core.exceptions import Forbidden, Unauthorized
from src.db.session import SessionDep

SESSION_COOKIE = "ops_session"


def get_auth_service(session: SessionDep) -> AuthService:
    """The auth service on the request's database session"""
    return AuthService(session, get_settings().auth)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_oauth_providers(request: Request) -> dict[Provider, AuthlibAdapter]:
    """The OAuth clients the app built at startup, by provider"""
    return request.app.state.oauth_providers


OAuthProvidersDep = Annotated[
    dict[Provider, AuthlibAdapter], Depends(get_oauth_providers)
]


async def current_user(
    service: AuthServiceDep,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    """The signed-in, enabled caller, who the request's writes are stamped with"""
    if not service.settings.enabled:
        user = await service.dev_user()
    else:
        user = await service.resolve_session(token) if token else None
        if user is None:
            raise Unauthorized("Sign in to continue")
    set_actor(user_actor(user.id))
    return user


CurrentUserDep = Annotated[User, Depends(current_user)]


async def admin_user(user: CurrentUserDep) -> User:
    """The signed-in caller, who must be an admin"""
    if user.role is not Role.ADMIN:
        raise Forbidden("Only the admin can use the portfolio")
    return user


AdminDep = Annotated[User, Depends(admin_user)]

__all__ = [
    "SESSION_COOKIE",
    "AdminDep",
    "AuthServiceDep",
    "CurrentUserDep",
    "OAuthProvidersDep",
    "admin_user",
    "current_user",
    "get_auth_service",
    "get_oauth_providers",
]
