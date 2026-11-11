import secrets
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import RedirectResponse

from src.core.auth import CurrentUserDep
from src.core.config import get_settings
from src.core.exceptions import InvalidInput, ServiceException
from src.db.session import SessionDep
from src.features.google.service import GoogleService

router = APIRouter(prefix="/integrations/google", tags=["google"])

_PENDING = "google_connect"


def get_google_service(session: SessionDep, request: Request) -> GoogleService:
    """The Google service on the request's database session"""
    return GoogleService(session, request.app.state.google, get_settings().google)


GoogleServiceDep = Annotated[GoogleService, Depends(get_google_service)]


def _settings_page(error: str) -> RedirectResponse:
    """Back to Settings, saying why connecting Google did not finish"""
    query = urlencode({"google_error": error})
    return RedirectResponse(
        f"{get_settings().auth.web_url}/settings?{query}", status.HTTP_303_SEE_OTHER
    )


@router.get("/connect")
async def connect_google(
    request: Request,
    user: CurrentUserDep,
    service: GoogleServiceDep,
    next_path: Annotated[str, Query(alias="next")] = "/settings",
) -> RedirectResponse:
    """Send the user to Google to allow reading and sending Gmail and reading and
    adding Calendar events"""
    state = secrets.token_urlsafe(32)
    url = service.authorize_url(state)
    request.session[_PENDING] = {
        "state": state,
        "user": str(user.id),
        "next": next_path
        if next_path.startswith("/") and not next_path.startswith("//")
        else "/settings",
    }
    return RedirectResponse(url, status.HTTP_303_SEE_OTHER)


@router.get("/callback")
async def finish_google_connect(
    request: Request,
    user: CurrentUserDep,
    service: GoogleServiceDep,
    code: str = "",
    state: str = "",
    error: str = "",
) -> RedirectResponse:
    """Store the token Google returns for the user who started, then go back"""
    pending: dict[str, str] = request.session.pop(_PENDING, {})
    if error:
        return _settings_page("denied")
    if not (
        code
        and state
        and secrets.compare_digest(state, pending.get("state", ""))
        and pending.get("user") == str(user.id)
    ):
        return _settings_page("failed")
    try:
        await service.connect(user.id, code)
    except InvalidInput:
        return _settings_page("scopes")
    except ServiceException:
        return _settings_page("failed")
    return RedirectResponse(
        f"{get_settings().auth.web_url}{pending['next']}", status.HTTP_303_SEE_OTHER
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_google(user: CurrentUserDep, service: GoogleServiceDep) -> None:
    """Revoke Ops's Google access and forget the stored token"""
    await service.disconnect(user.id)
