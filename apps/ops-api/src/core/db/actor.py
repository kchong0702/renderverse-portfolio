from __future__ import annotations

from contextvars import ContextVar
from uuid import UUID

SYSTEM_ACTOR = "system"

_actor: ContextVar[str] = ContextVar("actor", default=SYSTEM_ACTOR)


def user_actor(user_id: UUID) -> str:
    return f"user:{user_id}"


def set_actor(actor: str) -> None:
    """Write as this actor for the rest of the current request or task"""
    _actor.set(actor)


def current_actor() -> str:
    return _actor.get()


__all__ = ["SYSTEM_ACTOR", "current_actor", "set_actor", "user_actor"]
