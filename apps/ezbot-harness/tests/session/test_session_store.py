import pytest

from src.core.config import SessionSettings
from src.features.session.exceptions import SessionCapacityError
from src.features.session.store import (
    SessionStore,
    is_valid_cookie,
    new_cookie,
)


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def make_store(clock: Clock, **settings) -> SessionStore:
    return SessionStore(SessionSettings(**settings), clock=clock)


def test_session_expires_after_idle_ttl():
    clock = Clock()
    store = make_store(clock, idle_ttl_s=60)
    session = store.create("cookie")

    clock.now += 59
    assert store.get(session.id, "cookie") is session
    clock.now += 59
    assert store.get(session.id, "cookie") is session
    clock.now += 60
    assert store.get(session.id, "cookie") is None


def test_an_active_session_never_expires():
    clock = Clock()
    store = make_store(clock, idle_ttl_s=60)
    session = store.create("cookie")

    for _ in range(1000):
        clock.now += 59
        assert store.get(session.id, "cookie") is session


def test_each_tab_keeps_its_own_session():
    store = make_store(Clock())

    first = store.create("cookie")
    second = store.create("cookie")

    assert first.id != second.id
    assert store.get(first.id, "cookie") is first
    assert store.get(second.id, "cookie") is second


def test_a_session_belongs_to_its_cookie_only():
    store = make_store(Clock())
    session = store.create("cookie")

    assert store.get(session.id, "someone else") is None
    assert store.get(session.id, None) is None
    assert store.get(None, "cookie") is None


def test_capacity_refuses_new_sessions_and_keeps_live_ones():
    clock = Clock()
    store = make_store(clock, max_sessions=2, idle_ttl_s=60)
    first = store.create("a")
    second = store.create("b")

    with pytest.raises(SessionCapacityError):
        store.create("c")

    assert store.get(first.id, "a") is first
    assert store.get(second.id, "b") is second


def test_capacity_frees_up_as_idle_sessions_expire():
    clock = Clock()
    store = make_store(clock, max_sessions=1, idle_ttl_s=60)
    store.create("a")

    clock.now += 60

    assert store.create("b").cookie == "b"


def test_sweep_removes_expired_sessions():
    clock = Clock()
    store = make_store(clock, idle_ttl_s=10)
    store.create("cookie")
    store.create("cookie")

    clock.now += 11

    assert store.sweep() == 2
    assert len(store) == 0


def test_cookie_tokens_are_recognised_by_shape():
    assert is_valid_cookie(new_cookie())
    assert not is_valid_cookie(None)
    assert not is_valid_cookie("")
    assert not is_valid_cookie("x" * 44)
    assert not is_valid_cookie("not a token with spaces and enough length......")
