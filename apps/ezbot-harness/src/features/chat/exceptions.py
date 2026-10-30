from __future__ import annotations


class ResponseInProgressError(Exception):
    """The session already has a response streaming"""


class ResponseNotFoundError(Exception):
    """No resumable response matches the request"""


__all__ = [
    "ResponseInProgressError",
    "ResponseNotFoundError",
]
