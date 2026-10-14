"""Plain helpers shared by the auth API tests (fixtures live in conftest.py)."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from app.models import User

PASSWORD = "Correct-horse-42"
START = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)

MakeUser = Callable[..., Awaitable[User]]
Login = Callable[..., Awaitable[str]]


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> None:
        self.current += timedelta(**delta)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def assert_error(body: dict[str, object], code: str) -> None:
    """The 04 §1.3 envelope with the expected code."""
    error = body["error"]
    assert isinstance(error, dict)
    assert error["code"] == code
    assert {"code", "message", "details", "request_id"} <= error.keys()
