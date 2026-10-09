from datetime import UTC, datetime

from app.core.clock import FixedClock, SystemClock


def test_system_clock() -> None:
    clock = SystemClock()
    now = clock.now()

    assert now.tzinfo == UTC
    assert abs((now - datetime.now(UTC)).total_seconds()) < 1.0


def test_fixed_clock() -> None:
    fixed_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    clock = FixedClock(fixed_time)

    assert clock.now() == fixed_time
    assert clock.now() == fixed_time
