"""`/api/v1/users` and the first-admin bootstrap (04 §3, 05 §6, T-007)."""

import uuid

import pytest
import pytest_asyncio
from authkit import PASSWORD, Login, MakeUser, assert_error, bearer
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import verify_password
from app.models import AuditLog, RefreshToken, User
from app.services.user_service import bootstrap_admin

pytestmark = [pytest.mark.db, pytest.mark.asyncio, pytest.mark.usefixtures("api")]

USERS = "/api/v1/users"
UNKNOWN_ID = "7c1e0000-0000-4000-8000-000000000001"
NEW_USER = {
    "email": "riya.sharma@example.com",
    "full_name": "Riya Sharma",
    "role": "analyst",
    "password": "Min12chars!pass",
}


@pytest_asyncio.fixture
async def admin_token(make_user: MakeUser, login: Login) -> str:
    return await login(await make_user("admin", email="admin@example.com"))


async def audit_rows(session: AsyncSession, action: str) -> list[AuditLog]:
    return list(await session.scalars(select(AuditLog).where(AuditLog.action == action)))


# ---------------------------------------------------------------------------------- authz


@pytest.mark.parametrize("role", ["viewer", "analyst"])
@pytest.mark.parametrize(
    ("method", "path"), [("GET", USERS), ("POST", USERS), ("PATCH", f"{USERS}/{UNKNOWN_ID}")]
)
async def test_only_admins_manage_users(
    async_client: AsyncClient, make_user: MakeUser, login: Login, role: str, method: str, path: str
) -> None:
    token = await login(await make_user(role))

    response = await async_client.request(method, path, json=NEW_USER, headers=bearer(token))

    assert response.status_code == 403
    assert_error(response.json(), "FORBIDDEN")


async def test_users_require_authentication(async_client: AsyncClient) -> None:
    response = await async_client.get(USERS)

    assert response.status_code == 401


# ----------------------------------------------------------------------------------- list


async def test_list_users_is_paginated(
    async_client: AsyncClient, make_user: MakeUser, admin_token: str
) -> None:
    for _ in range(3):
        await make_user("viewer")

    response = await async_client.get(
        USERS, params={"page": 2, "page_size": 3}, headers=bearer(admin_token)
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["page"], body["page_size"], body["total"]) == (2, 3, 4)
    assert len(body["items"]) == 1
    assert set(body["items"][0]) == {
        "id",
        "email",
        "full_name",
        "role",
        "is_active",
        "created_at",
        "last_login_at",
    }


async def test_list_users_filters(
    async_client: AsyncClient, make_user: MakeUser, admin_token: str
) -> None:
    await make_user("viewer", email="riya.sharma@example.com", full_name="Riya Sharma")
    await make_user("viewer", email="dev.patel@example.com", is_active=False)
    await make_user("analyst", email="sam.lee@example.com")

    async def emails(**params: object) -> list[str]:
        response = await async_client.get(USERS, params=params, headers=bearer(admin_token))
        assert response.status_code == 200
        return sorted(item["email"] for item in response.json()["items"])

    assert await emails(role="viewer") == ["dev.patel@example.com", "riya.sharma@example.com"]
    assert await emails(role="viewer", is_active="true") == ["riya.sharma@example.com"]
    assert await emails(q="SHARMA") == ["riya.sharma@example.com"]
    assert await emails(q="sam.lee") == ["sam.lee@example.com"]
    assert await emails(q="%") == []  # wildcards are matched literally


async def test_list_users_sorts(
    async_client: AsyncClient, make_user: MakeUser, admin_token: str
) -> None:
    await make_user("viewer", email="b@example.com")
    await make_user("viewer", email="c@example.com")

    response = await async_client.get(USERS, params={"sort": "-email"}, headers=bearer(admin_token))

    assert [i["email"] for i in response.json()["items"]] == [
        "c@example.com",
        "b@example.com",
        "admin@example.com",
    ]


@pytest.mark.parametrize(
    "params",
    [{"page_size": 101}, {"page": 0}, {"role": "owner"}, {"sort": "password_hash"}],
    ids=["page-size", "page", "role", "sort"],
)
async def test_list_users_validation(
    async_client: AsyncClient, admin_token: str, params: dict[str, object]
) -> None:
    response = await async_client.get(USERS, params=params, headers=bearer(admin_token))

    assert response.status_code == 422
    assert_error(response.json(), "VALIDATION_ERROR")


# --------------------------------------------------------------------------------- create


async def test_create_user(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
) -> None:
    response = await async_client.post(USERS, json=NEW_USER, headers=bearer(admin_token))

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "riya.sharma@example.com"
    assert (body["role"], body["is_active"], body["last_login_at"]) == ("analyst", True, None)
    created = await db_session.get(User, uuid.UUID(body["id"]))
    assert created is not None
    assert verify_password(created.password_hash, NEW_USER["password"])
    [entry] = await audit_rows(db_session, "user.create")
    assert entry.target_id == body["id"]
    assert entry.metadata_ == {"role": "analyst"}  # no email or name in the audit trail


async def test_created_user_can_sign_in(async_client: AsyncClient, admin_token: str) -> None:
    await async_client.post(USERS, json=NEW_USER, headers=bearer(admin_token))

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": NEW_USER["email"], "password": NEW_USER["password"]},
    )

    assert response.status_code == 200


async def test_create_rejects_a_duplicate_email_ignoring_case(
    async_client: AsyncClient, make_user: MakeUser, admin_token: str
) -> None:
    await make_user(email="riya.sharma@example.com")

    response = await async_client.post(
        USERS,
        json={**NEW_USER, "email": "Riya.Sharma@EXAMPLE.com"},
        headers=bearer(admin_token),
    )

    assert response.status_code == 409
    assert_error(response.json(), "CONFLICT")


@pytest.mark.parametrize(
    "change",
    [
        {"password": "short-pass1"},
        {"email": "nope"},
        {"role": "owner"},
        {"full_name": "   "},
        {"is_active": False},
    ],
    ids=["short-password", "bad-email", "bad-role", "blank-name", "unknown-field"],
)
async def test_create_validation(
    async_client: AsyncClient, admin_token: str, change: dict[str, object]
) -> None:
    response = await async_client.post(
        USERS, json={**NEW_USER, **change}, headers=bearer(admin_token)
    )

    assert response.status_code == 422
    assert_error(response.json(), "VALIDATION_ERROR")


# --------------------------------------------------------------------------------- update


async def test_update_user(
    async_client: AsyncClient, make_user: MakeUser, admin_token: str, db_session: AsyncSession
) -> None:
    user = await make_user("viewer")

    response = await async_client.patch(
        f"{USERS}/{user.id}",
        json={"full_name": "Riya S.", "role": "analyst"},
        headers=bearer(admin_token),
    )

    assert response.status_code == 200
    assert (response.json()["full_name"], response.json()["role"]) == ("Riya S.", "analyst")
    [entry] = await audit_rows(db_session, "user.update")
    assert entry.target_id == str(user.id)
    assert entry.metadata_ == {"fields": ["full_name", "role"], "role": "analyst"}


async def test_password_reset_signs_the_user_out(
    async_client: AsyncClient,
    make_user: MakeUser,
    login: Login,
    admin_token: str,
    db_session: AsyncSession,
) -> None:
    user = await make_user()
    await login(user)

    response = await async_client.patch(
        f"{USERS}/{user.id}", json={"password": "Reset-by-admin-9"}, headers=bearer(admin_token)
    )

    assert response.status_code == 200
    live = await db_session.scalar(
        select(func.count())
        .select_from(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
    )
    assert live == 0
    [entry] = await audit_rows(db_session, "user.update")
    assert entry.metadata_ == {"fields": ["password"]}
    await db_session.refresh(user)
    assert verify_password(user.password_hash, "Reset-by-admin-9")
    assert not verify_password(user.password_hash, PASSWORD)


async def test_deactivated_user_is_signed_out(
    async_client: AsyncClient, make_user: MakeUser, login: Login, admin_token: str
) -> None:
    user = await make_user()
    token = await login(user)

    await async_client.patch(
        f"{USERS}/{user.id}", json={"is_active": False}, headers=bearer(admin_token)
    )

    assert (await async_client.get("/api/v1/auth/me", headers=bearer(token))).status_code == 401


async def test_last_active_admin_cannot_be_removed(
    async_client: AsyncClient, admin_token: str, db_session: AsyncSession
) -> None:
    admin = await db_session.scalar(select(User).where(User.email == "admin@example.com"))
    assert admin is not None

    for change in ({"role": "analyst"}, {"is_active": False}):
        response = await async_client.patch(
            f"{USERS}/{admin.id}", json=change, headers=bearer(admin_token)
        )
        assert response.status_code == 409
        assert_error(response.json(), "CONFLICT")


async def test_an_admin_can_be_demoted_while_another_remains(
    async_client: AsyncClient, make_user: MakeUser, admin_token: str
) -> None:
    other = await make_user("admin")

    response = await async_client.patch(
        f"{USERS}/{other.id}", json={"role": "viewer"}, headers=bearer(admin_token)
    )

    assert response.status_code == 200


async def test_update_unknown_user(async_client: AsyncClient, admin_token: str) -> None:
    response = await async_client.patch(
        f"{USERS}/{UNKNOWN_ID}", json={"full_name": "Nobody"}, headers=bearer(admin_token)
    )

    assert response.status_code == 404
    assert_error(response.json(), "NOT_FOUND")


@pytest.mark.parametrize(
    ("path_id", "body"),
    [
        ("not-a-uuid", {"full_name": "X"}),
        (UNKNOWN_ID, {"email": "new@example.com"}),
        (UNKNOWN_ID, {"password": "short"}),
    ],
    ids=["bad-id", "email-not-editable", "short-password"],
)
async def test_update_validation(
    async_client: AsyncClient, admin_token: str, path_id: str, body: dict[str, object]
) -> None:
    response = await async_client.patch(
        f"{USERS}/{path_id}", json=body, headers=bearer(admin_token)
    )

    assert response.status_code == 422
    assert_error(response.json(), "VALIDATION_ERROR")


# ------------------------------------------------------------------------------ bootstrap


def session_factory(db_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    """Sessions on the test's connection, so the bootstrap rolls back with the test."""
    return async_sessionmaker(
        bind=db_session.bind, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )


async def user_count(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(User)) or 0


async def test_bootstrap_creates_the_first_admin_once(db_session: AsyncSession) -> None:
    factory = session_factory(db_session)

    await bootstrap_admin(factory, email="first.admin@example.com", password="Bootstrap-pass-1")
    await bootstrap_admin(factory, email="first.admin@example.com", password="Bootstrap-pass-1")

    assert await user_count(db_session) == 1
    admin = await db_session.scalar(select(User))
    assert admin is not None
    assert (admin.email, admin.role, admin.is_active) == ("first.admin@example.com", "admin", True)
    assert verify_password(admin.password_hash, "Bootstrap-pass-1")
    [entry] = await audit_rows(db_session, "user.create")
    assert entry.actor_id is None
    assert entry.metadata_ == {"role": "admin", "source": "bootstrap"}


async def test_bootstrap_skips_when_users_exist(
    db_session: AsyncSession, make_user: MakeUser
) -> None:
    await make_user("viewer")

    await bootstrap_admin(
        session_factory(db_session), email="first.admin@example.com", password="Bootstrap-pass-1"
    )

    assert await user_count(db_session) == 1


@pytest.mark.parametrize(
    ("email", "password"), [("", "Bootstrap-pass-1"), ("first.admin@example.com", "")]
)
async def test_bootstrap_skips_without_credentials(
    db_session: AsyncSession, email: str, password: str
) -> None:
    await bootstrap_admin(session_factory(db_session), email=email, password=password)

    assert await user_count(db_session) == 0
