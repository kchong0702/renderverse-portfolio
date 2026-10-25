from __future__ import annotations

import ipaddress
import time
from collections import deque
from collections.abc import Callable


class SlidingWindowLimiter:
    def __init__(
        self,
        max_events: int,
        window_s: float,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._max_events = max_events
        self._window_s = window_s
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def _prune(self, key: str, now: float) -> deque[float]:
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= self._window_s:
            hits.popleft()
        return hits

    def retry_after(self, key: str) -> float:
        now = self._clock()
        hits = self._prune(key, now)
        if len(hits) < self._max_events:
            return 0.0
        return self._window_s - (now - hits[0])

    def record(self, key: str) -> None:
        now = self._clock()
        self._prune(key, now).append(now)

    def sweep(self) -> None:
        now = self._clock()
        for key in list(self._hits):
            if not self._prune(key, now):
                del self._hits[key]


def ip_key(ip: str) -> str:
    """Rate-limit key for a client address: IPv4 as is, IPv6 by its /64, since
    one IPv6 client usually holds the whole /64"""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped is not None:
            return str(address.ipv4_mapped)
        return str(ipaddress.IPv6Network((address, 64), strict=False))
    return str(address)


__all__ = ["SlidingWindowLimiter", "ip_key"]
