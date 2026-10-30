from __future__ import annotations

import time
from collections.abc import Callable

from src.core.config import RateLimitSettings
from src.features.rate_limit.limiter import SlidingWindowLimiter, ip_key
from src.features.rate_limit.schemas import MessageLimitExceeded

DAY_S = 86_400  # 24 hours


class MessageLimiter:
    """Chat message limits per cookie and per client IP: a burst window
    for each, plus a rolling daily limit per IP. A message counts against all of
    them, and only when every limit has room."""

    def __init__(
        self, settings: RateLimitSettings, clock: Callable[[], float] = time.monotonic
    ):
        self._cookie = SlidingWindowLimiter(
            settings.max_messages_per_cookie, settings.window_s, clock
        )
        self._ip = SlidingWindowLimiter(
            settings.max_messages_per_ip, settings.window_s, clock
        )
        self._ip_daily = SlidingWindowLimiter(
            settings.max_daily_messages_per_ip, DAY_S, clock
        )

    def acquire(self, cookie: str, ip: str) -> MessageLimitExceeded | None:
        """Count one message, or return why it is not allowed without counting it"""
        ip = ip_key(ip)
        daily = self._ip_daily.retry_after(ip)
        if daily > 0:
            return MessageLimitExceeded(retry_after=daily, limit="daily")
        burst = max(self._cookie.retry_after(cookie), self._ip.retry_after(ip))
        if burst > 0:
            return MessageLimitExceeded(retry_after=burst, limit="burst")
        self._cookie.record(cookie)
        self._ip.record(ip)
        self._ip_daily.record(ip)
        return None

    def sweep(self) -> None:
        """Forget cookies and IPs with nothing left to count"""
        self._cookie.sweep()
        self._ip.sweep()
        self._ip_daily.sweep()


__all__ = ["DAY_S", "MessageLimiter"]
