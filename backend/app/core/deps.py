"""Shared FastAPI dependencies: clock, current user and role guard (02 §5, 03 §M11)."""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, SystemClock
from app.core.errors import PermissionDenied, UnauthenticatedError
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import User

ROLE_RANK = {"viewer": 0, "analyst": 1, "admin": 2}

_bearer = HTTPBearer(auto_error=False)


def get_clock() -> Clock:
    """Overridden in tests with a `FixedClock`."""
    return SystemClock()


SessionDep = Annotated[AsyncSession, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]


async def get_current_user(
    session: SessionDep,
    clock: ClockDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """The active user behind the bearer token.

    The role comes from the database, not the token, so a demotion or deactivation applies at
    once instead of when the token expires.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthenticatedError("Missing bearer token")
    claims = decode_access_token(credentials.credentials, clock.now())
    if claims is None:
        raise UnauthenticatedError("Invalid or expired token")
    user = await session.get(User, claims.user_id)
    if user is None or not user.is_active:
        raise UnauthenticatedError("Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(minimum: str) -> Callable[[User], Awaitable[User]]:
    """Dependency allowing `minimum` and every higher role (viewer < analyst < admin)."""
    if minimum not in ROLE_RANK:
        raise ValueError(f"unknown role {minimum!r}")

    async def guard(user: CurrentUser) -> User:
        if ROLE_RANK.get(user.role, -1) < ROLE_RANK[minimum]:
            raise PermissionDenied(f"Requires role {minimum}")
        return user

    return guard
