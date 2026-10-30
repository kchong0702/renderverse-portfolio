from __future__ import annotations

import asyncio
import contextlib
import re
import secrets
import time
from collections.abc import Callable

from src.core.config import SessionSettings
from src.features.session.exceptions import SessionCapacityError
from src.features.session.models import Session
from src.infrastructure.observability.logging import get_logger

_logger = get_logger(__name__)

_COOKIE_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")


def new_cookie() -> str:
    """A fresh token for the HttpOnly browser cookie"""
    return secrets.token_urlsafe(32)


def is_valid_cookie(value: str | None) -> bool:
    """Whether a cookie value has the shape of a token from `new_cookie`"""
    return value is not None and _COOKIE_TOKEN.fullmatch(value) is not None


class SessionStore:
    def __init__(
        self,
        settings: SessionSettings,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._settings = settings
        self._clock = clock
        self._sessions: dict[str, Session] = {}
        self._sweeper: asyncio.Task[None] | None = None

    def __len__(self) -> int:
        return len(self._sessions)

    def _expired(self, session: Session, now: float) -> bool:
        return now - session.last_seen >= self._settings.idle_ttl_s

    def _discard(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if (
            session is not None
            and session.response is not None
            and not session.response.done
        ):
            session.response.stop()

    def create(self, cookie: str) -> Session:
        """Start a new session for one browser tab, leaving the other tabs'
        sessions under the same `cookie` alone"""
        if len(self._sessions) >= self._settings.max_sessions:
            self.sweep()
        if len(self._sessions) >= self._settings.max_sessions:
            _logger.warning("Refusing a new session at capacity", live=len(self))
            raise SessionCapacityError
        now = self._clock()
        session = Session(
            id=secrets.token_urlsafe(16),
            cookie=cookie,
            created_at=now,
            last_seen=now,
        )
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str | None, cookie: str | None) -> Session | None:
        """The live session for a tab, only for the cookie that owns it,
        refreshing its idle timer"""
        if not session_id or not cookie:
            return None
        session = self._sessions.get(session_id)
        if session is None or not secrets.compare_digest(session.cookie, cookie):
            return None
        now = self._clock()
        if self._expired(session, now):
            self._discard(session_id)
            return None
        session.last_seen = now
        return session

    def sweep(self) -> int:
        """Delete expired sessions, returning how many were removed"""
        now = self._clock()
        expired = [s.id for s in self._sessions.values() if self._expired(s, now)]
        for session_id in expired:
            self._discard(session_id)
        return len(expired)

    async def _sweep_forever(self, on_sweep: Callable[[], None] | None) -> None:
        while True:
            await asyncio.sleep(self._settings.sweep_interval_s)
            removed = self.sweep()
            if on_sweep is not None:
                on_sweep()
            if removed:
                _logger.info("Swept expired sessions", removed=removed, live=len(self))

    def start(self, on_sweep: Callable[[], None] | None = None) -> None:
        """Response the periodic sweep on the current event loop"""
        if self._sweeper is None:
            self._sweeper = asyncio.create_task(self._sweep_forever(on_sweep))

    async def aclose(self) -> None:
        """Stop sweeping and cancel every response in progress"""
        if self._sweeper is not None:
            self._sweeper.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._sweeper
            self._sweeper = None
        for session_id in list(self._sessions):
            self._discard(session_id)


__all__ = [
    "SessionStore",
    "is_valid_cookie",
    "new_cookie",
]
