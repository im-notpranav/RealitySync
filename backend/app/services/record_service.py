"""Record upsert and versioning (03 §M1, FR-ING-007/008, FR-NRM-*).

Applies one ingest event to `source_records` (current state) and `record_versions` (history):

- **New** record → record + version 1. A `delete` for an unknown record creates a deleted
  tombstone, so an older upsert arriving later cannot bring it back.
- **Newer** event (later `source_updated_at`, or the same time and received later, 02 §3.3) →
  new current state and a new version, unless the state is unchanged (same `record_hash` and
  deletion flag): then only the raw payload and recorded time move forward, no version.
- **Older** event → a version flagged `out_of_order`; the current state is not touched. At a
  recorded time that already has a version the same tie-break applies.
- An event that loses the equal-time tie-break writes nothing: at that recorded time the winner
  is the state, and the Time Machine must not see the loser as the later version.

Everything runs under a per-record advisory lock, inside the caller's transaction.
"""

import hashlib
import unicodedata
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import func, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.normalize import (
    InvalidAmount,
    InvalidTimestamp,
    name_block,
    normalize_amount,
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_plan,
    normalize_priority,
    normalize_status,
    normalize_ts,
)
from app.models import IngestEvent, RecordVersion, SourceRecord, SourceSystem
from app.services.ingest_service import canonical_json

Outcome = Literal["created", "updated", "deleted", "unchanged", "out_of_order", "superseded"]
DELETED_FIELD = "is_deleted"  # listed in `changed_fields` when a version deletes or restores

# The field that dates the record's creation in each record type (`source_created_at`).
CREATED_FIELD = {
    "account": "created_at",
    "subscription": "started_at",
    "invoice": "issued_at",
    "ticket": "opened_at",
}


class InvalidRecord(ValueError):
    """The payload cannot be normalized. The message names the field only (no record data)."""


@dataclass(frozen=True)
class RecordChanged:
    """What applying one event did; the pipeline hands it to entity resolution (T-017)."""

    record_id: uuid.UUID
    source_system_id: uuid.UUID
    record_type: str
    external_id: str
    parent_external_id: str | None
    outcome: Outcome
    version: int | None  # the version written, if any
    changed_fields: tuple[str, ...]

    @property
    def state_changed(self) -> bool:
        """The current state moved: downstream work (resolution, detection) is needed."""
        return self.outcome in ("created", "updated", "deleted")


# ------------------------------------------------------------------------------ normalization


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _iso(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value is not None else None


def _text(value: Any) -> str | None:
    """Trimmed, NFKC, whitespace collapsed; case kept (subjects, references)."""
    if _blank(value) or not isinstance(value, str):
        return None
    return " ".join(unicodedata.normalize("NFKC", value).split())


def _company(value: Any) -> str | None:
    cleaned = _text(value)
    return cleaned.casefold() if cleaned else None


def _field(name: str, normalize: Callable[[], Any]) -> Any:
    try:
        return normalize()
    except (InvalidTimestamp, InvalidAmount, TypeError, ValueError, AttributeError) as exc:
        raise InvalidRecord(f"payload.{name} is invalid") from exc


def _ts(payload: Mapping[str, Any], name: str) -> str | None:
    value = payload.get(name)
    if _blank(value):
        return None
    return _iso(_field(name, lambda: normalize_ts(value)))


def _status(
    payload: Mapping[str, Any], record_type: str, status_mapping: Mapping[str, Any]
) -> dict[str, Any]:
    raw = payload.get("status")
    status = _field(
        "status",
        lambda: normalize_status(status_mapping, record_type, raw if _blank(raw) else str(raw)),
    )
    return {"status": status.value, "status_unmapped": status.unmapped}


def _money(payload: Mapping[str, Any]) -> dict[str, Any]:
    amount, currency = payload.get("amount"), payload.get("currency")
    given = currency.strip().upper() if isinstance(currency, str) and currency.strip() else None
    if _blank(amount):
        return {"amount": None, "currency": given}
    money = _field("amount", lambda: normalize_amount(amount, given))
    return {"amount": str(money.amount), "currency": money.currency}


def _account(payload: Mapping[str, Any], phone_region: str) -> dict[str, Any]:
    raw_name, raw_email, raw_phone = payload.get("name"), payload.get("email"), payload.get("phone")
    name = normalize_name(raw_name) if isinstance(raw_name, str) else None
    email = normalize_email(raw_email) if isinstance(raw_email, str) else None
    phone = normalize_phone(raw_phone, phone_region) if isinstance(raw_phone, str) else None
    refs = payload.get("external_refs")
    plan = payload.get("plan")
    return {
        "name": name.full if name else None,
        "name_block": name_block(name) if name else None,
        "email": email.display if email else None,
        "email_canonical": email.canonical if email else None,
        "email_domain": email.domain if email else None,
        "phone_e164": phone.e164 if phone else None,
        "company": _company(payload.get("company")),
        "plan": normalize_plan(plan) if isinstance(plan, str) else None,
        "created_at": _ts(payload, "created_at"),
        "external_refs": refs if isinstance(refs, dict) and refs else None,
    }


def _subscription(payload: Mapping[str, Any]) -> dict[str, Any]:
    plan, quantity = payload.get("plan"), payload.get("quantity")
    return {
        "plan": normalize_plan(plan) if isinstance(plan, str) else None,
        "started_at": _ts(payload, "started_at"),
        "cancelled_at": _ts(payload, "cancelled_at"),
        "quantity": quantity
        if isinstance(quantity, int) and not isinstance(quantity, bool)
        else None,
        **_money(payload),
    }


def _invoice(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "issued_at": _ts(payload, "issued_at"),
        "paid_at": _ts(payload, "paid_at"),
        "due_at": _ts(payload, "due_at"),
        "subscription_external_id": _text(payload.get("subscription_external_id")),
        **_money(payload),
    }


def _ticket(payload: Mapping[str, Any]) -> dict[str, Any]:
    priority = payload.get("priority")
    return {
        "subject": _text(payload.get("subject")),
        "priority": normalize_priority(priority) if isinstance(priority, str) else None,
        "opened_at": _ts(payload, "opened_at"),
        "closed_at": _ts(payload, "closed_at"),
        "first_response_at": _ts(payload, "first_response_at"),
    }


def normalize_record(
    record_type: str,
    payload: Mapping[str, Any],
    *,
    parent_external_id: str | None,
    status_mapping: Mapping[str, Any],
    phone_region: str,
) -> dict[str, Any]:
    """The `normalized` JSON of a record (03 §M2): every key of its record type, `None` when
    missing or unreadable. JSON-safe: timestamps are ISO 8601 UTC (`Z`), amounts decimal
    strings. Keys outside 04 §5.1 are ignored (D-025). Raises `InvalidRecord`."""
    if record_type == "account":
        fields = _account(payload, phone_region)
    elif record_type == "subscription":
        fields = _subscription(payload)
    elif record_type == "invoice":
        fields = _invoice(payload)
    elif record_type == "ticket":
        fields = _ticket(payload)
    else:
        raise InvalidRecord("record_type is unknown")
    return {
        **fields,
        **_status(payload, record_type, status_mapping),
        "parent_external_id": parent_external_id,
    }


def record_hash(normalized: Mapping[str, Any]) -> str:
    """sha256 of the canonical JSON of the normalized fields (03 §M1)."""
    return hashlib.sha256(canonical_json(normalized).encode()).hexdigest()


def changed_fields(before: Mapping[str, Any] | None, after: Mapping[str, Any]) -> list[str]:
    """Normalized keys whose value differs; against nothing, the keys that have a value."""
    if before is None:
        return sorted(key for key, value in after.items() if value is not None)
    return sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))


# ----------------------------------------------------------------------------------- upsert


def record_lock_key(source_system_id: uuid.UUID, record_type: str, external_id: str) -> str:
    """The text whose `hashtext` is the record's advisory lock (02 §3.3, rule 1)."""
    return f"{source_system_id}{record_type}{external_id}"


async def lock_record(
    session: AsyncSession, source_system_id: uuid.UUID, record_type: str, external_id: str
) -> None:
    """Serialize work on one record until the transaction ends."""
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": record_lock_key(source_system_id, record_type, external_id)},
    )


async def _wins_tie(session: AsyncSession, event: IngestEvent) -> bool:
    """At an equal recorded time the event received last wins, then the higher id (02 §3.3).

    The state at that time came from an already processed event; this one wins unless one of
    them was received after it.
    """
    later = await session.scalar(
        select(IngestEvent.id)
        .where(
            IngestEvent.source_system_id == event.source_system_id,
            IngestEvent.record_type == event.record_type,
            IngestEvent.external_id == event.external_id,
            IngestEvent.source_updated_at == event.source_updated_at,
            IngestEvent.status == "processed",
            tuple_(IngestEvent.received_at, IngestEvent.id) > (event.received_at, event.id),
        )
        .limit(1)
    )
    return later is None


async def _next_version(session: AsyncSession, record_id: uuid.UUID) -> int:
    latest = await session.scalar(
        select(func.max(RecordVersion.version)).where(RecordVersion.source_record_id == record_id)
    )
    return (latest or 0) + 1


def _version(
    record: SourceRecord,
    *,
    version: int,
    payload: dict[str, Any],
    normalized: dict[str, Any],
    changed: list[str],
    recorded_at: datetime,
    is_deleted: bool,
    out_of_order: bool = False,
) -> RecordVersion:
    return RecordVersion(
        source_record_id=record.id,
        source_system_id=record.source_system_id,
        version=version,
        payload=payload,
        normalized=normalized,
        changed_fields=changed,
        source_updated_at=recorded_at,
        is_deleted=is_deleted,
        out_of_order=out_of_order,
    )


def _created_at(record_type: str, normalized: Mapping[str, Any]) -> datetime | None:
    value = normalized.get(CREATED_FIELD[record_type])
    return datetime.fromisoformat(value) if isinstance(value, str) else None


async def apply_event(
    session: AsyncSession, event: IngestEvent, *, phone_region: str
) -> RecordChanged:
    """Apply one ingest event to its record (03 §M1). Flushes; the caller commits."""
    system = await session.get(SourceSystem, event.source_system_id)
    if system is None:
        raise InvalidRecord("source system is unknown")
    await lock_record(session, event.source_system_id, event.record_type, event.external_id)
    record = await session.scalar(
        select(SourceRecord).where(
            SourceRecord.source_system_id == event.source_system_id,
            SourceRecord.record_type == event.record_type,
            SourceRecord.external_id == event.external_id,
        )
    )
    deleting = event.event_type == "delete"

    def normalize(payload: Mapping[str, Any], parent: str | None) -> dict[str, Any]:
        return normalize_record(
            event.record_type,
            payload,
            parent_external_id=parent,
            status_mapping=system.status_mapping,
            phone_region=phone_region,
        )

    if deleting and record is not None:
        # A delete only identifies the record: its version keeps the last known state.
        payload, normalized = record.payload, record.normalized
        parent = record.parent_external_id
    else:
        parent = event.parent_external_id
        payload = event.payload
        normalized = normalize({} if deleting else event.payload, parent)
    digest = record_hash(normalized)

    def result(outcome: Outcome, version: int | None, changed: list[str]) -> RecordChanged:
        assert record is not None
        return RecordChanged(
            record_id=record.id,
            source_system_id=record.source_system_id,
            record_type=record.record_type,
            external_id=record.external_id,
            parent_external_id=record.parent_external_id,
            outcome=outcome,
            version=version,
            changed_fields=tuple(changed),
        )

    if record is None:
        record = SourceRecord(
            source_system_id=event.source_system_id,
            record_type=event.record_type,
            external_id=event.external_id,
            parent_external_id=parent,
            payload=payload,
            normalized=normalized,
            record_hash=digest,
            version=1,
            source_created_at=_created_at(event.record_type, normalized),
            source_updated_at=event.source_updated_at,
            is_deleted=deleting,
        )
        session.add(record)
        await session.flush()
        changed = changed_fields(None, normalized) + ([DELETED_FIELD] if deleting else [])
        session.add(
            _version(
                record,
                version=1,
                payload=payload,
                normalized=normalized,
                changed=changed,
                recorded_at=event.source_updated_at,
                is_deleted=deleting,
            )
        )
        await session.flush()
        return result("deleted" if deleting else "created", 1, changed)

    if event.source_updated_at < record.source_updated_at:
        if deleting:
            normalized = normalize({}, record.parent_external_id)  # until history says otherwise
        return await _out_of_order(session, record, event, payload, normalized, deleting, result)
    if event.source_updated_at == record.source_updated_at and not await _wins_tie(session, event):
        return result("superseded", None, [])

    if digest == record.record_hash and deleting == record.is_deleted:
        # Same state, newer recording: keep the latest raw payload and time, no version.
        record.payload = payload
        record.source_updated_at = event.source_updated_at
        await session.flush()
        return result("unchanged", None, [])

    changed = changed_fields(record.normalized, normalized)
    if deleting != record.is_deleted:
        changed = sorted([*changed, DELETED_FIELD])
    version = await _next_version(session, record.id)
    record.parent_external_id = parent
    record.payload = payload
    record.normalized = normalized
    record.record_hash = digest
    record.version = version
    record.source_created_at = _created_at(record.record_type, normalized)
    record.source_updated_at = event.source_updated_at
    record.is_deleted = deleting
    session.add(
        _version(
            record,
            version=version,
            payload=payload,
            normalized=normalized,
            changed=changed,
            recorded_at=event.source_updated_at,
            is_deleted=deleting,
        )
    )
    await session.flush()
    return result("deleted" if deleting else "updated", version, changed)


async def _keep_skipped_states(
    session: AsyncSession, record: SourceRecord, previous: RecordVersion, *, after: datetime
) -> None:
    """Version the state that skipped events confirmed, before a late event hides it (D-066).

    Events whose state was already current write no version (they only advance the record's
    recorded time). They held `previous`'s state. A late version at `after` would make the
    Time Machine show its state up to the next version instead, so the earliest such event
    between `after` and the next version gets the version it skipped.
    """
    next_version_at = await session.scalar(
        select(func.min(RecordVersion.source_updated_at)).where(
            RecordVersion.source_record_id == record.id,
            RecordVersion.source_updated_at > after,
        )
    )
    window = [
        IngestEvent.source_system_id == record.source_system_id,
        IngestEvent.record_type == record.record_type,
        IngestEvent.external_id == record.external_id,
        IngestEvent.status == "processed",
        IngestEvent.source_updated_at > after,
    ]
    if next_version_at is not None:
        window.append(IngestEvent.source_updated_at < next_version_at)
    confirmed_at = await session.scalar(
        select(func.min(IngestEvent.source_updated_at)).where(*window)
    )
    if confirmed_at is None:
        return
    session.add(
        _version(
            record,
            version=await _next_version(session, record.id),
            payload=previous.payload,
            normalized=previous.normalized,
            changed=[],
            recorded_at=confirmed_at,
            is_deleted=previous.is_deleted,
            out_of_order=next_version_at is not None,
        )
    )
    await session.flush()


async def _current_version(session: AsyncSession, record_id: uuid.UUID) -> int:
    """The version the Time Machine shows now: the latest (recorded time, version)."""
    version = await session.scalar(
        select(RecordVersion.version)
        .where(RecordVersion.source_record_id == record_id)
        .order_by(RecordVersion.source_updated_at.desc(), RecordVersion.version.desc())
        .limit(1)
    )
    assert version is not None
    return version


async def _out_of_order(
    session: AsyncSession,
    record: SourceRecord,
    event: IngestEvent,
    payload: dict[str, Any],
    normalized: dict[str, Any],
    deleting: bool,
    result: Callable[[Outcome, int | None, list[str]], RecordChanged],
) -> RecordChanged:
    """Record an older event in the history only; the current state stays (03 §M1).

    Like a newer event, it writes no version when it does not change the state at its time
    (the version before it already holds it). A late delete keeps the state the record had at
    that recorded time, or no fields at all when it predates the whole history.
    """
    if not await _wins_tie(session, event):
        return result("superseded", None, [])  # a later-received event holds that time
    previous = await session.scalar(
        select(RecordVersion)
        .where(
            RecordVersion.source_record_id == record.id,
            RecordVersion.source_updated_at <= event.source_updated_at,
        )
        .order_by(RecordVersion.source_updated_at.desc(), RecordVersion.version.desc())
        .limit(1)
    )
    if deleting and previous is not None:
        payload, normalized = previous.payload, previous.normalized
    if (
        previous is not None
        and previous.normalized == normalized
        and previous.is_deleted == deleting
    ):
        return result("unchanged", None, [])  # already the state at that time (or a replay)
    if previous is not None:
        await _keep_skipped_states(session, record, previous, after=event.source_updated_at)

    changed = changed_fields(previous.normalized if previous else None, normalized)
    if deleting != (previous.is_deleted if previous else False):
        changed = sorted([*changed, DELETED_FIELD])
    version = await _next_version(session, record.id)
    session.add(
        _version(
            record,
            version=version,
            payload=payload,
            normalized=normalized,
            changed=changed,
            recorded_at=event.source_updated_at,
            is_deleted=deleting,
            out_of_order=True,
        )
    )
    await session.flush()
    record.version = await _current_version(session, record.id)
    await session.flush()
    return result("out_of_order", version, changed)
