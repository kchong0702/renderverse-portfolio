from __future__ import annotations

from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Cookie, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from src.adapters.oauth_providers import OAuthFailed, OAuthIdentity, OAuthProvider
from src.core.auth.dependencies import (
    SESSION_COOKIE,
    AuthServiceDep,
    CurrentUserDep,
    OAuthProvidersDep,
    current_user,
)
from src.core.auth.enums import Role
from src.core.auth.models import PASSWORD
from src.core.auth.service import AuthService
from src.core.auth.types import Timezone
from src.core.config import AuthSettings, get_settings
from src.core.exceptions import (
    Conflict,
    Forbidden,
    InvalidInput,
    NotFound,
    Unauthorized,
)

router = APIRouter(tags=["auth"])


class MeRead(BaseModel):
    id: UUID
    email: str
    role: Role


class ProviderRead(BaseModel):
    name: str
    """The name in the provider's sign-in URLs"""

    label: str
    """The provider's name on its sign-in button"""


class SignInMethods(BaseModel):
    required: bool
    """False while auth is disabled: every request is auth.dev_email"""

    password: bool
    """Whether a password signs in"""

    providers: list[ProviderRead]
    """The providers set up on this server"""


class PasswordSignIn(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)
    timezone: Timezone
    """The IANA time zone of the browser signing in"""


class IdentityRead(BaseModel):
    provider: str
    """The sign-in method: password, or a provider's name"""

    label: str | None
    """The provider's name on its button; None for a password, or a provider no
    longer in the settings"""

    email: str | None
    """The linked account's email; None while it is not linked"""

    configured: bool
    """Whether the method can be connected on this server"""


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


def _settings_page(settings: AuthSettings, error: str) -> RedirectResponse:
    """Back to ops-web's settings with why linking an account failed"""
    query = urlencode({"link_error": error})
    return RedirectResponse(
        f"{settings.web_url}/settings?{query}", status.HTTP_303_SEE_OTHER
    )


def _provider(providers: dict[str, OAuthProvider], provider: str) -> OAuthProvider:
    client = providers.get(provider)
    if client is None:
        raise NotFound(f"Sign in with {provider} is not set up")
    return client


async def _authorize(
    client: OAuthProvider, request: Request, provider: str, next_path: str
) -> Response:
    """Send the user to the provider, coming back through the web callback to next"""
    request.session["next"] = _safe_next(next_path)
    callback = request.url_for("finish_oauth", provider=provider)
    return await client.authorize_redirect(
        request, f"{get_settings().auth.web_url}{callback.path}"
    )


async def _finish_link(
    request: Request,
    service: AuthService,
    provider: str,
    identity: OAuthIdentity,
    user_id: str,
    next_path: str,
) -> RedirectResponse:
    """Link the account to the user who started linking, if they are still signed in,
    and go back to ops-web"""
    try:
        user = await current_user(service, request.cookies.get(SESSION_COOKIE))
    except Unauthorized:
        return _settings_page(service.settings, "failed")
    if str(user.id) != user_id:
        return _settings_page(service.settings, "failed")
    try:
        await service.link_identity(user, provider, identity)
    except Conflict:
        return _settings_page(service.settings, "taken")
    except InvalidInput:
        return _settings_page(service.settings, "unverified")
    return RedirectResponse(
        f"{service.settings.web_url}{next_path}", status.HTTP_303_SEE_OTHER
    )


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
        providers=[
            ProviderRead(name=name, label=get_settings().auth.provider_labels[name])
            for name in providers
        ],
    )


@router.post("/auth/password", status_code=status.HTTP_204_NO_CONTENT)
async def sign_in_with_password(
    body: PasswordSignIn,
    request: Request,
    response: Response,
    service: AuthServiceDep,
) -> None:
    """Sign in with an email and password and set the session cookie"""
    user = await service.sign_in_with_password(
        body.email, body.password, request.client.host if request.client else ""
    )
    token = await service.create_session(
        user, body.timezone, request.headers.get("user-agent", "")
    )
    _set_session_cookie(response, token, service.settings)


@router.get("/auth/{provider}/login")
async def start_oauth(
    provider: str,
    request: Request,
    providers: OAuthProvidersDep,
    timezone: Annotated[Timezone, Query()],
    next_path: Annotated[str, Query(alias="next")] = "/",
) -> Response:
    """Send the user to the provider to approve the sign-in from a browser in
    timezone"""
    client = _provider(providers, provider)
    request.session.pop("link_user", None)
    request.session["timezone"] = timezone
    return await _authorize(client, request, provider, next_path)


@router.get("/auth/{provider}/link")
async def start_link(
    provider: str,
    request: Request,
    user: CurrentUserDep,
    providers: OAuthProvidersDep,
    next_path: Annotated[str, Query(alias="next")] = "/settings",
) -> Response:
    """Send the signed-in user to the provider to approve linking the account"""
    client = _provider(providers, provider)
    request.session["link_user"] = str(user.id)
    return await _authorize(client, request, provider, next_path)


@router.get("/auth/{provider}/callback")
async def finish_oauth(
    provider: str,
    request: Request,
    service: AuthServiceDep,
    providers: OAuthProvidersDep,
) -> RedirectResponse:
    """Finish the provider's sign-in or link, set the session cookie on sign-in and
    go back to ops-web"""
    client = _provider(providers, provider)
    next_path = _safe_next(request.session.pop("next", "/"))
    link_user = request.session.pop("link_user", None)
    try:
        identity = await client.fetch_identity(request)
    except OAuthFailed:
        if link_user is not None:
            return _settings_page(service.settings, "failed")
        return _sign_in_page(service.settings, "failed")
    if link_user is not None:
        return await _finish_link(
            request, service, provider, identity, link_user, next_path
        )
    try:
        user = await service.sign_in_with_identity(provider, identity)
    except Forbidden:
        return _sign_in_page(service.settings, "not_allowed")

    token = await service.create_session(
        user,
        request.session.pop("timezone", service.settings.dev_timezone),
        request.headers.get("user-agent", ""),
    )
    response = RedirectResponse(
        f"{service.settings.web_url}{next_path}", status.HTTP_303_SEE_OTHER
    )
    _set_session_cookie(response, token, service.settings)
    return response


@router.get("/auth/identities")
async def read_identities(
    user: CurrentUserDep, service: AuthServiceDep, providers: OAuthProvidersDep
) -> list[IdentityRead]:
    """The password, every provider in the settings and every account still linked,
    each with the account's email and whether it can be linked"""
    labels = service.settings.provider_labels
    linked = {
        identity.provider: identity.email for identity in await service.identities(user)
    }
    return [
        IdentityRead(
            provider=provider,
            label=labels.get(provider),
            email=linked.get(provider),
            configured=provider == PASSWORD or provider in providers,
        )
        for provider in dict.fromkeys([PASSWORD, *labels, *linked])
    ]


@router.delete("/auth/identities/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_identity(
    provider: str, user: CurrentUserDep, service: AuthServiceDep
) -> None:
    """Remove one way the signed-in user signs in, never the last"""
    await service.unlink(user, provider)


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
