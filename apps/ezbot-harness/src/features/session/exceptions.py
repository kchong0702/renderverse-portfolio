from __future__ import annotations


class SessionCapacityError(Exception):
    """The store is full; live sessions are never evicted to make room"""


__all__ = [
    "SessionCapacityError",
]
