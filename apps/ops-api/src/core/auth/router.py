from __future__ import annotations

from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from src.core.auth.dependencies import (
    SESSION_COOKIE,
    current_user,
    get_auth_service,
    get_oauth_providers,
)
from src.core.auth.errors import OAuthFailed
from src.core.auth.models import User
from src.core.auth.oauth_providers import AuthlibAdapter, Provider
from src.core.auth.service import AuthService
from src.core.config import AuthSettings, get_settings
from src.core.errors import Forbidden, NotFound

router = APIRouter(tags=["auth"])


class MeRead(BaseModel):
    id: UUID
    email: str


class SignInMethods(BaseModel):
    required: bool
    """False while auth is disabled: every request is auth.dev_email"""

    password: bool
    google: bool
    github: bool


class PasswordSignIn(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)


def _set_session_cookie(response: Response, token: str, settings: AuthSettings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_idle_days * 24 * 60 * 60,
        path=get_settings().app.route_prefix,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
    )


def _safe_next(path: str) -> str:
    """Only paths on ops-web itself, never another site"""
    return path if path.startswith("/") and not path.startswith("//") else "/"


def _sign_in_page(settings: AuthSettings, error: str) -> RedirectResponse:
    query = urlencode({"error": error})
    return RedirectResponse(
        f"{settings.web_url}/sign-in?{query}", status.HTTP_303_SEE_OTHER
    )


def _provider(
    providers: dict[Provider, AuthlibAdapter], provider: Provider
) -> AuthlibAdapter:
    client = providers.get(provider)
    if client is None:
        raise NotFound(f"Sign in with {provider} is not set up")
    return client


@router.get("/me")
async def read_me(user: Annotated[User, Depends(current_user)]) -> MeRead:
    return MeRead(id=user.id, email=user.email)


@router.get("/auth/methods")
async def read_sign_in_methods(
    providers: Annotated[dict[Provider, AuthlibAdapter], Depends(get_oauth_providers)],
) -> SignInMethods:
    return SignInMethods(
        required=get_settings().auth.enabled,
        password=True,
        google="google" in providers,
        github="github" in providers,
    )


@router.post("/auth/password", status_code=status.HTTP_204_NO_CONTENT)
async def sign_in_with_password(
    body: PasswordSignIn,
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    user = await service.sign_in_with_password(body.email, body.password)
    token = await service.create_session(user, request.headers.get("user-agent", ""))
    _set_session_cookie(response, token, service.settings)


@router.get("/auth/{provider}/login")
async def start_oauth(
    provider: Provider,
    request: Request,
    providers: Annotated[dict[Provider, AuthlibAdapter], Depends(get_oauth_providers)],
    next_path: Annotated[str, Query(alias="next")] = "/",
) -> Response:
    client = _provider(providers, provider)
    request.session["next"] = _safe_next(next_path)
    callback = request.url_for("finish_oauth", provider=provider)
    return await client.authorize_redirect(
        request, f"{get_settings().auth.web_url}{callback.path}"
    )


@router.get("/auth/{provider}/callback")
async def finish_oauth(
    provider: Provider,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    providers: Annotated[dict[Provider, AuthlibAdapter], Depends(get_oauth_providers)],
) -> RedirectResponse:
    client = _provider(providers, provider)
    next_path = _safe_next(request.session.pop("next", "/"))
    try:
        identity = await client.fetch_identity(request)
    except OAuthFailed:
        return _sign_in_page(service.settings, "failed")
    try:
        user = await service.sign_in_with_identity(provider, identity)
    except Forbidden:
        return _sign_in_page(service.settings, "not_allowed")

    token = await service.create_session(user, request.headers.get("user-agent", ""))
    response = RedirectResponse(
        f"{service.settings.web_url}{next_path}", status.HTTP_303_SEE_OTHER
    )
    _set_session_cookie(response, token, service.settings)
    return response


@router.post("/auth/sign-out", status_code=status.HTTP_204_NO_CONTENT)
async def sign_out(
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    if token:
        await service.end_session(token)
    response.delete_cookie(
        SESSION_COOKIE,
        path=get_settings().app.route_prefix,
        httponly=True,
        secure=service.settings.secure_cookies,
        samesite="lax",
    )


__all__ = ["router"]
