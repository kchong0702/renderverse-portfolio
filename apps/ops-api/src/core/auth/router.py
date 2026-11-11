from __future__ import annotations

from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Cookie, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from src.core.auth.dependencies import (
    SESSION_COOKIE,
    AuthServiceDep,
    CurrentUserDep,
    OAuthProvidersDep,
)
from src.core.auth.enums import Role
from src.core.auth.exceptions import OAuthFailed
from src.core.auth.oauth_providers import AuthlibAdapter, Provider
from src.core.config import AuthSettings, get_settings
from src.core.exceptions import Forbidden, NotFound

router = APIRouter(tags=["auth"])


class MeRead(BaseModel):
    id: UUID
    email: str
    role: Role


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
async def read_me(user: CurrentUserDep) -> MeRead:
    """The signed-in user"""
    return MeRead(id=user.id, email=user.email, role=user.role)


@router.get("/auth/methods")
async def read_sign_in_methods(providers: OAuthProvidersDep) -> SignInMethods:
    """Whether sign-in is required, and the ways to sign in"""
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
    service: AuthServiceDep,
) -> None:
    """Sign in with an email and password and set the session cookie"""
    user = await service.sign_in_with_password(body.email, body.password)
    token = await service.create_session(user, request.headers.get("user-agent", ""))
    _set_session_cookie(response, token, service.settings)


@router.get("/auth/{provider}/login")
async def start_oauth(
    provider: Provider,
    request: Request,
    providers: OAuthProvidersDep,
    next_path: Annotated[str, Query(alias="next")] = "/",
) -> Response:
    """Send the user to the provider to approve the sign-in"""
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
    service: AuthServiceDep,
    providers: OAuthProvidersDep,
) -> RedirectResponse:
    """Finish the provider's sign-in, set the session cookie and go back to ops-web"""
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
    service: AuthServiceDep,
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    """End the session and clear its cookie"""
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
