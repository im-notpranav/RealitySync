"""Ingest (03 §M1, 04 §5) and the API keys that authenticate it (04 §3, FR-AUT-005).

Ingest only validates and persists events (`pending`) and wakes the worker; normalization and
record updates happen asynchronously in the worker (FR-ING-006).
"""

import hashlib
import json
import math
import secrets
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import structlog
from pydantic import ValidationError
from sqlalchemy import ColumnElement, UnaryExpression, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    AppError,
    ConflictError,
    NotFoundError,
    RateLimited,
    UnauthenticatedError,
    ValidationFailed,
)
from app.core.security import hash_token
from app.domain.normalize import (
    InvalidAmount,
    InvalidTimestamp,
    normalize_amount,
    normalize_email,
    normalize_ts,
)
from app.models import ApiKey, IngestEvent, SourceSystem, User
from app.schemas.api_key import ApiKeyCreate, ApiKeyOut
from app.schemas.ingest import (
    MAX_BATCH,
    MAX_PAYLOAD_BYTES,
    IngestAccepted,
    IngestEventIn,
    IngestEventOut,
    Rejection,
)
from app.services import audit_service

log = structlog.get_logger(__name__)

API_KEY_PREFIX = "rs_live_"
# Shown in lists: the fixed prefix plus the first 8 characters of the secret part (D-063).
_DISPLAY_CHARS = len(API_KEY_PREFIX) + 8
INGEST_CHANNEL = "ingest_pending"


# ------------------------------------------------------------------------------ rate limit


class RequestLimiter:
    """At most `limit` requests per key in any `window_seconds` (sliding window, in memory)."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window = timedelta(seconds=window_seconds)
        self._hits: dict[str, deque[datetime]] = {}

    def hit(self, key: str, now: datetime) -> None:
        """Count one request, or raise `429 RATE_LIMITED` with `Retry-After` when over."""
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self._window:
            hits.popleft()
        if len(hits) >= self._limit:
            wait = (hits[0] + self._window - now).total_seconds()
            raise RateLimited(retry_after=max(1, math.ceil(wait)))
        hits.append(now)

    def clear(self) -> None:
        self._hits.clear()


api_key_limiter = RequestLimiter(limit=60, window_seconds=60)  # 04 §15, per API key


# -------------------------------------------------------------------------------- API keys


@dataclass(frozen=True)
class IngestCaller:
    """Who sent a batch: an admin (`user_id`) or a machine (`api_key`)."""

    user_id: uuid.UUID | None = None
    api_key: ApiKey | None = None


def new_api_key() -> str:
    return API_KEY_PREFIX + secrets.token_urlsafe(32)  # 256 random bits


async def _system_ids(session: AsyncSession) -> dict[uuid.UUID, str]:
    rows = await session.execute(select(SourceSystem.id, SourceSystem.key))
    return {row.id: row.key for row in rows}


def _key_out(key: ApiKey, systems: dict[uuid.UUID, str]) -> ApiKeyOut:
    return ApiKeyOut.model_validate(
        {
            "id": key.id,
            "name": key.name,
            "key_prefix": key.key_prefix,
            "source_system": systems.get(key.source_system_id) if key.source_system_id else None,
            "created_by": key.created_by,
            "created_at": key.created_at,
            "last_used_at": key.last_used_at,
            "revoked_at": key.revoked_at,
        }
    )


async def create_api_key(
    session: AsyncSession, *, actor: User, data: ApiKeyCreate, now: datetime
) -> tuple[ApiKey, str]:
    """Create a key and return it with its secret; only the sha256 of the secret is stored."""
    system_id: uuid.UUID | None = None
    if data.source_system is not None:
        system_id = await session.scalar(
            select(SourceSystem.id).where(SourceSystem.key == data.source_system)
        )
        if system_id is None:
            raise ValidationFailed(
                "Unknown source system",
                details=[{"field": "source_system", "message": "is not a configured system"}],
            )
    secret = new_api_key()
    key = ApiKey(
        name=data.name,
        key_prefix=secret[:_DISPLAY_CHARS],
        key_hash=hash_token(secret),
        source_system_id=system_id,
        created_by=actor.id,
        created_at=now,
    )
    session.add(key)
    await session.flush()
    audit_service.record(
        session,
        actor_id=actor.id,
        action="api_key.create",
        target_type="api_key",
        target_id=key.id,
        metadata={"source_system": data.source_system},
    )
    await session.commit()
    await session.refresh(key)
    return key, secret


async def list_api_keys(
    session: AsyncSession, *, page: int, page_size: int
) -> tuple[list[ApiKeyOut], int]:
    total = await session.scalar(select(func.count()).select_from(ApiKey)) or 0
    keys = await session.scalars(
        select(ApiKey)
        .order_by(ApiKey.created_at.desc(), ApiKey.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    systems = await _system_ids(session)
    return [_key_out(key, systems) for key in keys], total


async def revoke_api_key(
    session: AsyncSession, *, actor: User, key_id: uuid.UUID, now: datetime
) -> None:
    """Revoke a key. Revoking an already revoked key changes nothing."""
    key = await session.get(ApiKey, key_id)
    if key is None:
        raise NotFoundError("api_key", str(key_id))
    if key.revoked_at is not None:
        return
    key.revoked_at = now
    audit_service.record(
        session,
        actor_id=actor.id,
        action="api_key.revoke",
        target_type="api_key",
        target_id=key.id,
    )
    await session.commit()


async def authenticate_api_key(session: AsyncSession, secret: str, now: datetime) -> ApiKey:
    """The active key for `secret`, counted against its rate limit (60 requests / min)."""
    key = await session.scalar(select(ApiKey).where(ApiKey.key_hash == hash_token(secret)))
    if key is None or key.revoked_at is not None:
        raise UnauthenticatedError("Invalid API key")
    api_key_limiter.hit(str(key.id), now)
    return key


# ---------------------------------------------------------------------------------- ingest

_TEXT = "text"
_TIMESTAMP = "timestamp"
_EMAIL = "email"
_AMOUNT = "amount"
_CURRENCY = "currency"
_COUNT = "count"
_OBJECT = "object"

# 04 §5.1. Keys not listed here are stored raw and ignored by normalization.
PAYLOAD_FIELDS: dict[str, dict[str, str]] = {
    "account": {
        "name": _TEXT,
        "created_at": _TIMESTAMP,
        "email": _EMAIL,
        "phone": _TEXT,
        "status": _TEXT,
        "plan": _TEXT,
        "company": _TEXT,
        "external_refs": _OBJECT,
    },
    "subscription": {
        "plan": _TEXT,
        "status": _TEXT,
        "started_at": _TIMESTAMP,
        "amount": _AMOUNT,
        "currency": _CURRENCY,
        "cancelled_at": _TIMESTAMP,
        "quantity": _COUNT,
    },
    "invoice": {
        "amount": _AMOUNT,
        "currency": _CURRENCY,
        "status": _TEXT,
        "issued_at": _TIMESTAMP,
        "paid_at": _TIMESTAMP,
        "due_at": _TIMESTAMP,
        "subscription_external_id": _TEXT,
    },
    "ticket": {
        "subject": _TEXT,
        "status": _TEXT,
        "opened_at": _TIMESTAMP,
        "closed_at": _TIMESTAMP,
        "priority": _TEXT,
        "first_response_at": _TIMESTAMP,
    },
}
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "account": ("name", "created_at"),
    "subscription": ("plan", "status", "started_at"),
    "invoice": ("amount", "currency", "status", "issued_at"),
    "ticket": ("subject", "status", "opened_at"),
}


def canonical_json(value: Any) -> str:
    """Sorted keys, no whitespace, no NaN/Infinity (Postgres JSON rejects them)."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def idempotency_key(event: IngestEventIn) -> str:
    """`sha256(source|record_type|external_id|event_type|source_updated_at|payload_hash)`, with
    `payload_hash` the sha256 of the raw payload's canonical JSON (03 §M1)."""
    parts = (
        event.source,
        event.record_type,
        event.external_id,
        event.event_type,
        event.source_updated_at.isoformat(),  # already UTC
        _sha256(canonical_json(event.payload)),
    )
    return _sha256("|".join(parts))


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _check_text(value: Any, _payload: dict[str, Any]) -> str | None:
    return None if isinstance(value, str) else "must be a string"


def _check_timestamp(value: Any, _payload: dict[str, Any]) -> str | None:
    try:
        normalize_ts(value)
    except InvalidTimestamp as exc:
        return f"is not a valid timestamp ({exc})"
    return None


def _check_email(value: Any, _payload: dict[str, Any]) -> str | None:
    if isinstance(value, str) and normalize_email(value) is not None:
        return None
    return "is not a valid email"


def _check_amount(value: Any, payload: dict[str, Any]) -> str | None:
    currency = payload.get("currency")
    try:
        normalize_amount(value, currency if isinstance(currency, str) else None)
    except InvalidAmount as exc:
        return f"is not a valid amount ({exc})"
    return None


def _check_currency(value: Any, _payload: dict[str, Any]) -> str | None:
    code = value.strip() if isinstance(value, str) else ""
    if len(code) == 3 and code.isascii() and code.isalpha():
        return None
    return "must be a three-letter ISO 4217 code"


def _check_count(value: Any, _payload: dict[str, Any]) -> str | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return None
    return "must be a whole number ≥ 0"


def _check_object(value: Any, _payload: dict[str, Any]) -> str | None:
    return None if isinstance(value, dict) else "must be an object"


_CHECKS: dict[str, Callable[[Any, dict[str, Any]], str | None]] = {
    _TEXT: _check_text,
    _TIMESTAMP: _check_timestamp,
    _EMAIL: _check_email,
    _AMOUNT: _check_amount,
    _CURRENCY: _check_currency,
    _COUNT: _check_count,
    _OBJECT: _check_object,
}


def payload_problems(record_type: str, event_type: str, payload: dict[str, Any]) -> list[str]:
    """Problems with the documented payload fields (04 §5.1). Messages name fields, never values.

    A `delete` event only identifies the record, so its payload is not checked (D-064).
    """
    if event_type == "delete":
        return []
    problems = [
        f"payload.{field} is required"
        for field in REQUIRED_FIELDS[record_type]
        if _blank(payload.get(field))
    ]
    for field, kind in PAYLOAD_FIELDS[record_type].items():
        value = payload.get(field)
        if _blank(value):
            continue
        problem = _CHECKS[kind](value, payload)
        if problem:
            problems.append(f"payload.{field} {problem}")
    return problems


def _describe(exc: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in error['loc']) or 'event'}: {error['msg']}"
        for error in exc.errors(include_url=False)
    )


def _payload_size_problem(payload: dict[str, Any]) -> str | None:
    try:
        size = len(canonical_json(payload).encode())
    except ValueError:
        return "payload must not contain NaN or Infinity"
    if size > MAX_PAYLOAD_BYTES:
        return f"payload is larger than {MAX_PAYLOAD_BYTES // 1024} KB"
    return None


async def ingest_batch(
    session: AsyncSession, *, caller: IngestCaller, events: list[Any], now: datetime
) -> IngestAccepted:
    """Validate each event, persist the valid ones as `pending` and wake the worker.

    Invalid events are reported in `rejected` and the rest are still accepted. Replays (same
    idempotency key) are counted as `duplicates` and not queued again (FR-ING-005).
    """
    if len(events) > MAX_BATCH:
        raise AppError(
            code="PAYLOAD_TOO_LARGE",
            message=f"A batch holds at most {MAX_BATCH} events",
            status_code=413,
        )
    systems = {s.key: s for s in await session.scalars(select(SourceSystem))}
    bound_to = caller.api_key.source_system_id if caller.api_key else None
    batch_id = uuid.uuid4()
    rejected: list[Rejection] = []
    rows: list[dict[str, Any]] = []

    for index, raw in enumerate(events):
        try:
            event = IngestEventIn.model_validate(raw)
        except ValidationError as exc:
            rejected.append(Rejection(index=index, code="VALIDATION_ERROR", message=_describe(exc)))
            continue
        system = systems.get(event.source)
        if system is None or not system.is_active:
            message = f"source {event.source} is not an active source system"
            rejected.append(Rejection(index=index, code="VALIDATION_ERROR", message=message))
            continue
        if bound_to is not None and system.id != bound_to:
            message = "this API key may only send events for its own source system"
            rejected.append(Rejection(index=index, code="FORBIDDEN", message=message))
            continue
        problems = [
            p
            for p in (
                _payload_size_problem(event.payload),
                *payload_problems(event.record_type, event.event_type, event.payload),
            )
            if p
        ]
        if problems:
            message = "; ".join(problems)
            rejected.append(Rejection(index=index, code="VALIDATION_ERROR", message=message))
            continue
        rows.append(
            {
                "batch_id": batch_id,
                "source_system_id": system.id,
                "record_type": event.record_type,
                "external_id": event.external_id,
                "parent_external_id": event.parent_external_id,
                "event_type": event.event_type,
                "payload": event.payload,
                "source_updated_at": event.source_updated_at,
                "idempotency_key": event.idempotency_key or idempotency_key(event),
                "received_at": now,
            }
        )

    accepted = 0
    if rows:
        inserted = await session.scalars(
            insert(IngestEvent)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
            .returning(IngestEvent.id)
        )
        accepted = len(inserted.all())
    if accepted:
        # Delivered by Postgres only when the transaction commits, so the worker never sees an
        # uncommitted event.
        await session.execute(
            text("SELECT pg_notify(:channel, :batch)"),
            {"channel": INGEST_CHANNEL, "batch": str(batch_id)},
        )
    if caller.api_key is not None:
        caller.api_key.last_used_at = now
    await session.commit()
    log.info(
        "ingest_batch",
        batch_id=str(batch_id),
        accepted=accepted,
        duplicates=len(rows) - accepted,
        rejected=len(rejected),
    )
    return IngestAccepted(
        accepted=accepted, duplicates=len(rows) - accepted, rejected=rejected, batch_id=batch_id
    )


SORTABLE = {
    "received_at": IngestEvent.received_at,
    "processed_at": IngestEvent.processed_at,
    "attempts": IngestEvent.attempts,
}


def _order_by(sort: str | None) -> list[UnaryExpression[Any]]:
    if not sort:
        return [IngestEvent.received_at.desc(), IngestEvent.id.desc()]
    descending = sort.startswith("-")
    column = SORTABLE.get(sort.lstrip("-"))
    if column is None:
        raise ValidationFailed(
            "Invalid sort field",
            details=[{"field": "sort", "message": f"must be one of {sorted(SORTABLE)}"}],
        )
    ordered = column.desc().nulls_last() if descending else column.asc().nulls_last()
    return [ordered, IngestEvent.id.desc()]


def _event_out(event: IngestEvent, source: str) -> IngestEventOut:
    return IngestEventOut.model_validate(
        {
            "id": event.id,
            "source": source,
            "record_type": event.record_type,
            "external_id": event.external_id,
            "status": event.status,
            "attempts": event.attempts,
            "error": event.error,
            "received_at": event.received_at,
            "processed_at": event.processed_at,
        }
    )


async def list_events(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    source: str | None = None,
    received_from: datetime | None = None,
    received_to: datetime | None = None,
    sort: str | None = None,
) -> tuple[list[IngestEventOut], int]:
    filters: list[ColumnElement[bool]] = []
    if status is not None:
        filters.append(IngestEvent.status == status)
    if source is not None:
        filters.append(SourceSystem.key == source)
    if received_from is not None:
        filters.append(IngestEvent.received_at >= received_from)
    if received_to is not None:
        filters.append(IngestEvent.received_at <= received_to)

    joined = select(IngestEvent, SourceSystem.key).join(
        SourceSystem, SourceSystem.id == IngestEvent.source_system_id
    )
    total = (
        await session.scalar(
            select(func.count())
            .select_from(IngestEvent)
            .join(SourceSystem, SourceSystem.id == IngestEvent.source_system_id)
            .where(*filters)
        )
        or 0
    )
    rows = await session.execute(
        joined.where(*filters)
        .order_by(*_order_by(sort))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [_event_out(event, key) for event, key in rows], total


async def retry_event(session: AsyncSession, *, actor: User, event_id: uuid.UUID) -> IngestEventOut:
    """`failed → pending` (FR-ING-009); `409 CONFLICT` for any other status.

    `attempts` keeps counting, so the history of failures stays visible (D-064).
    """
    event = await session.get(IngestEvent, event_id, with_for_update=True)
    if event is None:
        raise NotFoundError("ingest_event", str(event_id))
    if event.status != "failed":
        raise ConflictError(f"Only failed events can be retried (status is {event.status})")
    event.status = "pending"
    event.error = None
    event.locked_at = None
    event.processed_at = None
    audit_service.record(
        session,
        actor_id=actor.id,
        action="ingest_event.retry",
        target_type="ingest_event",
        target_id=event.id,
        metadata={"attempts": event.attempts},
    )
    await session.execute(
        text("SELECT pg_notify(:channel, :event)"),
        {"channel": INGEST_CHANNEL, "event": str(event.id)},
    )
    await session.commit()
    await session.refresh(event)
    source = await session.scalar(
        select(SourceSystem.key).where(SourceSystem.id == event.source_system_id)
    )
    return _event_out(event, source or "")
