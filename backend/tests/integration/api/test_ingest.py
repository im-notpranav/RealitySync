"""`/ingest/events` (04 §5, 03 §M1; FR-ING-002…006, 009, 010; T-011)."""

import json
import uuid
from collections.abc import Generator
from datetime import timedelta
from typing import Any

import pytest
import pytest_asyncio
from authkit import START, Login, MakeUser, MutableClock, assert_error, bearer
from httpx import AsyncClient
from ingestkit import (
    ACCOUNT_EVENT,
    EVENTS_BY_TYPE,
    INVOICE_EVENT,
    SUBSCRIPTION_EVENT,
    TICKET_EVENT,
    api_key,
    event,
    expected_idempotency_key,
)
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed import default_source_systems
from app.models import ApiKey, AuditLog, IngestEvent, SourceSystem
from app.services.ingest_service import api_key_limiter

pytestmark = [pytest.mark.db, pytest.mark.asyncio, pytest.mark.usefixtures("api", "systems")]

URL = "/api/v1/ingest/events"


@pytest_asyncio.fixture
async def systems(db_session: AsyncSession) -> dict[str, uuid.UUID]:
    """System key → id (ids, not ORM objects: `stored()` expires every loaded object)."""
    await db_session.execute(
        insert(SourceSystem)
        .values(default_source_systems())
        .on_conflict_do_nothing(index_elements=["key"])
    )
    await db_session.commit()
    rows = await db_session.execute(select(SourceSystem.key, SourceSystem.id))
    return {key: system_id for key, system_id in rows}


@pytest.fixture(autouse=True)
def fresh_api_key_limiter() -> Generator[None, None, None]:
    api_key_limiter.clear()
    yield
    api_key_limiter.clear()


@pytest_asyncio.fixture
async def admin(make_user: MakeUser, login: Login) -> dict[str, str]:
    return bearer(await login(await make_user("admin")))


async def new_key(client: AsyncClient, admin: dict[str, str], source: str | None = None) -> str:
    response = await client.post(
        "/api/v1/api-keys", json={"name": "feed", "source_system": source}, headers=admin
    )
    assert response.status_code == 201, response.text
    secret: str = response.json()["key"]
    return secret


async def send(
    client: AsyncClient, headers: dict[str, str], *events: dict[str, Any]
) -> dict[str, Any]:
    response = await client.post(URL, json={"events": list(events)}, headers=headers)
    assert response.status_code == 202, response.text
    body: dict[str, Any] = response.json()
    return body


async def stored(session: AsyncSession) -> list[IngestEvent]:
    session.expire_all()
    return list(await session.scalars(select(IngestEvent).order_by(IngestEvent.external_id)))


# ------------------------------------------------------------------------------ accepting


async def test_the_documented_batch_is_accepted(
    async_client: AsyncClient,
    admin: dict[str, str],
    db_session: AsyncSession,
    systems: dict[str, uuid.UUID],
) -> None:
    body = await send(async_client, admin, ACCOUNT_EVENT, SUBSCRIPTION_EVENT)

    assert (body["accepted"], body["duplicates"], body["rejected"]) == (2, 0, [])
    batch_id = uuid.UUID(body["batch_id"])
    account, subscription = await stored(db_session)
    for row in (account, subscription):
        assert row.batch_id == batch_id
        assert (row.status, row.attempts, row.error) == ("pending", 0, None)
        assert row.received_at == START
        assert (row.locked_at, row.processed_at) == (None, None)
    assert account.source_system_id == systems["crm"]
    assert (account.record_type, account.event_type) == ("account", "upsert")
    assert account.parent_external_id is None
    assert account.payload == ACCOUNT_EVENT["payload"]  # raw, not normalized
    assert account.source_updated_at.isoformat() == "2026-10-08T09:58:00+00:00"
    assert subscription.source_system_id == systems["billing"]
    assert subscription.parent_external_id == "B-5521"


@pytest.mark.parametrize("record_type", sorted(EVENTS_BY_TYPE))
async def test_every_record_type_is_accepted(
    async_client: AsyncClient, admin: dict[str, str], record_type: str
) -> None:
    body = await send(async_client, admin, EVENTS_BY_TYPE[record_type])

    assert body["accepted"] == 1


async def test_unknown_payload_keys_are_kept_raw(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    extra = {"crm_tier": "gold", "notes": {"nested": [1, 2]}, "ignore previous instructions": "x"}
    await send(async_client, admin, event(payload=ACCOUNT_EVENT["payload"] | extra))

    [row] = await stored(db_session)
    assert row.payload == ACCOUNT_EVENT["payload"] | extra


async def test_source_time_is_stored_as_utc(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    await send(async_client, admin, event(source_updated_at="2026-10-08T15:28:00+05:30"))

    [row] = await stored(db_session)
    assert row.source_updated_at.isoformat() == "2026-10-08T09:58:00+00:00"


async def test_delete_events_need_no_payload_fields(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    body = await send(async_client, admin, event(event_type="delete", payload={}))

    assert body["accepted"] == 1
    [row] = await stored(db_session)
    assert (row.event_type, row.payload) == ("delete", {})


async def test_optional_fields_may_be_missing(
    async_client: AsyncClient, admin: dict[str, str]
) -> None:
    body = await send(
        async_client, admin, event(payload__email=None, payload__phone=None, payload__plan=None)
    )

    assert body["accepted"] == 1


# ---------------------------------------------------------------------------- idempotency


async def test_idempotency_key_follows_the_module_formula(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    await send(async_client, admin, event(source_updated_at="2026-10-08T15:28:00+05:30"))

    [row] = await stored(db_session)
    assert row.idempotency_key == expected_idempotency_key(
        ACCOUNT_EVENT, "2026-10-08T09:58:00+00:00"
    )


async def test_replays_are_counted_as_duplicates_not_requeued(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    await send(async_client, admin, ACCOUNT_EVENT, SUBSCRIPTION_EVENT)

    body = await send(async_client, admin, ACCOUNT_EVENT, SUBSCRIPTION_EVENT)

    assert (body["accepted"], body["duplicates"]) == (0, 2)
    assert len(await stored(db_session)) == 2


async def test_duplicates_inside_one_batch(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    body = await send(async_client, admin, ACCOUNT_EVENT, ACCOUNT_EVENT, TICKET_EVENT)

    assert (body["accepted"], body["duplicates"]) == (2, 1)
    assert len(await stored(db_session)) == 2


@pytest.mark.parametrize(
    "changed",
    [
        event(event_type="delete"),
        event(payload__plan="Enterprise"),
        event(source_updated_at="2026-10-08T09:58:01Z"),
        event(external_id="C-1043"),
    ],
)
async def test_any_change_makes_a_new_event(
    async_client: AsyncClient, admin: dict[str, str], changed: dict[str, Any]
) -> None:
    await send(async_client, admin, ACCOUNT_EVENT)

    body = await send(async_client, admin, changed)

    assert (body["accepted"], body["duplicates"]) == (1, 0)


async def test_a_client_idempotency_key_is_used_as_is(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    await send(async_client, admin, event(idempotency_key="crm-export-42"))

    body = await send(
        async_client, admin, event(idempotency_key="crm-export-42", payload__plan="x")
    )

    assert body["duplicates"] == 1
    [row] = await stored(db_session)
    assert row.idempotency_key == "crm-export-42"


# ----------------------------------------------------------------------------- rejections


async def test_invalid_events_are_rejected_and_the_rest_accepted(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    body = await send(
        async_client,
        admin,
        ACCOUNT_EVENT,
        event(external_id="C-2", payload__email="not-an-email"),
        TICKET_EVENT,
    )

    assert (body["accepted"], body["duplicates"]) == (2, 0)
    [rejection] = body["rejected"]
    assert rejection["index"] == 1
    assert rejection["code"] == "VALIDATION_ERROR"
    assert "payload.email is not a valid email" in rejection["message"]
    assert "not-an-email" not in rejection["message"]  # messages never echo values
    assert [r.external_id for r in await stored(db_session)] == ["C-1042", "T-1"]


@pytest.mark.parametrize(
    ("base", "field"),
    [
        (ACCOUNT_EVENT, "name"),
        (ACCOUNT_EVENT, "created_at"),
        (SUBSCRIPTION_EVENT, "plan"),
        (SUBSCRIPTION_EVENT, "status"),
        (SUBSCRIPTION_EVENT, "started_at"),
        (INVOICE_EVENT, "amount"),
        (INVOICE_EVENT, "currency"),
        (INVOICE_EVENT, "status"),
        (INVOICE_EVENT, "issued_at"),
        (TICKET_EVENT, "subject"),
        (TICKET_EVENT, "status"),
        (TICKET_EVENT, "opened_at"),
    ],
)
async def test_required_payload_fields(
    async_client: AsyncClient, admin: dict[str, str], base: dict[str, Any], field: str
) -> None:
    missing = event(base, **{f"payload__{field}": None})
    blank = event(base, **{f"payload__{field}": "  "})

    body = await send(async_client, admin, missing, blank)

    assert body["accepted"] == 0
    assert len(body["rejected"]) == 2
    for rejection in body["rejected"]:
        assert f"payload.{field} is required" in rejection["message"]


TIMESTAMP = "is not a valid timestamp"


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        (event(payload__created_at="2025-11-02T10:00:00"), f"payload.created_at {TIMESTAMP}"),
        (event(payload__created_at="02/11/25"), f"payload.created_at {TIMESTAMP}"),
        (event(payload__name=42), "payload.name must be a string"),
        (event(payload__external_refs=["C-1"]), "payload.external_refs must be an object"),
        (event(INVOICE_EVENT, payload__amount="1.299,00"), "payload.amount is not a valid amount"),
        (event(INVOICE_EVENT, payload__currency="rupees"), "payload.currency must be a three"),
        (event(SUBSCRIPTION_EVENT, payload__quantity=-1), "payload.quantity must be a whole"),
        (event(SUBSCRIPTION_EVENT, payload__quantity=True), "payload.quantity must be a whole"),
        (event(SUBSCRIPTION_EVENT, payload__currency=None), "payload.amount is not a valid"),
        (event(TICKET_EVENT, payload__first_response_at="soon"), "payload.first_response_at"),
        (event(INVOICE_EVENT, payload__due_at="2026-10-30"), f"payload.due_at {TIMESTAMP}"),
    ],
)
async def test_payload_field_types(
    async_client: AsyncClient, admin: dict[str, str], bad: dict[str, Any], message: str
) -> None:
    body = await send(async_client, admin, bad)

    [rejection] = body["rejected"]
    assert rejection["code"] == "VALIDATION_ERROR"
    assert message in rejection["message"]


async def test_unknown_statuses_plans_and_priorities_are_accepted(
    async_client: AsyncClient, admin: dict[str, str]
) -> None:
    """They are flagged during normalization (03 §M2), not refused at the door."""
    body = await send(
        async_client,
        admin,
        event(payload__status="VIP", payload__plan="Platinum"),
        event(TICKET_EVENT, payload__priority="asap"),
    )

    assert body["accepted"] == 2


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        (event(source="erp"), "source"),
        (event(record_type="contact"), "record_type"),
        (event(event_type="merge"), "event_type"),
        (event(external_id=""), "external_id"),
        (event(external_id="x" * 256), "external_id"),
        (event(source_updated_at="2026-10-08T09:58:00"), "time zone"),
        (event(source_updated_at="08/10/26"), "four-digit year"),
        (event(source_updated_at=None), "source_updated_at"),
        (event(payload=["not", "an", "object"]), "payload"),
        (event(unexpected="field"), "unexpected"),
        (event(SUBSCRIPTION_EVENT, parent_external_id=None), "parent_external_id is required"),
        (event(TICKET_EVENT, parent_external_id=None), "parent_external_id is required"),
    ],
)
async def test_event_shape(
    async_client: AsyncClient, admin: dict[str, str], bad: dict[str, Any], message: str
) -> None:
    body = await send(async_client, admin, bad)

    [rejection] = body["rejected"]
    assert rejection["code"] == "VALIDATION_ERROR"
    assert message in rejection["message"]


async def test_non_object_events_are_rejected(
    async_client: AsyncClient, admin: dict[str, str]
) -> None:
    response = await async_client.post(
        URL, json={"events": [ACCOUNT_EVENT, "text", 3, None]}, headers=admin
    )

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] == 1
    assert [r["index"] for r in body["rejected"]] == [1, 2, 3]


async def test_inactive_sources_are_rejected(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    await db_session.execute(
        update(SourceSystem).where(SourceSystem.key == "support").values(is_active=False)
    )
    await db_session.commit()

    body = await send(async_client, admin, TICKET_EVENT, ACCOUNT_EVENT)

    assert body["accepted"] == 1
    [rejection] = body["rejected"]
    assert rejection["index"] == 0
    assert "not an active source system" in rejection["message"]


async def test_payloads_over_16_kb_are_rejected(
    async_client: AsyncClient, admin: dict[str, str]
) -> None:
    body = await send(async_client, admin, event(payload__notes="x" * 16_500))

    [rejection] = body["rejected"]
    assert "larger than 16 KB" in rejection["message"]


async def test_nan_in_a_payload_is_rejected(
    async_client: AsyncClient, admin: dict[str, str]
) -> None:
    raw = json.dumps({"events": [event(payload__score=float("nan"))]})

    response = await async_client.post(
        URL, content=raw, headers=admin | {"Content-Type": "application/json"}
    )

    assert response.status_code == 202
    [rejection] = response.json()["rejected"]
    assert "NaN" in rejection["message"]


async def test_more_than_500_events_is_413(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    events = [event(external_id=f"C-{n}") for n in range(501)]

    response = await async_client.post(URL, json={"events": events}, headers=admin)

    assert response.status_code == 413
    assert_error(response.json(), "PAYLOAD_TOO_LARGE")
    assert await stored(db_session) == []


async def test_500_events_are_accepted(async_client: AsyncClient, admin: dict[str, str]) -> None:
    events = [event(external_id=f"C-{n}") for n in range(500)]

    body = await send(async_client, admin, *events)

    assert body["accepted"] == 500


@pytest.mark.parametrize(
    "body", [{"events": []}, {}, {"events": "x"}, {"events": [ACCOUNT_EVENT], "extra": 1}]
)
async def test_batch_shape(
    async_client: AsyncClient, admin: dict[str, str], body: dict[str, Any]
) -> None:
    response = await async_client.post(URL, json=body, headers=admin)

    assert response.status_code == 422
    assert_error(response.json(), "VALIDATION_ERROR")


# --------------------------------------------------------------------------------- auth


async def test_ingest_needs_credentials(async_client: AsyncClient) -> None:
    response = await async_client.post(URL, json={"events": [ACCOUNT_EVENT]})

    assert response.status_code == 401
    assert_error(response.json(), "UNAUTHENTICATED")


@pytest.mark.parametrize("role", ["viewer", "analyst"])
async def test_only_admins_ingest_with_a_jwt(
    async_client: AsyncClient, make_user: MakeUser, login: Login, role: str
) -> None:
    headers = bearer(await login(await make_user(role)))

    response = await async_client.post(URL, json={"events": [ACCOUNT_EVENT]}, headers=headers)

    assert response.status_code == 403
    assert_error(response.json(), "FORBIDDEN")


async def test_an_api_key_can_ingest(
    async_client: AsyncClient,
    admin: dict[str, str],
    db_session: AsyncSession,
    clock: MutableClock,
) -> None:
    secret = await new_key(async_client, admin)
    clock.advance(minutes=1)

    body = await send(async_client, api_key(secret), ACCOUNT_EVENT, SUBSCRIPTION_EVENT)

    assert body["accepted"] == 2
    key = await db_session.scalar(select(ApiKey))
    assert key is not None
    await db_session.refresh(key)
    assert key.last_used_at == START + timedelta(minutes=1)


async def test_an_api_key_wins_over_a_bearer_token(
    async_client: AsyncClient, admin: dict[str, str], make_user: MakeUser, login: Login
) -> None:
    secret = await new_key(async_client, admin)
    viewer = bearer(await login(await make_user("viewer")))

    body = await send(async_client, viewer | api_key(secret), ACCOUNT_EVENT)

    assert body["accepted"] == 1


@pytest.mark.parametrize("secret", ["rs_live_wrong", ""])
async def test_unknown_api_keys_are_refused(async_client: AsyncClient, secret: str) -> None:
    response = await async_client.post(
        URL, json={"events": [ACCOUNT_EVENT]}, headers=api_key(secret)
    )

    assert response.status_code == 401
    assert_error(response.json(), "UNAUTHENTICATED")


async def test_revoked_api_keys_are_refused(
    async_client: AsyncClient, admin: dict[str, str]
) -> None:
    secret = await new_key(async_client, admin)
    [listed] = (await async_client.get("/api/v1/api-keys", headers=admin)).json()["items"]
    await async_client.delete(f"/api/v1/api-keys/{listed['id']}", headers=admin)

    response = await async_client.post(
        URL, json={"events": [ACCOUNT_EVENT]}, headers=api_key(secret)
    )

    assert response.status_code == 401


async def test_a_bound_key_only_sends_its_own_system(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    secret = await new_key(async_client, admin, source="billing")

    body = await send(async_client, api_key(secret), ACCOUNT_EVENT, SUBSCRIPTION_EVENT)

    assert body["accepted"] == 1
    [rejection] = body["rejected"]
    assert (rejection["index"], rejection["code"]) == (0, "FORBIDDEN")
    assert [r.external_id for r in await stored(db_session)] == ["SUB-7781"]


async def test_api_keys_are_limited_to_60_requests_a_minute(
    async_client: AsyncClient, admin: dict[str, str], clock: MutableClock
) -> None:
    secret = await new_key(async_client, admin)
    batch = {"events": [event(source="erp")]}  # rejected, cheap
    for _ in range(60):
        response = await async_client.post(URL, json=batch, headers=api_key(secret))
        assert response.status_code == 202

    limited = await async_client.post(URL, json=batch, headers=api_key(secret))

    assert limited.status_code == 429
    assert_error(limited.json(), "RATE_LIMITED")
    assert limited.headers["Retry-After"] == "60"
    # Admins sending with a JWT are not counted against the key.
    assert (await async_client.post(URL, json=batch, headers=admin)).status_code == 202
    clock.advance(seconds=60)
    assert (await async_client.post(URL, json=batch, headers=api_key(secret))).status_code == 202


# ----------------------------------------------------------------------- listing & retry


async def make_failed(session: AsyncSession) -> IngestEvent:
    await session.execute(update(IngestEvent).values(status="failed", attempts=5, error="boom"))
    await session.commit()
    [row] = await stored(session)
    return row


async def test_list_events(async_client: AsyncClient, admin: dict[str, str]) -> None:
    await send(async_client, admin, ACCOUNT_EVENT, SUBSCRIPTION_EVENT, TICKET_EVENT)

    response = await async_client.get(URL, headers=admin)

    assert response.status_code == 200
    body = response.json()
    assert (body["page"], body["page_size"], body["total"]) == (1, 25, 3)
    item = next(i for i in body["items"] if i["external_id"] == "C-1042")
    assert item == {
        "id": item["id"],
        "source": "crm",
        "record_type": "account",
        "external_id": "C-1042",
        "status": "pending",
        "attempts": 0,
        "error": None,
        "received_at": "2026-10-14T09:00:00Z",
        "processed_at": None,
    }
    assert "payload" not in response.text


async def test_list_filters(
    async_client: AsyncClient,
    admin: dict[str, str],
    db_session: AsyncSession,
    clock: MutableClock,
) -> None:
    await send(async_client, admin, ACCOUNT_EVENT)
    clock.advance(minutes=10)  # stays inside the 15-minute access token
    await send(async_client, admin, SUBSCRIPTION_EVENT, TICKET_EVENT)
    await db_session.execute(
        update(IngestEvent).where(IngestEvent.external_id == "T-1").values(status="failed")
    )
    await db_session.commit()

    async def ids(**params: str) -> list[str]:
        response = await async_client.get(URL, params=params, headers=admin)
        assert response.status_code == 200, response.text
        return sorted(i["external_id"] for i in response.json()["items"])

    assert await ids(source="billing") == ["SUB-7781"]
    assert await ids(status="failed") == ["T-1"]
    assert await ids(**{"from": "2026-10-14T09:05:00Z"}) == ["SUB-7781", "T-1"]
    assert await ids(to="2026-10-14T09:05:00+00:00") == ["C-1042"]
    assert await ids(sort="-attempts") == ["C-1042", "SUB-7781", "T-1"]


@pytest.mark.parametrize(
    "params",
    [{"from": "2026-10-14T09:30:00"}, {"status": "lost"}, {"source": "erp"}, {"sort": "payload"}],
)
async def test_list_validation(
    async_client: AsyncClient, admin: dict[str, str], params: dict[str, str]
) -> None:
    response = await async_client.get(URL, params=params, headers=admin)

    assert response.status_code == 422
    assert_error(response.json(), "VALIDATION_ERROR")


async def test_retry_puts_a_failed_event_back_in_the_queue(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    await send(async_client, admin, ACCOUNT_EVENT)
    failed = await make_failed(db_session)

    response = await async_client.post(f"{URL}/{failed.id}/retry", headers=admin)

    assert response.status_code == 202
    assert (response.json()["status"], response.json()["error"]) == ("pending", None)
    [row] = await stored(db_session)
    assert (row.status, row.error, row.attempts) == ("pending", None, 5)
    [entry] = await db_session.scalars(
        select(AuditLog).where(AuditLog.action == "ingest_event.retry")
    )
    assert entry.target_id == str(failed.id)


async def test_only_failed_events_can_be_retried(
    async_client: AsyncClient, admin: dict[str, str], db_session: AsyncSession
) -> None:
    await send(async_client, admin, ACCOUNT_EVENT)
    [row] = await stored(db_session)

    response = await async_client.post(f"{URL}/{row.id}/retry", headers=admin)

    assert response.status_code == 409
    assert_error(response.json(), "CONFLICT")


async def test_retrying_an_unknown_event_is_404(
    async_client: AsyncClient, admin: dict[str, str]
) -> None:
    response = await async_client.post(f"{URL}/{uuid.uuid4()}/retry", headers=admin)

    assert response.status_code == 404
    assert_error(response.json(), "NOT_FOUND")


@pytest.mark.parametrize("role", ["viewer", "analyst"])
async def test_listing_and_retry_are_admin_only(
    async_client: AsyncClient, make_user: MakeUser, login: Login, role: str
) -> None:
    headers = bearer(await login(await make_user(role)))

    assert (await async_client.get(URL, headers=headers)).status_code == 403
    retry = await async_client.post(f"{URL}/{uuid.uuid4()}/retry", headers=headers)
    assert retry.status_code == 403
