"""User administration and first-admin bootstrap (FR-AUT-004/005, 04 §3)."""

import uuid
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import ColumnElement, UnaryExpression, func, or_, select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import ConflictError, NotFoundError, ValidationFailed
from app.core.security import hash_password
from app.models import User
from app.schemas.user import UserCreate, UserUpdate
from app.services import audit_service, auth_service

log = structlog.get_logger(__name__)

SORTABLE = {
    "email": User.email,
    "full_name": User.full_name,
    "role": User.role,
    "created_at": User.created_at,
    "last_login_at": User.last_login_at,
}


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("user", str(user_id))
    return user


async def list_users(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    role: str | None = None,
    is_active: bool | None = None,
    q: str | None = None,
    sort: str | None = None,
) -> tuple[list[User], int]:
    filters: list[ColumnElement[bool]] = []
    if role is not None:
        filters.append(User.role == role)
    if is_active is not None:
        filters.append(User.is_active.is_(is_active))
    if q:
        pattern = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        filters.append(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))

    total = await session.scalar(select(func.count()).select_from(User).where(*filters)) or 0
    rows = await session.scalars(
        select(User)
        .where(*filters)
        .order_by(*_order_by(sort))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


async def create_user(session: AsyncSession, *, actor: User, data: UserCreate) -> User:
    if await session.scalar(select(User.id).where(User.email == data.email)) is not None:
        raise ConflictError("A user with this email already exists")
    user = User(
        email=data.email,
        full_name=data.full_name,
        role=data.role,
        password_hash=hash_password(data.password),
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:  # a concurrent create won the race
        await session.rollback()
        raise ConflictError("A user with this email already exists") from exc
    audit_service.record(
        session,
        actor_id=actor.id,
        action="user.create",
        target_type="user",
        target_id=user.id,
        metadata={"role": user.role},
    )
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(
    session: AsyncSession, *, actor: User, user_id: uuid.UUID, data: UserUpdate, now: datetime
) -> User:
    """Apply the given fields. A new password or a deactivation signs the user out everywhere."""
    user = await get_user(session, user_id)
    changes = data.model_dump(exclude_none=True)
    if not changes:
        return user

    demoted = changes.get("role", user.role) != "admin"
    deactivated = changes.get("is_active", user.is_active) is False
    if user.role == "admin" and user.is_active and (demoted or deactivated):
        await _ensure_another_active_admin(session, user.id)

    for field in ("full_name", "role", "is_active"):
        if field in changes:
            setattr(user, field, changes[field])
    if "password" in changes:
        user.password_hash = hash_password(changes["password"])
    if "password" in changes or changes.get("is_active") is False:
        await auth_service.revoke_tokens(session, user_id=user.id, now=now)

    metadata: dict[str, object] = {"fields": sorted(changes)}
    if "role" in changes:
        metadata["role"] = changes["role"]
    audit_service.record(
        session,
        actor_id=actor.id,
        action="user.update",
        target_type="user",
        target_id=user.id,
        metadata=metadata,
    )
    await session.commit()
    await session.refresh(user)
    return user


async def bootstrap_admin(
    session_factory: async_sessionmaker[AsyncSession], *, email: str, password: str
) -> None:
    """Create the first admin from `ADMIN_EMAIL`/`ADMIN_PASSWORD` when no user exists (05 §6).

    Idempotent. Skips with a warning, instead of stopping the API, when the variables are unset
    or the database is not migrated yet; restart the API after `make migrate`.
    """
    if not email or not password:
        log.warning("admin_bootstrap_skipped", reason="ADMIN_EMAIL or ADMIN_PASSWORD not set")
        return
    try:
        async with session_factory() as session:
            if await session.scalar(select(func.count()).select_from(User)):
                return
            admin = User(
                email=email,
                full_name="Administrator",
                role="admin",
                password_hash=hash_password(password),
            )
            session.add(admin)
            await session.flush()
            audit_service.record(
                session,
                actor_id=None,
                action="user.create",
                target_type="user",
                target_id=admin.id,
                metadata={"role": "admin", "source": "bootstrap"},
            )
            await session.commit()
            log.info("admin_bootstrapped", user_id=str(admin.id))
    except IntegrityError:
        log.info("admin_bootstrap_skipped", reason="created concurrently")
    except (DBAPIError, OSError) as exc:
        log.warning("admin_bootstrap_skipped", reason=type(exc).__name__)


def _order_by(sort: str | None) -> list[UnaryExpression[Any]]:
    if not sort:
        return [User.created_at.asc(), User.id.asc()]
    descending = sort.startswith("-")
    column = SORTABLE.get(sort.lstrip("-"))
    if column is None:
        raise ValidationFailed(
            "Invalid sort field",
            details=[{"field": "sort", "message": f"must be one of {sorted(SORTABLE)}"}],
        )
    ordered = column.desc().nulls_last() if descending else column.asc().nulls_last()
    return [ordered, User.id.asc()]


async def _ensure_another_active_admin(session: AsyncSession, user_id: uuid.UUID) -> None:
    others = await session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.role == "admin", User.is_active.is_(True), User.id != user_id)
    )
    if not others:
        raise ConflictError("The last active admin cannot be demoted or deactivated")
