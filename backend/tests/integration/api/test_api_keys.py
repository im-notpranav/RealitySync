"""`/api-keys` (04 §3, FR-AUT-005, T-011)."""

import hashlib
import uuid
from typing import Any

import pytest
import pytest_asyncio
from authkit import START, Login, MakeUser, MutableClock, assert_error, bearer
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed import default_source_systems
from app.models import ApiKey, AuditLog, SourceSystem

pytestmark = [pytest.mark.db, pytest.mark.asyncio, pytest.mark.usefixtures("api", "systems")]

URL = "/api/v1/api-keys"


@pytest_asyncio.fixture
async def systems(db_session: AsyncSession) -> None:
    await db_session.execute(
        insert(SourceSystem)
        .values(default_source_systems())
        .on_conflict_do_nothing(index_elements=["key"])
    )
    await db_session.commit()


@pytest_asyncio.fixture
async def admin(make_user: MakeUser, login: Login) -> dict[str, str]:
    return bearer(await login(await make_user("admin")))


async def create(client: AsyncClient, headers: dict[str, str], **body: Any) -> dict[str, Any]:
    response = await client.post(URL, json={"name": "simulator", **body}, headers=headers)
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


async def audit_actions(session: AsyncSession, action: str) -> list[AuditLog]:
    return list(await session.scalars(select(AuditLog).where(AuditLog.action == action)))


async def test_create_returns_the_secret_once(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    created = await create(async_client, admin)

    assert set(created) == {"id", "name", "key", "created_at"}
    assert created["name"] == "simulator"
    secret = created["key"]
    assert secret.startswith("rs_live_") and len(secret) > 40

    key = await db_session.get(ApiKey, uuid.UUID(created["id"]))
    assert key is not None
    # Only the hash is stored; the prefix is the fixed part plus 8 characters.
    assert key.key_hash == hashlib.sha256(secret.encode()).hexdigest()
    assert key.key_prefix == secret[:16]
    assert secret not in (key.key_hash, key.key_prefix, key.name)
    assert key.source_system_id is None
    [entry] = await audit_actions(db_session, "api_key.create")
    assert entry.target_id == created["id"]
    assert entry.metadata_ == {"source_system": None}


async def test_list_never_returns_secrets(
    async_client: AsyncClient, admin: dict[str, str], clock: MutableClock
) -> None:
    first = await create(async_client, admin)
    clock.advance(seconds=1)  # distinct created_at, so newest-first is well defined
    await create(async_client, admin, name="billing feed", source_system="billing")

    response = await async_client.get(URL, headers=admin)

    assert response.status_code == 200
    body = response.json()
    assert (body["page"], body["page_size"], body["total"]) == (1, 25, 2)
    assert first["key"] not in response.text
    newest, oldest = body["items"]
    assert set(newest) == {
        "id",
        "name",
        "key_prefix",
        "source_system",
        "created_by",
        "created_at",
        "last_used_at",
        "revoked_at",
    }
    assert (newest["name"], newest["source_system"]) == ("billing feed", "billing")
    assert (oldest["key_prefix"], oldest["source_system"]) == (first["key"][:16], None)
    assert oldest["revoked_at"] is None


async def test_list_paginates(async_client: AsyncClient, admin: dict[str, str]) -> None:
    for n in range(3):
        await create(async_client, admin, name=f"key {n}")

    response = await async_client.get(URL, params={"page": 2, "page_size": 2}, headers=admin)

    body = response.json()
    assert (body["total"], len(body["items"])) == (3, 1)


async def test_a_key_can_be_bound_to_a_system(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    created = await create(async_client, admin, source_system="crm")

    key = await db_session.get(ApiKey, uuid.UUID(created["id"]))
    crm = await db_session.scalar(select(SourceSystem).where(SourceSystem.key == "crm"))
    assert key is not None and crm is not None
    assert key.source_system_id == crm.id


@pytest.mark.parametrize(
    "body",
    [
        {"name": "x", "source_system": "erp"},
        {"name": ""},
        {"name": "x" * 256},
        {"source_system": "crm"},
        {"name": "x", "key": "rs_live_chosen"},
    ],
)
async def test_create_validation(
    async_client: AsyncClient, admin: dict[str, str], body: dict[str, Any]
) -> None:
    response = await async_client.post(URL, json=body, headers=admin)

    assert response.status_code == 422
    assert_error(response.json(), "VALIDATION_ERROR")


async def test_revoke(
    async_client: AsyncClient,
    admin: dict[str, str],
    db_session: AsyncSession,
    clock: MutableClock,
) -> None:
    created = await create(async_client, admin)
    clock.advance(minutes=5)

    response = await async_client.delete(f"{URL}/{created['id']}", headers=admin)

    assert response.status_code == 204
    assert response.content == b""
    key = await db_session.get(ApiKey, uuid.UUID(created["id"]))
    assert key is not None
    await db_session.refresh(key)
    assert key.revoked_at is not None
    assert key.revoked_at.replace(microsecond=0) == START.replace(minute=5)
    [entry] = await audit_actions(db_session, "api_key.revoke")
    assert entry.target_id == created["id"]


async def test_revoking_twice_changes_nothing(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    created = await create(async_client, admin)
    await async_client.delete(f"{URL}/{created['id']}", headers=admin)

    response = await async_client.delete(f"{URL}/{created['id']}", headers=admin)

    assert response.status_code == 204
    assert len(await audit_actions(db_session, "api_key.revoke")) == 1


async def test_revoking_an_unknown_key_is_404(
    async_client: AsyncClient, admin: dict[str, str]
) -> None:
    response = await async_client.delete(f"{URL}/{uuid.uuid4()}", headers=admin)

    assert response.status_code == 404
    assert_error(response.json(), "NOT_FOUND")


@pytest.mark.parametrize("role", ["viewer", "analyst"])
async def test_only_admins_manage_keys(
    async_client: AsyncClient, make_user: MakeUser, login: Login, role: str
) -> None:
    headers = bearer(await login(await make_user(role)))

    for method, path in (("GET", URL), ("POST", URL), ("DELETE", f"{URL}/{uuid.uuid4()}")):
        response = await async_client.request(method, path, json={"name": "x"}, headers=headers)
        assert response.status_code == 403, (method, path)
        assert_error(response.json(), "FORBIDDEN")


async def test_keys_need_a_session(async_client: AsyncClient) -> None:
    response = await async_client.get(URL)

    assert response.status_code == 401
    assert_error(response.json(), "UNAUTHENTICATED")
