"""Record upsert and versioning (T-012, 03 §M1): new / newer / older / equal-time / delete,
replay idempotency (invariant 1) and concurrent events for one record.

Tests commit for real: the per-record advisory lock only matters across connections, and the
equal-time tie-break reads events other transactions processed. Created rows are deleted.
"""

import asyncio
import random
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.seed import default_source_systems
from app.models import IngestEvent, RecordVersion, SourceRecord, SourceSystem
from app.services.record_service import DELETED_FIELD, RecordChanged, apply_event

pytestmark = [pytest.mark.db, pytest.mark.asyncio]

Factory = async_sessionmaker[AsyncSession]
T0 = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
RECEIVED = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)
_seq = count()


def at(hours: float) -> datetime:
    return T0 + timedelta(hours=hours)


def account(**payload: Any) -> dict[str, Any]:
    return {
        "name": "Jon Smith",
        "created_at": "2025-11-02T10:00:00Z",
        "status": "Customer",
        **payload,
    }


@pytest_asyncio.fixture
async def factory(db_engine: AsyncEngine) -> AsyncGenerator[Factory, None]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        created = list(
            await session.scalars(
                insert(SourceSystem)
                .values(default_source_systems())
                .on_conflict_do_nothing(index_elements=["key"])
                .returning(SourceSystem.id)
            )
        )
        await session.commit()
    try:
        yield factory
    finally:
        async with factory() as session:
            await session.execute(delete(IngestEvent))
            await session.execute(delete(SourceRecord))
            await session.execute(delete(SourceSystem).where(SourceSystem.id.in_(created)))
            await session.commit()


async def system_id(factory: Factory, key: str = "crm") -> uuid.UUID:
    async with factory() as session:
        found = await session.scalar(select(SourceSystem.id).where(SourceSystem.key == key))
        assert found is not None
        return found


async def new_event(
    factory: Factory,
    recorded: datetime,
    payload: dict[str, Any] | None = None,
    *,
    event_type: str = "upsert",
    external_id: str = "C-1042",
    record_type: str = "account",
    parent: str | None = None,
    received: datetime | None = None,
    source: str = "crm",
) -> IngestEvent:
    """A committed ingest event in `processing`, as the worker hands it to the pipeline."""
    async with factory() as session:
        event = IngestEvent(
            batch_id=uuid.uuid4(),
            source_system_id=await session.scalar(
                select(SourceSystem.id).where(SourceSystem.key == source)
            ),
            record_type=record_type,
            external_id=external_id,
            parent_external_id=parent,
            event_type=event_type,
            payload=account() if payload is None else payload,
            source_updated_at=recorded,
            idempotency_key=uuid.uuid4().hex,
            status="processing",
            attempts=1,
            received_at=received or RECEIVED + timedelta(seconds=next(_seq)),
        )
        session.add(event)
        await session.commit()
        return event


async def apply(factory: Factory, event: IngestEvent) -> RecordChanged:
    """What the ingest loop does: apply and mark processed in one transaction."""
    async with factory() as session:
        row = await session.get(IngestEvent, event.id)
        assert row is not None
        change = await apply_event(session, row, phone_region="IN")
        row.status = "processed"
        await session.commit()
        return change


async def send(
    factory: Factory, recorded: datetime, payload: Any = None, **kw: Any
) -> RecordChanged:
    return await apply(factory, await new_event(factory, recorded, payload, **kw))


async def current(factory: Factory, external_id: str = "C-1042") -> SourceRecord:
    async with factory() as session:
        record = await session.scalar(
            select(SourceRecord).where(SourceRecord.external_id == external_id)
        )
        assert record is not None
        return record


async def versions(factory: Factory, external_id: str = "C-1042") -> list[RecordVersion]:
    async with factory() as session:
        return list(
            await session.scalars(
                select(RecordVersion)
                .join(SourceRecord, SourceRecord.id == RecordVersion.source_record_id)
                .where(SourceRecord.external_id == external_id)
                .order_by(RecordVersion.version)
            )
        )


# ------------------------------------------------------------------------------------- new


async def test_a_new_record_gets_version_1(factory: Factory) -> None:
    change = await send(factory, at(0), account(email="Jon@Example.com", parent_note="x"))

    record = await current(factory)
    (v1,) = await versions(factory)
    assert (change.outcome, change.version, change.state_changed) == ("created", 1, True)
    assert change.record_id == record.id
    assert (record.version, record.source_updated_at, record.is_deleted) == (1, at(0), False)
    assert record.normalized["email_canonical"] == "jon@example.com"
    assert record.normalized["status"] == "active"
    assert record.payload["parent_note"] == "x"  # unknown keys kept raw
    assert record.source_created_at == datetime(2025, 11, 2, 10, 0, tzinfo=UTC)
    assert (v1.version, v1.source_updated_at, v1.out_of_order, v1.is_deleted) == (
        1,
        at(0),
        False,
        False,
    )
    assert v1.source_system_id == record.source_system_id == await system_id(factory)
    assert v1.normalized == record.normalized
    assert v1.changed_fields == list(change.changed_fields)
    assert {"name", "email", "status", "created_at"} <= set(v1.changed_fields)


async def test_children_keep_their_parent(factory: Factory) -> None:
    change = await send(
        factory,
        at(0),
        {"plan": "Pro", "status": "active", "started_at": "2025-11-02T10:00:00Z"},
        record_type="subscription",
        external_id="SUB-1",
        parent="B-1",
        source="billing",
    )

    record = await current(factory, "SUB-1")
    assert change.parent_external_id == record.parent_external_id == "B-1"
    assert record.normalized["parent_external_id"] == "B-1"
    assert record.source_created_at == datetime(2025, 11, 2, 10, 0, tzinfo=UTC)


async def test_records_are_kept_apart_by_system_type_and_id(factory: Factory) -> None:
    await send(factory, at(0))
    await send(factory, at(0), external_id="C-2")
    await send(factory, at(0), source="billing")

    async with factory() as session:
        assert len(list(await session.scalars(select(SourceRecord)))) == 3


# ----------------------------------------------------------------------------------- newer


async def test_a_newer_event_makes_a_new_version(factory: Factory) -> None:
    await send(factory, at(0))

    change = await send(factory, at(1), account(status="former customer", plan="Pro"))

    record = await current(factory)
    v1, v2 = await versions(factory)
    assert (change.outcome, change.version, change.changed_fields) == (
        "updated",
        2,
        ("plan", "status"),
    )
    assert (record.version, record.source_updated_at) == (2, at(1))
    assert record.normalized["status"] == "churned"
    assert (v2.version, v2.changed_fields, v2.out_of_order) == (2, ["plan", "status"], False)
    assert v1.normalized["status"] == "active"  # history kept


async def test_an_unchanged_state_writes_no_version(factory: Factory) -> None:
    await send(factory, at(0), account(email="jon@example.com"))

    change = await send(factory, at(1), account(email="  JON@Example.COM "))

    record = await current(factory)
    assert (change.outcome, change.version, change.state_changed) == ("unchanged", None, False)
    assert len(await versions(factory)) == 1
    assert record.version == 1
    # The latest raw payload and recorded time still move forward.
    assert (record.payload["email"], record.source_updated_at) == ("  JON@Example.COM ", at(1))


# ----------------------------------------------------------------------------------- older


async def test_an_older_event_only_goes_into_the_history(factory: Factory) -> None:
    await send(factory, at(0), account(plan="starter"))
    await send(factory, at(2), account(plan="enterprise"))

    change = await send(factory, at(1), account(plan="pro"))

    record = await current(factory)
    *_, late = await versions(factory)
    assert (change.outcome, change.state_changed) == ("out_of_order", False)
    assert (record.version, record.normalized["plan"]) == (2, "enterprise")
    assert (late.version, late.out_of_order, late.source_updated_at) == (3, True, at(1))
    assert late.changed_fields == ["plan"]  # against the version recorded before it (t0)


async def test_an_event_older_than_all_history(factory: Factory) -> None:
    await send(factory, at(5))

    change = await send(factory, at(1), account(plan="pro"))

    assert change.outcome == "out_of_order"
    assert {"name", "plan", "status"} <= set(change.changed_fields)


async def test_an_older_replay_is_not_recorded_twice(factory: Factory) -> None:
    await send(factory, at(0))
    await send(factory, at(2), account(plan="pro"))

    assert (await send(factory, at(0))).outcome == "unchanged"  # already v1
    assert (await send(factory, at(1), account(plan="starter"))).outcome == "out_of_order"
    assert (await send(factory, at(1), account(plan="starter"))).outcome == "unchanged"
    assert len(await versions(factory)) == 3


async def test_a_late_event_before_a_skipped_confirmation(factory: Factory) -> None:
    """t1 starter, t3 starter (same state: no version), t5 pro; then a late t2 enterprise.
    At t3 the record was starter again, so the history needs that version now."""
    await send(factory, at(1), account(plan="starter"))
    await send(factory, at(3), account(plan="starter"))
    await send(factory, at(5), account(plan="pro"))

    await send(factory, at(2), account(plan="enterprise"))

    history = sorted(await versions(factory), key=lambda v: (v.source_updated_at, v.version))
    assert [(v.source_updated_at, v.normalized["plan"]) for v in history] == [
        (at(1), "starter"),
        (at(2), "enterprise"),
        (at(3), "starter"),
        (at(5), "pro"),
    ]
    assert (await current(factory)).version == 2  # still the t5 version


async def test_a_late_event_after_an_unchanged_resend(factory: Factory) -> None:
    """The resend at t5 wrote no version; the late t4 event must not become the newest one."""
    await send(factory, at(2), account(plan="enterprise"))
    await send(factory, at(5), account(plan="enterprise"))  # unchanged: no version

    change = await send(factory, at(4), account(plan="starter"))

    record = await current(factory)
    history = await versions(factory)
    assert change.outcome == "out_of_order"
    assert [(v.source_updated_at, v.normalized["plan"], v.out_of_order) for v in history] == [
        (at(2), "enterprise", False),
        (at(5), "enterprise", False),  # the confirmed state, written when it became needed
        (at(4), "starter", True),
    ]
    assert (record.version, record.normalized["plan"]) == (2, "enterprise")
    winning = max(history, key=lambda v: (v.source_updated_at, v.version))
    assert winning.normalized == record.normalized


# ------------------------------------------------------------------------------ equal times


async def test_at_an_equal_time_the_later_received_event_wins(factory: Factory) -> None:
    first = await new_event(factory, at(1), account(plan="starter"), received=RECEIVED)
    second = await new_event(
        factory, at(1), account(plan="pro"), received=RECEIVED + timedelta(seconds=1)
    )
    await send(factory, at(0))

    # Processed in the "wrong" order: the later-received event first.
    assert (await apply(factory, second)).outcome == "updated"
    loser = await apply(factory, first)

    assert (loser.outcome, loser.version) == ("superseded", None)
    assert (await current(factory)).normalized["plan"] == "pro"
    assert len(await versions(factory)) == 2  # the loser is not in the history


async def test_at_an_equal_time_processed_in_order(factory: Factory) -> None:
    first = await new_event(factory, at(1), account(plan="starter"), received=RECEIVED)
    second = await new_event(
        factory, at(1), account(plan="pro"), received=RECEIVED + timedelta(seconds=1)
    )

    await apply(factory, first)
    assert (await apply(factory, second)).outcome == "updated"
    assert (await current(factory)).normalized["plan"] == "pro"


async def test_an_equal_receive_time_falls_back_to_the_event_id(factory: Factory) -> None:
    a = await new_event(factory, at(1), account(plan="starter"), received=RECEIVED)
    b = await new_event(factory, at(1), account(plan="pro"), received=RECEIVED)
    low, high = sorted([a, b], key=lambda e: e.id)

    await apply(factory, high)
    assert (await apply(factory, low)).outcome == "superseded"
    assert (await current(factory)).normalized["plan"] == high.payload["plan"]


# ---------------------------------------------------------------------------------- delete


async def test_a_delete_soft_deletes_and_keeps_the_last_state(factory: Factory) -> None:
    await send(factory, at(0), account(plan="pro"))

    change = await send(factory, at(1), {}, event_type="delete")

    record = await current(factory)
    _, v2 = await versions(factory)
    assert (change.outcome, change.changed_fields, change.state_changed) == (
        "deleted",
        (DELETED_FIELD,),
        True,
    )
    assert (record.is_deleted, record.version, record.normalized["plan"]) == (True, 2, "pro")
    assert (v2.is_deleted, v2.normalized["plan"], v2.source_updated_at) == (True, "pro", at(1))


async def test_deleting_twice_changes_nothing(factory: Factory) -> None:
    await send(factory, at(0))
    await send(factory, at(1), {}, event_type="delete")

    assert (await send(factory, at(2), {}, event_type="delete")).outcome == "unchanged"
    assert len(await versions(factory)) == 2


async def test_a_newer_upsert_restores_a_deleted_record(factory: Factory) -> None:
    await send(factory, at(0))
    await send(factory, at(1), {}, event_type="delete")

    change = await send(factory, at(2))

    assert (change.outcome, change.changed_fields) == ("updated", (DELETED_FIELD,))
    assert (await current(factory)).is_deleted is False


async def test_a_delete_for_an_unknown_record_leaves_a_tombstone(factory: Factory) -> None:
    change = await send(factory, at(5), {}, event_type="delete")

    record = await current(factory)
    assert (change.outcome, record.is_deleted, record.version) == ("deleted", True, 1)
    assert record.normalized["name"] is None

    late = await send(factory, at(1))  # an older upsert cannot bring it back

    assert late.outcome == "out_of_order"
    assert (await current(factory)).is_deleted is True


async def test_a_late_delete_keeps_the_state_of_its_time(factory: Factory) -> None:
    await send(factory, at(0), account(plan="starter"))
    await send(factory, at(5), account(plan="enterprise"))

    change = await send(factory, at(2), {}, event_type="delete")

    *_, late = await versions(factory)
    assert change.outcome == "out_of_order"
    assert (late.is_deleted, late.out_of_order, late.normalized["plan"]) == (True, True, "starter")
    assert late.changed_fields == [DELETED_FIELD]
    assert (await current(factory)).is_deleted is False


# ------------------------------------------------------------------- replay and concurrency


async def snapshot(factory: Factory) -> list[tuple[Any, ...]]:
    async with factory() as session:
        records = [
            (
                r.external_id,
                r.payload,
                r.normalized,
                r.record_hash,
                r.version,
                r.source_updated_at,
                r.is_deleted,
                r.parent_external_id,
                r.source_created_at,
            )
            for r in await session.scalars(select(SourceRecord).order_by(SourceRecord.external_id))
        ]
        history = [
            (
                r.external_id,
                v.version,
                v.payload,
                v.normalized,
                v.changed_fields,
                v.source_updated_at,
                v.is_deleted,
                v.out_of_order,
            )
            for v, r in (
                await session.execute(
                    select(RecordVersion, SourceRecord)
                    .join(SourceRecord, SourceRecord.id == RecordVersion.source_record_id)
                    .order_by(SourceRecord.external_id, RecordVersion.version)
                )
            ).all()
        ]
        return [*records, *history]


async def test_replaying_every_event_twice_changes_nothing(factory: Factory) -> None:
    """Invariant 1: processing is at-least-once, so a second pass must be a no-op."""
    stream = [
        await new_event(factory, at(0), account(plan="starter")),
        await new_event(factory, at(3), account(plan="pro")),
        await new_event(factory, at(1), account(plan="enterprise")),  # late
        await new_event(factory, at(3), account(plan="starter")),  # equal time, received later
        await new_event(factory, at(6), account(plan="starter")),  # unchanged resend
        await new_event(factory, at(5), account(plan="pro")),  # late, after the resend
        await new_event(factory, at(2), {}, event_type="delete"),  # late delete
        await new_event(factory, at(4), {}, event_type="delete", external_id="C-9"),
        await new_event(factory, at(3), account(), external_id="C-9"),
    ]
    for event in stream:
        await apply(factory, event)
    first = await snapshot(factory)

    for event in stream:
        await apply(factory, event)

    assert await snapshot(factory) == first


@pytest.mark.parametrize("order", ["forward", "reverse"])
async def test_concurrent_events_end_in_the_same_state(factory: Factory, order: str) -> None:
    """Many events for one record, applied concurrently on separate connections."""
    events = [
        await new_event(factory, at(i), account(plan=plan))
        for i, plan in enumerate(["starter", "pro", "enterprise", "pro", "starter", "enterprise"])
    ]
    if order == "reverse":
        events.reverse()

    changes = await asyncio.gather(*(apply(factory, e) for e in events))

    record = await current(factory)
    assert sum(c.outcome == "created" for c in changes) == 1  # no duplicate creation
    assert (record.source_updated_at, record.normalized["plan"]) == (at(5), "enterprise")
    history = await versions(factory)
    assert [v.version for v in history] == list(range(1, len(history) + 1))
    winning = max(history, key=lambda v: (v.source_updated_at, v.version))
    assert winning.normalized == record.normalized  # the Time Machine sees the same state


def reference_state(events: list[IngestEvent], until: datetime) -> tuple[bool, str | None] | None:
    """The state at `until` straight from the rules: the event with the greatest
    (recorded time, received time, id) at or before it wins. `(is_deleted, plan)`; a deleted
    record counts as absent, so its fields are not compared."""
    state: tuple[bool, str | None] | None = None
    for e in sorted(events, key=lambda e: (e.source_updated_at, e.received_at, e.id)):
        if e.source_updated_at > until:
            break
        deleted = e.event_type == "delete"
        state = (deleted, None if deleted else e.payload["plan"])
    return state


def as_of(history: list[RecordVersion], until: datetime) -> tuple[bool, str | None] | None:
    visible = [v for v in history if v.source_updated_at <= until]
    if not visible:
        return None
    winner = max(visible, key=lambda v: (v.source_updated_at, v.version))
    return (winner.is_deleted, None if winner.is_deleted else winner.normalized["plan"])


@pytest.mark.parametrize("seed", range(12))
async def test_any_processing_order_gives_the_same_history(factory: Factory, seed: int) -> None:
    """Invariant 1 / Time Machine parity, on random streams with ties, late events, deletes
    and unchanged resends, applied in a shuffled order."""
    rng = random.Random(seed)
    external_id = f"P-{seed}"
    events = []
    for _ in range(9):
        recorded = at(rng.choice([0, 1, 2, 3, 4]))
        if rng.random() < 0.2:
            events.append(
                await new_event(factory, recorded, {}, event_type="delete", external_id=external_id)
            )
        else:
            plan = rng.choice(["starter", "pro"])
            events.append(
                await new_event(factory, recorded, account(plan=plan), external_id=external_id)
            )
    shuffled = events[:]
    rng.shuffle(shuffled)

    for event in shuffled:
        await apply(factory, event)

    history = await versions(factory, external_id)
    record = await current(factory, external_id)
    for hour in range(5):
        assert as_of(history, at(hour)) == reference_state(events, at(hour)), f"at t{hour}"
    final = reference_state(events, at(4))
    assert final is not None
    assert (record.is_deleted, None if record.is_deleted else record.normalized["plan"]) == final
    assert record.source_updated_at == max(e.source_updated_at for e in events)

    before = await snapshot(factory)
    rng.shuffle(shuffled)
    for event in shuffled:  # at-least-once delivery: everything again, in another order
        await apply(factory, event)
    assert await snapshot(factory) == before
