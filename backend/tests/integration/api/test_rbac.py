"""`require_role` on sample routes: viewer < analyst < admin (03 §M11, T-007)."""

from typing import Annotated

import pytest
from authkit import Login, MakeUser, assert_error, bearer
from fastapi import APIRouter, Depends
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.main import app
from app.models import User

pytestmark = [pytest.mark.db, pytest.mark.asyncio, pytest.mark.usefixtures("api")]

sample = APIRouter(prefix="/test-rbac")


@sample.get("/viewer")
async def viewer_route(user: Annotated[User, Depends(require_role("viewer"))]) -> dict[str, str]:
    return {"role": user.role}


@sample.post("/analyst")
async def analyst_route(
    user: Annotated[User, Depends(require_role("analyst"))],
) -> dict[str, str]:
    return {"role": user.role}


@sample.post("/admin")
async def admin_route(user: Annotated[User, Depends(require_role("admin"))]) -> dict[str, str]:
    return {"role": user.role}


app.include_router(sample)

ALLOWED = {
    ("viewer", "viewer"): True,
    ("viewer", "analyst"): False,
    ("viewer", "admin"): False,
    ("analyst", "viewer"): True,
    ("analyst", "analyst"): True,
    ("analyst", "admin"): False,
    ("admin", "viewer"): True,
    ("admin", "analyst"): True,
    ("admin", "admin"): True,
}


@pytest.mark.parametrize(("role", "required"), sorted(ALLOWED))
async def test_role_hierarchy(
    async_client: AsyncClient, make_user: MakeUser, login: Login, role: str, required: str
) -> None:
    token = await login(await make_user(role))
    method = async_client.get if required == "viewer" else async_client.post

    response = await method(f"/test-rbac/{required}", headers=bearer(token))

    if ALLOWED[(role, required)]:
        assert response.status_code == 200
        assert response.json() == {"role": role}
    else:
        assert response.status_code == 403
        assert_error(response.json(), "FORBIDDEN")


@pytest.mark.parametrize("required", ["viewer", "analyst", "admin"])
async def test_anonymous_requests_are_unauthenticated(
    async_client: AsyncClient, required: str
) -> None:
    method = async_client.get if required == "viewer" else async_client.post

    response = await method(f"/test-rbac/{required}")

    assert response.status_code == 401
    assert_error(response.json(), "UNAUTHENTICATED")


async def test_role_changes_apply_to_existing_tokens(
    async_client: AsyncClient, make_user: MakeUser, login: Login, db_session: AsyncSession
) -> None:
    """The role is read from the database on every request, not trusted from the token."""
    user = await make_user("admin")
    token = await login(user)
    user.role = "viewer"
    await db_session.commit()

    response = await async_client.post("/test-rbac/admin", headers=bearer(token))

    assert response.status_code == 403


async def test_unknown_role_is_a_programming_error() -> None:
    with pytest.raises(ValueError):
        require_role("superuser")
