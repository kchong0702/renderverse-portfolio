from fastapi import Depends, Request, status

from src.app.deps import get_session_store, get_settings_dep
from src.app.errors import api_error
from src.core.config import Settings
from src.infrastructure.store.session import SessionStore
from src.shared.schemas.session import Session


def client_ip(request: Request, settings: Settings = Depends(get_settings_dep)) -> str:  # noqa: B008
    """Real client address, from the configured proxy header when present"""
    header = settings.rate_limit.client_ip_header
    if header:
        forwarded = request.headers.get(header, "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"


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
