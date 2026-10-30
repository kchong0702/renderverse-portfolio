import pytest

from src.features.rate_limit.limiter import SlidingWindowLimiter, ip_key


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_allows_up_to_the_limit_within_the_window():
    clock = Clock()
    limiter = SlidingWindowLimiter(max_events=2, window_s=10, clock=clock)

    for _ in range(2):
        assert limiter.retry_after("a") == 0
        limiter.record("a")

    assert limiter.retry_after("a") == 10


def test_window_slides():
    clock = Clock()
    limiter = SlidingWindowLimiter(max_events=1, window_s=10, clock=clock)
    limiter.record("a")

    clock.now = 4
    assert limiter.retry_after("a") == 6
    clock.now = 10
    assert limiter.retry_after("a") == 0


def test_sweep_forgets_idle_keys():
    clock = Clock()
    limiter = SlidingWindowLimiter(max_events=1, window_s=10, clock=clock)
    limiter.record("a")

    clock.now = 20
    limiter.sweep()

    assert limiter._hits == {}


@pytest.mark.parametrize(
    ("ip", "key"),
    [
        ("203.0.113.7", "203.0.113.7"),
        ("2001:db8:1:2:3:4:5:6", "2001:db8:1:2::/64"),
        ("2001:db8:1:2:ffff::1", "2001:db8:1:2::/64"),
        ("::ffff:203.0.113.7", "203.0.113.7"),
        ("unknown", "unknown"),
    ],
)
def test_ip_key_groups_ipv6_by_slash_64(ip, key):
    assert ip_key(ip) == key
