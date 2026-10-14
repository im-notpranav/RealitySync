"""Fixtures for API tests that need real users (T-007)."""

from collections.abc import Generator

import pytest
from authkit import PASSWORD, START, Login, MakeUser, MutableClock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_clock
from app.core.rate_limit import change_password_limiter, login_limiter
from app.core.security import hash_password, ws_tickets
from app.main import app
from app.models import User


@pytest.fixture
def clock() -> Generator[MutableClock, None, None]:
    test_clock = MutableClock(START)
    app.dependency_overrides[get_clock] = lambda: test_clock
    yield test_clock
    app.dependency_overrides.pop(get_clock, None)


@pytest.fixture
def api(override_get_session: None, clock: MutableClock) -> Generator[None, None, None]:
    """Real database session, test clock and fresh in-memory limiters for each test."""
    for store in (login_limiter, change_password_limiter, ws_tickets):
        store.clear()
    yield
    for store in (login_limiter, change_password_limiter, ws_tickets):
        store.clear()


@pytest.fixture
def make_user(db_session: AsyncSession) -> MakeUser:
    counter = iter(range(1, 10_000))

    async def _make(
        role: str = "analyst",
        *,
        email: str | None = None,
        password: str = PASSWORD,
        is_active: bool = True,
        full_name: str = "Test User",
    ) -> User:
        user = User(
            email=email or f"user{next(counter)}.{role}@example.com",
            full_name=full_name,
            role=role,
            is_active=is_active,
            password_hash=hash_password(password),
        )
        db_session.add(user)
        await db_session.commit()
        return user

    return _make


@pytest.fixture
def login(async_client: AsyncClient) -> Login:
    async def _login(user: User, password: str = PASSWORD) -> str:
        response = await async_client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": password}
        )
        assert response.status_code == 200, response.text
        token: str = response.json()["access_token"]
        return token

    return _login
