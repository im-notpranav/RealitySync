from datetime import UTC, datetime, timedelta

import pytest

from app.core.errors import RateLimited
from app.core.rate_limit import FailureLimiter

NOW = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)


def test_allows_until_the_limit_of_failures() -> None:
    limiter = FailureLimiter(limit=5, window_seconds=60)
    for second in range(5):
        limiter.check("ip|ana", NOW + timedelta(seconds=second))
        limiter.record_failure("ip|ana", NOW + timedelta(seconds=second))

    with pytest.raises(RateLimited) as blocked:
        limiter.check("ip|ana", NOW + timedelta(seconds=10))

    assert blocked.value.status_code == 429
    assert blocked.value.retry_after == 50  # the first failure leaves the window at +60 s


def test_window_slides() -> None:
    limiter = FailureLimiter(limit=5, window_seconds=60)
    for _ in range(5):
        limiter.record_failure("k", NOW)

    limiter.check("k", NOW + timedelta(seconds=60))


def test_keys_are_independent() -> None:
    limiter = FailureLimiter(limit=1, window_seconds=60)
    limiter.record_failure("a", NOW)

    limiter.check("b", NOW)
    with pytest.raises(RateLimited):
        limiter.check("a", NOW)


def test_retry_after_is_at_least_one_second() -> None:
    limiter = FailureLimiter(limit=1, window_seconds=60)
    limiter.record_failure("k", NOW)

    with pytest.raises(RateLimited) as blocked:
        limiter.check("k", NOW + timedelta(seconds=59, milliseconds=900))

    assert blocked.value.retry_after == 1
