"""`/api/v1/auth/*` against a real database (04 §2, T-007)."""

import pytest
from authkit import PASSWORD, Login, MakeUser, MutableClock, assert_error, bearer
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_token, ws_tickets
from app.models import AuditLog, RefreshToken, User

pytestmark = [pytest.mark.db, pytest.mark.asyncio, pytest.mark.usefixtures("api")]

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
FETCH = {"X-Requested-With": "fetch"}


async def post_login(client: AsyncClient, email: str, password: str = PASSWORD) -> Response:
    return await client.post(LOGIN, json={"email": email, "password": password})


async def refresh_with(client: AsyncClient, token: str) -> Response:
    """Send exactly this refresh token, whatever the cookie jar holds."""
    client.cookies.clear()
    return await client.post(REFRESH, headers={**FETCH, "Cookie": f"refresh_token={token}"})


def refresh_cookie(response: Response) -> str:
    return response.cookies["refresh_token"]


async def audit_actions(session: AsyncSession, user: User) -> list[str]:
    rows = await session.scalars(
        select(AuditLog.action)
        .where(AuditLog.target_id == str(user.id))
        .order_by(AuditLog.created_at)
    )
    return list(rows)


# --------------------------------------------------------------------------------------- login


async def test_login_returns_tokens_and_sets_the_refresh_cookie(
    async_client: AsyncClient, make_user: MakeUser, db_session: AsyncSession, clock: MutableClock
) -> None:
    user = await make_user("admin", full_name="Ana Lopez")

    response = await post_login(async_client, user.email)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["access_token"].count(".") == 2
    assert body["user"] == {
        "id": str(user.id),
        "email": user.email,
        "full_name": "Ana Lopez",
        "role": "admin",
    }
    cookie = response.headers["set-cookie"].lower()
    assert "refresh_token=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/api/v1/auth" in cookie
    assert "secure" not in cookie  # APP_ENV=test; production adds Secure
    assert "max-age=604800" in cookie
    await db_session.refresh(user)
    assert user.last_login_at == clock.now()
    assert await audit_actions(db_session, user) == ["user.login"]


async def test_login_stores_only_the_refresh_token_hash(
    async_client: AsyncClient, make_user: MakeUser, db_session: AsyncSession
) -> None:
    user = await make_user()

    raw = refresh_cookie(await post_login(async_client, user.email))

    stored = await db_session.scalar(select(RefreshToken).where(RefreshToken.user_id == user.id))
    assert stored is not None
    assert stored.token_hash == hash_token(raw)
    assert stored.token_hash != raw


async def test_login_ignores_email_case(async_client: AsyncClient, make_user: MakeUser) -> None:
    user = await make_user(email="ana.lopez@example.com")

    response = await post_login(async_client, "Ana.Lopez@Example.com")

    assert response.status_code == 200
    assert response.json()["user"]["id"] == str(user.id)


@pytest.mark.parametrize("case", ["wrong-password", "unknown-email", "deactivated"])
async def test_login_failures_look_the_same(
    async_client: AsyncClient, make_user: MakeUser, case: str
) -> None:
    user = await make_user(is_active=case != "deactivated")
    email = "nobody@example.com" if case == "unknown-email" else user.email
    password = "Wrong-password-1" if case == "wrong-password" else PASSWORD

    response = await post_login(async_client, email, password)

    assert response.status_code == 401
    assert_error(response.json(), "INVALID_CREDENTIALS")
    assert response.json()["error"]["message"] == "Invalid email or password"
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": PASSWORD},
        {"email": "ana@example.com"},
        {"email": "ana@example.com", "password": PASSWORD, "remember": True},
        {"email": "ana@example.com", "password": "x" * 256},
    ],
    ids=["bad-email", "missing-password", "unknown-field", "too-long"],
)
async def test_login_validation(async_client: AsyncClient, payload: dict[str, object]) -> None:
    response = await async_client.post(LOGIN, json=payload)

    assert response.status_code == 422
    assert_error(response.json(), "VALIDATION_ERROR")


async def test_login_is_rate_limited_after_five_failures(
    async_client: AsyncClient, make_user: MakeUser, clock: MutableClock
) -> None:
    user = await make_user()
    for _ in range(5):
        assert (await post_login(async_client, user.email, "Wrong-password-1")).status_code == 401
        clock.advance(seconds=1)

    blocked = await post_login(async_client, user.email)  # even the right password

    assert blocked.status_code == 429
    assert_error(blocked.json(), "RATE_LIMITED")
    assert blocked.headers["Retry-After"] == "55"

    clock.advance(seconds=55)
    assert (await post_login(async_client, user.email)).status_code == 200


async def test_rate_limit_is_per_email(async_client: AsyncClient, make_user: MakeUser) -> None:
    locked, other = await make_user(), await make_user()
    for _ in range(5):
        await post_login(async_client, locked.email, "Wrong-password-1")

    assert (await post_login(async_client, other.email)).status_code == 200


# ------------------------------------------------------------------------------------- refresh


async def test_refresh_rotates_the_token(
    async_client: AsyncClient, make_user: MakeUser, db_session: AsyncSession
) -> None:
    user = await make_user()
    first = refresh_cookie(await post_login(async_client, user.email))

    response = await refresh_with(async_client, first)

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"] == str(user.id)
    assert body["expires_in"] == 900
    second = refresh_cookie(response)
    assert second != first
    old = await db_session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(first))
    )
    new = await db_session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(second))
    )
    assert old is not None and new is not None
    await db_session.refresh(old)
    assert old.revoked_at is not None
    assert old.replaced_by == new.id
    assert new.family_id == old.family_id


async def test_reusing_a_rotated_token_revokes_the_family(
    async_client: AsyncClient, make_user: MakeUser
) -> None:
    user = await make_user()
    first = refresh_cookie(await post_login(async_client, user.email))
    second = refresh_cookie(await refresh_with(async_client, first))

    reuse = await refresh_with(async_client, first)

    assert reuse.status_code == 401
    assert_error(reuse.json(), "UNAUTHENTICATED")
    # The thief's copy and the legitimate successor are both dead now.
    assert (await refresh_with(async_client, second)).status_code == 401


async def test_reuse_leaves_other_sessions_alone(
    async_client: AsyncClient, make_user: MakeUser
) -> None:
    user = await make_user()
    laptop = refresh_cookie(await post_login(async_client, user.email))
    phone = refresh_cookie(await post_login(async_client, user.email))
    await refresh_with(async_client, laptop)

    await refresh_with(async_client, laptop)  # reuse

    assert (await refresh_with(async_client, phone)).status_code == 200


async def test_refresh_needs_the_csrf_header(
    async_client: AsyncClient, make_user: MakeUser
) -> None:
    user = await make_user()
    token = refresh_cookie(await post_login(async_client, user.email))
    async_client.cookies.clear()

    response = await async_client.post(REFRESH, headers={"Cookie": f"refresh_token={token}"})

    assert response.status_code == 401
    assert_error(response.json(), "UNAUTHENTICATED")


@pytest.mark.parametrize("token", [None, "not-a-real-token"], ids=["missing", "unknown"])
async def test_refresh_rejects_missing_or_unknown_tokens(
    async_client: AsyncClient, token: str | None
) -> None:
    if token is None:
        response = await async_client.post(REFRESH, headers=FETCH)
    else:
        response = await refresh_with(async_client, token)

    assert response.status_code == 401
    assert_error(response.json(), "UNAUTHENTICATED")


async def test_refresh_token_expires_after_seven_days(
    async_client: AsyncClient, make_user: MakeUser, clock: MutableClock
) -> None:
    user = await make_user()
    token = refresh_cookie(await post_login(async_client, user.email))

    clock.advance(days=7)

    assert (await refresh_with(async_client, token)).status_code == 401


async def test_refresh_rejects_deactivated_users(
    async_client: AsyncClient, make_user: MakeUser, db_session: AsyncSession
) -> None:
    user = await make_user()
    token = refresh_cookie(await post_login(async_client, user.email))
    user.is_active = False
    await db_session.commit()

    assert (await refresh_with(async_client, token)).status_code == 401


# -------------------------------------------------------------------------------- me / logout


async def test_me_returns_the_user_object(
    async_client: AsyncClient, make_user: MakeUser, login: Login
) -> None:
    user = await make_user("viewer", full_name="Riya Sharma")
    token = await login(user)

    response = await async_client.get("/api/v1/auth/me", headers=bearer(token))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["email"] == user.email
    assert body["full_name"] == "Riya Sharma"
    assert body["role"] == "viewer"
    assert body["is_active"] is True
    assert body["created_at"]
    assert body["last_login_at"] is not None
    assert "password_hash" not in body


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer nope"}, {"Authorization": "Basic dXNlcjpwYXNz"}],
    ids=["missing", "invalid", "wrong-scheme"],
)
async def test_me_requires_a_valid_token(
    async_client: AsyncClient, headers: dict[str, str]
) -> None:
    response = await async_client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 401
    assert_error(response.json(), "UNAUTHENTICATED")


async def test_access_token_expires_after_15_minutes(
    async_client: AsyncClient, make_user: MakeUser, login: Login, clock: MutableClock
) -> None:
    token = await login(await make_user())

    clock.advance(minutes=14, seconds=59)
    assert (await async_client.get("/api/v1/auth/me", headers=bearer(token))).status_code == 200
    clock.advance(seconds=1)
    assert (await async_client.get("/api/v1/auth/me", headers=bearer(token))).status_code == 401


async def test_deactivation_blocks_existing_access_tokens(
    async_client: AsyncClient, make_user: MakeUser, login: Login, db_session: AsyncSession
) -> None:
    user = await make_user()
    token = await login(user)
    user.is_active = False
    await db_session.commit()

    assert (await async_client.get("/api/v1/auth/me", headers=bearer(token))).status_code == 401


async def test_logout_revokes_the_family_and_clears_the_cookie(
    async_client: AsyncClient, make_user: MakeUser
) -> None:
    user = await make_user()
    response = await post_login(async_client, user.email)
    token, access = refresh_cookie(response), response.json()["access_token"]

    logout = await async_client.post("/api/v1/auth/logout", headers=bearer(access))

    assert logout.status_code == 204
    assert logout.content == b""
    cleared = logout.headers["set-cookie"].lower()
    assert "refresh_token=" in cleared and "max-age=0" in cleared
    assert "path=/api/v1/auth" in cleared
    assert (await refresh_with(async_client, token)).status_code == 401


async def test_logout_requires_authentication(async_client: AsyncClient) -> None:
    response = await async_client.post("/api/v1/auth/logout")

    assert response.status_code == 401


async def test_logout_cannot_revoke_someone_elses_token(
    async_client: AsyncClient, make_user: MakeUser, login: Login
) -> None:
    victim, attacker = await make_user(), await make_user()
    victim_token = refresh_cookie(await post_login(async_client, victim.email))
    attacker_access = await login(attacker)
    async_client.cookies.clear()

    await async_client.post(
        "/api/v1/auth/logout",
        headers={**bearer(attacker_access), "Cookie": f"refresh_token={victim_token}"},
    )

    assert (await refresh_with(async_client, victim_token)).status_code == 200


# ----------------------------------------------------------------------------- change password


async def test_change_password(
    async_client: AsyncClient, make_user: MakeUser, db_session: AsyncSession
) -> None:
    user = await make_user()
    other_device = refresh_cookie(await post_login(async_client, user.email))
    this_device = await post_login(async_client, user.email)
    current = refresh_cookie(this_device)
    async_client.cookies.clear()

    response = await async_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "Brand-new-pass-77"},
        headers={
            **bearer(this_device.json()["access_token"]),
            "Cookie": f"refresh_token={current}",
        },
    )

    assert response.status_code == 204
    assert (await post_login(async_client, user.email)).status_code == 401
    assert (await post_login(async_client, user.email, "Brand-new-pass-77")).status_code == 200
    assert (await refresh_with(async_client, other_device)).status_code == 401
    assert (await refresh_with(async_client, current)).status_code == 200
    assert "user.password_change" in await audit_actions(db_session, user)


async def test_change_password_rejects_a_wrong_current_password(
    async_client: AsyncClient, make_user: MakeUser, login: Login
) -> None:
    token = await login(await make_user())

    response = await async_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Wrong-password-1", "new_password": "Brand-new-pass-77"},
        headers=bearer(token),
    )

    assert response.status_code == 401
    assert_error(response.json(), "INVALID_CREDENTIALS")


async def test_change_password_needs_twelve_characters(
    async_client: AsyncClient, make_user: MakeUser, login: Login
) -> None:
    token = await login(await make_user())

    response = await async_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "short-pass1"},
        headers=bearer(token),
    )

    assert response.status_code == 422
    assert_error(response.json(), "VALIDATION_ERROR")


async def test_change_password_is_rate_limited(
    async_client: AsyncClient, make_user: MakeUser, login: Login
) -> None:
    token = await login(await make_user())
    attempt = {"current_password": "Wrong-password-1", "new_password": "Brand-new-pass-77"}
    for _ in range(5):
        response = await async_client.post(
            "/api/v1/auth/change-password", json=attempt, headers=bearer(token)
        )
        assert response.status_code == 401

    blocked = await async_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "Brand-new-pass-77"},
        headers=bearer(token),
    )

    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


# ---------------------------------------------------------------------------------- ws ticket


async def test_ws_ticket_is_issued_for_the_caller(
    async_client: AsyncClient, make_user: MakeUser, login: Login, clock: MutableClock
) -> None:
    user = await make_user("viewer")
    token = await login(user)

    response = await async_client.post("/api/v1/auth/ws-ticket", headers=bearer(token))

    assert response.status_code == 200
    body = response.json()
    assert body["expires_in"] == 60
    assert body["ticket"].startswith("wst_")
    assert ws_tickets.consume(body["ticket"], clock.now()) == user.id
    assert ws_tickets.consume(body["ticket"], clock.now()) is None


async def test_ws_ticket_requires_authentication(async_client: AsyncClient) -> None:
    assert (await async_client.post("/api/v1/auth/ws-ticket")).status_code == 401
