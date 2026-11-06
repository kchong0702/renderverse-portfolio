from __future__ import annotations

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

_SAME_ORIGIN_FETCH = frozenset({"same-origin", "none"})


def _is_allowed(headers: Headers, allowed_origins: set[str]) -> bool:
    """The order of Go's CrossOriginProtection: a trusted origin, then the browser's
    Sec-Fetch-Site, then Origin for browsers that don't send it"""
    origin = headers.get("origin")
    if origin in allowed_origins:
        return True
    fetch_site = headers.get("sec-fetch-site")
    if fetch_site is not None:
        return fetch_site in _SAME_ORIGIN_FETCH
    return origin is None


class CSRFMiddleware:
    def __init__(self, app: ASGIApp, allowed_origins: set[str]):
        self.app = app
        self.allowed_origins = allowed_origins

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and scope["method"] not in _SAFE_METHODS
            and not _is_allowed(Headers(scope=scope), self.allowed_origins)
        ):
            response = JSONResponse(
                {"detail": "Cross-site request blocked"}, status_code=403
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


__all__ = ["CSRFMiddleware"]
