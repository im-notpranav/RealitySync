"""Login, refresh rotation with reuse detection, logout and password change (03 §M11)."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import InvalidCredentialsError, UnauthenticatedError
from app.core.rate_limit import change_password_limiter, login_limiter
from app.core.security import (
    burn_password_check,
    create_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    password_needs_rehash,
    verify_password,
    ws_tickets,
)
from app.models import RefreshToken, User
from app.services import audit_service

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    expires_in: int
    refresh_token: str
    user: User


async def login(
    session: AsyncSession, *, email: str, password: str, client_ip: str, now: datetime
) -> IssuedTokens:
    """Check credentials and start a new refresh-token family.

    Unknown email, wrong password and deactivated account all give the same error, after the
    same amount of hashing work, so the response does not reveal which accounts exist.
    """
    limiter_key = f"{client_ip}|{email.lower()}"
    login_limiter.check(limiter_key, now)

    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        burn_password_check(password)
    if user is None or not verify_password(user.password_hash, password) or not user.is_active:
        login_limiter.record_failure(limiter_key, now)
        raise InvalidCredentialsError("Invalid email or password")

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = now
    tokens, _ = await _issue(session, user, family_id=uuid.uuid4(), now=now)
    audit_service.record(
        session, actor_id=user.id, action="user.login", target_type="user", target_id=user.id
    )
    await session.commit()
    log.info("user_login", user_id=str(user.id))
    return tokens


async def refresh(
    session: AsyncSession, *, refresh_token: str | None, now: datetime
) -> IssuedTokens:
    """Rotate a refresh token. Presenting an already rotated or revoked token revokes its family.

    The row is locked so two concurrent refreshes of the same token cannot both succeed.
    """
    if not refresh_token:
        raise UnauthenticatedError("Missing refresh token")
    row = await session.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(refresh_token))
        .with_for_update()
    )
    if row is None:
        raise UnauthenticatedError("Invalid refresh token")
    if row.revoked_at is not None:
        await revoke_tokens(session, user_id=row.user_id, now=now, family_id=row.family_id)
        await session.commit()
        log.warning("refresh_token_reuse", user_id=str(row.user_id), family_id=str(row.family_id))
        raise UnauthenticatedError("Refresh token reused")
    if row.expires_at <= now:
        raise UnauthenticatedError("Refresh token expired")
    user = await session.get(User, row.user_id)
    if user is None or not user.is_active:
        raise UnauthenticatedError("Invalid refresh token")

    tokens, successor = await _issue(session, user, family_id=row.family_id, now=now)
    row.revoked_at = now
    row.replaced_by = successor.id
    await session.commit()
    return tokens


async def logout(
    session: AsyncSession, *, user: User, refresh_token: str | None, now: datetime
) -> None:
    """Revoke the family of the presented refresh token, if it is the caller's."""
    family_id = await _own_family(session, user.id, refresh_token)
    if family_id is not None:
        await revoke_tokens(session, user_id=user.id, now=now, family_id=family_id)
    await session.commit()


async def change_password(
    session: AsyncSession,
    *,
    user: User,
    current_password: str,
    new_password: str,
    refresh_token: str | None,
    now: datetime,
) -> None:
    """Replace the caller's password and sign out their other sessions (FR-AUT-007).

    The session that made the change keeps its refresh-token family when its cookie came along.
    """
    limiter_key = str(user.id)
    change_password_limiter.check(limiter_key, now)
    if not verify_password(user.password_hash, current_password):
        change_password_limiter.record_failure(limiter_key, now)
        raise InvalidCredentialsError("Current password is incorrect")

    user.password_hash = hash_password(new_password)
    keep = await _own_family(session, user.id, refresh_token)
    await revoke_tokens(session, user_id=user.id, now=now, except_family_id=keep)
    audit_service.record(
        session,
        actor_id=user.id,
        action="user.password_change",
        target_type="user",
        target_id=user.id,
    )
    await session.commit()


def issue_ws_ticket(user: User, now: datetime) -> tuple[str, int]:
    return ws_tickets.issue(user.id, now), ws_tickets.ttl_seconds


async def revoke_tokens(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    now: datetime,
    family_id: uuid.UUID | None = None,
    except_family_id: uuid.UUID | None = None,
) -> None:
    """Revoke the user's live refresh tokens: one family, all but one family, or all."""
    statement = (
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    if family_id is not None:
        statement = statement.where(RefreshToken.family_id == family_id)
    if except_family_id is not None:
        statement = statement.where(RefreshToken.family_id != except_family_id)
    await session.execute(statement)


async def _issue(
    session: AsyncSession, user: User, *, family_id: uuid.UUID, now: datetime
) -> tuple[IssuedTokens, RefreshToken]:
    raw = new_refresh_token()
    row = RefreshToken(
        user_id=user.id,
        family_id=family_id,
        token_hash=hash_token(raw),
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_DAYS),
    )
    session.add(row)
    await session.flush()
    access_token, expires_in = create_access_token(user.id, user.role, now)
    return IssuedTokens(access_token, expires_in, raw, user), row


async def _own_family(
    session: AsyncSession, user_id: uuid.UUID, refresh_token: str | None
) -> uuid.UUID | None:
    """Family of a live refresh token that belongs to `user_id`, else None."""
    if not refresh_token:
        return None
    row = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    )
    if row is None or row.user_id != user_id or row.revoked_at is not None:
        return None
    return row.family_id
