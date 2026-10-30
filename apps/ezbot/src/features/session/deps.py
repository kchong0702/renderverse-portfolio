from fastapi import Depends, Request, status

from src.app.deps import get_session_store, get_settings_dep
from src.app.errors import api_error
from src.core.config import Settings
from src.features.session.models import Session
from src.features.session.store import SessionStore


async def current_session(
    request: Request,
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
    store: SessionStore = Depends(get_session_store),  # noqa: B008
) -> Session:
    """This tab's live session, which must belong to the caller's cookie"""
    session = store.get(
        request.headers.get(settings.session.session_header),
        request.cookies.get(settings.session.cookie_name),
    )
    if session is None:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            "SESSION_EXPIRED",
            "The chat session has expired, start a new one",
        )
    return session
