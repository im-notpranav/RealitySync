"""Auth tables behave as 05 §2.1, 2.2 and 2.19 specify (T-006)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models import AuditLog, RefreshToken, User

pytestmark = [pytest.mark.db, pytest.mark.asyncio]

NOW = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)


def make_user(email: str = "ana.lopez@example.com", role: str = "analyst") -> User:
    return User(email=email, password_hash="argon2id$test", full_name="Ana Lopez", role=role)


def make_token(user: User, token_hash: str = "a" * 64) -> RefreshToken:
    return RefreshToken(
        user_id=user.id,
        family_id=uuid.uuid4(),
        token_hash=token_hash,
        expires_at=NOW + timedelta(days=7),
    )


async def add(session: AsyncSession, *rows: object) -> None:
    session.add_all(rows)
    await session.flush()


async def test_user_defaults(db_session: AsyncSession) -> None:
    user = make_user()
    await add(db_session, user)
    await db_session.refresh(user)

    assert isinstance(user.id, uuid.UUID)
    assert user.is_active is True
    assert user.last_login_at is None
    assert user.created_at.tzinfo is not None
    assert user.updated_at.tzinfo is not None


async def test_email_is_unique_ignoring_case(db_session: AsyncSession) -> None:
    await add(db_session, make_user("ana.lopez@example.com"))

    with pytest.raises(IntegrityError, match="uq_users_email"):
        async with db_session.begin_nested():
            await add(db_session, make_user("Ana.Lopez@EXAMPLE.com"))


async def test_email_lookup_ignores_case(db_session: AsyncSession) -> None:
    await add(db_session, make_user("ana.lopez@example.com"))

    found = await db_session.scalar(select(User).where(User.email == "ANA.LOPEZ@example.com"))

    assert found is not None


@pytest.mark.parametrize("role", ["admin", "analyst", "viewer"])
async def test_known_roles_are_accepted(db_session: AsyncSession, role: str) -> None:
    await add(db_session, make_user(role=role))


async def test_unknown_role_is_rejected(db_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError, match="ck_users_role"):
        async with db_session.begin_nested():
            await add(db_session, make_user(role="superuser"))


async def test_token_hash_is_unique(db_session: AsyncSession) -> None:
    user = make_user()
    await add(db_session, user)
    await add(db_session, make_token(user))

    with pytest.raises(IntegrityError, match="uq_refresh_tokens_token_hash"):
        async with db_session.begin_nested():
            await add(db_session, make_token(user))


async def test_rotation_links_tokens(db_session: AsyncSession) -> None:
    user = make_user()
    await add(db_session, user)
    old, new = make_token(user, "a" * 64), make_token(user, "b" * 64)
    new.family_id = old.family_id
    await add(db_session, old, new)

    old.revoked_at = NOW
    old.replaced_by = new.id
    await db_session.flush()
    await db_session.refresh(old)

    assert old.replaced_by == new.id


async def test_replaced_by_must_reference_a_token(db_session: AsyncSession) -> None:
    user = make_user()
    await add(db_session, user)
    token = make_token(user)
    token.replaced_by = uuid.uuid4()

    with pytest.raises(IntegrityError, match="fk_refresh_tokens_replaced_by_refresh_tokens"):
        async with db_session.begin_nested():
            await add(db_session, token)


async def test_deleting_a_user_deletes_tokens_and_keeps_audit(db_session: AsyncSession) -> None:
    user = make_user()
    await add(db_session, user)
    token = make_token(user)
    entry = AuditLog(actor_id=user.id, action="user.login", target_type="user", target_id="u-1")
    await add(db_session, token, entry)
    token_id, entry_id = token.id, entry.id
    db_session.expunge_all()

    await db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user.id})

    assert await db_session.get(RefreshToken, token_id) is None
    kept = await db_session.get(AuditLog, entry_id)
    assert kept is not None
    assert kept.actor_id is None


async def test_audit_log_defaults(db_session: AsyncSession) -> None:
    entry = AuditLog(action="rule.update", target_type="rule", target_id="R001")
    await add(db_session, entry)
    await db_session.refresh(entry)

    assert entry.metadata_ == {}
    assert entry.actor_id is None
    assert entry.created_at.tzinfo is not None


async def test_indexes_match_the_schema(db_engine: AsyncEngine) -> None:
    async with db_engine.connect() as conn:
        indexes = await conn.run_sync(
            lambda sync: {
                table: {
                    ix["name"]: ix
                    for ix in inspect(sync).get_indexes(table)
                    if not ix.get("duplicates_constraint")
                }
                for table in ("refresh_tokens", "audit_logs")
            }
        )
        rows = await conn.execute(
            text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'audit_logs'")
        )
        definitions = {name: definition for name, definition in rows}

    assert {name: ix["column_names"] for name, ix in indexes["refresh_tokens"].items()} == {
        "ix_refresh_tokens_user_id": ["user_id"],
        "ix_refresh_tokens_family_id": ["family_id"],
        "ix_refresh_tokens_expires_at": ["expires_at"],
    }
    assert set(indexes["audit_logs"]) == {
        "ix_audit_logs_created_at",
        "ix_audit_logs_actor_id_created_at",
        "ix_audit_logs_action",
    }
    assert "(created_at DESC)" in definitions["ix_audit_logs_created_at"]
    assert "(actor_id, created_at DESC)" in definitions["ix_audit_logs_actor_id_created_at"]
    assert "(action)" in definitions["ix_audit_logs_action"]
