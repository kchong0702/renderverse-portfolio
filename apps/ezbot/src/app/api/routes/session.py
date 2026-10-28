from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from src.app.api.schemas.chat import Session as SessionResponse
from src.app.deps import get_session_store, get_settings_dep
from src.app.errors import api_error
from src.core.config import Settings
from src.infrastructure.store.session import (
    SessionStore,
    is_valid_cookie,
    new_cookie,
)
from src.shared.exceptions import SessionCapacityError

router = APIRouter()


@router.post("/session")
async def create_session(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings_dep)],
    store: Annotated[SessionStore, Depends(get_session_store)],
) -> SessionResponse:
    config = settings.session
    cookie = request.cookies.get(config.cookie_name)
    if not is_valid_cookie(cookie):
        cookie = new_cookie()
        response.set_cookie(
            config.cookie_name,
            cookie,
            httponly=True,
            secure=config.cookie_secure,
            samesite=config.cookie_same_site,
            path=settings.app.route_prefix,
        )

    try:
        session = store.create(cookie)
    except SessionCapacityError as exc:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AT_CAPACITY",
            "Ezbot is at capacity, try again later",
        ) from exc
    return SessionResponse(session_id=session.id, idle_ttl_s=config.idle_ttl_s)
