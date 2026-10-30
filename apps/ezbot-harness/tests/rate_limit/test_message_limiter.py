from src.core.config import RateLimitSettings
from src.features.rate_limit.message_limiter import DAY_S, MessageLimiter


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def make_limiter(clock: Clock, **settings) -> MessageLimiter:
    defaults = {
        "window_s": 600,
        "max_messages_per_cookie": 2,
        "max_messages_per_ip": 3,
        "max_daily_messages_per_ip": 5,
    }
    return MessageLimiter(RateLimitSettings(**{**defaults, **settings}), clock=clock)


def test_cookie_burst_limit_covers_every_tab_of_the_cookie():
    limiter = make_limiter(Clock())

    assert limiter.acquire("cookie", "1.1.1.1") is None
    assert limiter.acquire("cookie", "1.1.1.1") is None
    exceeded = limiter.acquire("cookie", "1.1.1.1")

    assert exceeded is not None and exceeded.limit == "burst"
    assert limiter.acquire("other cookie", "1.1.1.1") is None


def test_ip_burst_limit_covers_every_cookie_on_the_ip():
    limiter = make_limiter(Clock())

    for cookie in ["a", "b", "c"]:
        assert limiter.acquire(cookie, "1.1.1.1") is None
    exceeded = limiter.acquire("d", "1.1.1.1")

    assert exceeded is not None and exceeded.limit == "burst"
    assert limiter.acquire("d", "2.2.2.2") is None


def test_daily_limit_is_a_rolling_24_hours_per_ip():
    clock = Clock()
    limiter = make_limiter(clock)

    for i in range(5):
        clock.now = i * 600
        assert limiter.acquire(f"cookie {i}", "1.1.1.1") is None

    clock.now = 5 * 600
    exceeded = limiter.acquire("cookie 5", "1.1.1.1")
    assert exceeded is not None and exceeded.limit == "daily"
    assert exceeded.retry_after == DAY_S - 5 * 600

    clock.now = DAY_S
    assert limiter.acquire("cookie 5", "1.1.1.1") is None


def test_a_refused_message_counts_against_nothing():
    limiter = make_limiter(Clock(), max_messages_per_cookie=1)
    limiter.acquire("cookie", "1.1.1.1")

    assert limiter.acquire("cookie", "1.1.1.1") is not None
    assert limiter.acquire("other", "1.1.1.1") is None
    assert limiter.acquire("third", "1.1.1.1") is None
