from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth.models import User
from src.core.auth.oauth_providers import AuthlibAdapter, Provider
from src.core.auth.repository import AuthRepository
from src.core.auth.service import AuthService
from src.core.config import get_settings
from src.core.db.actor import set_actor, user_actor
from src.core.db.session import get_session
from src.core.errors import Unauthorized

SESSION_COOKIE = "ops_session"


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthService:
    return AuthService(AuthRepository(session), get_settings().auth)


def get_oauth_providers(request: Request) -> dict[Provider, AuthlibAdapter]:
    return request.app.state.oauth_providers


async def current_user(
    service: Annotated[AuthService, Depends(get_auth_service)],
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    """The signed-in, allowlisted caller, who the request's writes are stamped with"""
    if not service.settings.enabled:
        user = await service.dev_user()
    else:
        user = await service.resolve_session(token) if token else None
        if user is None:
            raise Unauthorized("Sign in to continue")
    set_actor(user_actor(user.id))
    return user


__all__ = [
    "SESSION_COOKIE",
    "current_user",
    "get_auth_service",
    "get_oauth_providers",
]
