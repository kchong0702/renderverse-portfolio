import math

from fastapi import HTTPException, status

from src.app.errors import api_error
from src.features.rate_limit.schemas import MessageLimitExceeded


def rate_limited(exceeded: MessageLimitExceeded) -> HTTPException:
    """429 error for a refused message, with `Retry-After` in whole seconds"""
    seconds = max(1, math.ceil(exceeded.retry_after))
    if exceeded.limit == "daily":
        code, message = "DAILY_LIMIT", "Daily message limit reached"
    else:
        code, message = "RATE_LIMITED", "Too many messages"
    return api_error(
        status.HTTP_429_TOO_MANY_REQUESTS,
        code,
        f"{message}, try again in {seconds} seconds",
        **{"Retry-After": str(seconds)},
    )
