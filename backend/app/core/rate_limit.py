"""In-memory sliding-window failure limiter (02 §5; Redis later)."""

import math
from collections import deque
from datetime import datetime, timedelta

from app.core.errors import RateLimited


class FailureLimiter:
    """Blocks a key after `limit` failures inside the last `window_seconds` (04 §15).

    Only failures count, so a user who signs in correctly is never slowed down; successes do not
    reset the window, so a correct guess cannot buy an attacker more attempts.
    """

    def __init__(self, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window = timedelta(seconds=window_seconds)
        self._failures: dict[str, deque[datetime]] = {}

    def check(self, key: str, now: datetime) -> None:
        """Raise `429 RATE_LIMITED` with `Retry-After` when the key has used up its failures."""
        failures = self._recent(key, now)
        if len(failures) >= self._limit:
            wait = (failures[0] + self._window - now).total_seconds()
            raise RateLimited(retry_after=max(1, math.ceil(wait)))

    def record_failure(self, key: str, now: datetime) -> None:
        self._failures.setdefault(key, deque()).append(now)

    def clear(self) -> None:
        self._failures.clear()

    def _recent(self, key: str, now: datetime) -> deque[datetime]:
        failures = self._failures.get(key)
        if failures is None:
            return deque()
        while failures and failures[0] <= now - self._window:
            failures.popleft()
        if not failures:
            del self._failures[key]  # keeps memory bounded by keys with recent failures
        return failures


login_limiter = FailureLimiter(limit=5, window_seconds=60)
change_password_limiter = FailureLimiter(limit=5, window_seconds=60)
