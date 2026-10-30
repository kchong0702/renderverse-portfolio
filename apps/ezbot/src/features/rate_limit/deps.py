from fastapi import Depends, Request

from src.app.deps import get_settings_dep
from src.core.config import Settings


def client_ip(request: Request, settings: Settings = Depends(get_settings_dep)) -> str:  # noqa: B008
    """Real client address, from the configured proxy header when present"""
    header = settings.rate_limit.client_ip_header
    if header:
        forwarded = request.headers.get(header, "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"
