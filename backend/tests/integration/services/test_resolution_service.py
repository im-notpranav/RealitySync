"""Entity resolution (T-017, 03 §M3): founding and joining entities, review links, ambiguity,
rejections, children, re-evaluation, canonical fields, detection requests, concurrency and
replay. Commits for real (advisory locks work across connections); cleans up afterwards."""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import count
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.seed import default_source_systems
from app.models import (
    Entity,
    EntityLink,
    IngestEvent,
    RejectedPair,
    SourceRecord,
    SourceSystem,
    User,
)
from app.services import resolution_service
from app.services.record_service import RecordChanged, apply_event
from app.services.resolution_service import ResolutionResult

pytestmark = [pytest.mark.db, pytest.mark.asyncio]

Factory = async_sessionmaker[AsyncSession]
T0 = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
AUTO, REVIEW = 0.85, 0.60
_seq = count()


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
            for model in (RejectedPair, EntityLink, Entity, IngestEvent, SourceRecord):
                await session.execute(delete(model))
            await session.execute(delete(User).where(User.email.like("%@resolution.test")))
            await session.execute(delete(SourceSystem).where(SourceSystem.id.in_(created)))
            await session.commit()


async def ingest(
    factory: Factory,
    source: str,
    external_id: str,
    payload: dict[str, Any],
    *,
    record_type: str = "account",
    parent: str | None = None,
    event_type: str = "upsert",
) -> ResolutionResult | None:
    """One event through what the ingest loop does: apply, resolve, commit."""
    async with factory() as session:
        system_id = await session.scalar(select(SourceSystem.id).where(SourceSystem.key == source))
        event = IngestEvent(
            batch_id=uuid.uuid4(),
            source_system_id=system_id,
            record_type=record_type,
            external_id=external_id,
            parent_external_id=parent,
            event_type=event_type,
            payload=payload,
            source_updated_at=T0 + timedelta(minutes=next(_seq)),
            idempotency_key=uuid.uuid4().hex,
            status="processing",
            attempts=1,
            received_at=T0,
        )
        session.add(event)
        await session.flush()
        change = await apply_event(session, event, phone_region="IN")
        result = None
        if change.state_changed:
            result = await resolution_service.resolve(session, change, auto=AUTO, review=REVIEW)
        event.status = "processed"
        await session.commit()
        return result


def account(
    name: str, email: str | None = None, phone: str | None = None, **extra: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": name, "created_at": "2025-01-01T00:00:00Z", **extra}
    if email:
        payload["email"] = email
    if phone:
        payload["phone"] = phone
    return payload


SUBSCRIPTION = {"plan": "pro", "status": "active", "started_at": "2025-02-01T00:00:00Z"}
TICKET = {"subject": "Help", "status": "open", "opened_at": "2025-03-01T00:00:00Z"}


async def link_of(factory: Factory, external_id: str) -> EntityLink | None:
    async with factory() as session:
        link: EntityLink | None = await session.scalar(
            select(EntityLink)
            .join(SourceRecord, SourceRecord.id == EntityLink.source_record_id)
            .where(SourceRecord.external_id == external_id, EntityLink.status != "rejected")
        )
        return link


async def entity_of(factory: Factory, external_id: str) -> Entity:
    link = await link_of(factory, external_id)
    assert link is not None, f"{external_id} is not linked"
    async with factory() as session:
        entity = await session.get(Entity, link.entity_id)
        assert entity is not None
        return entity


async def entity_count(factory: Factory) -> int:
    async with factory() as session:
        return len(list(await session.scalars(select(Entity.id))))


async def clear_requests(factory: Factory) -> None:
    async with factory() as session:
        await session.execute(update(Entity).values(detection_requested_at=None))
        await session.commit()


async def requested(factory: Factory) -> set[uuid.UUID]:
    async with factory() as session:
        return set(
            await session.scalars(
                select(Entity.id).where(Entity.detection_requested_at.is_not(None))
            )
        )


# --------------------------------------------------------------------------- found and join


async def test_the_first_account_founds_an_entity(factory: Factory) -> None:
    result = await ingest(factory, "crm", "C-1", account("Jon  Smith", "Jon.Smith@Example.com"))

    entity = await entity_of(factory, "C-1")
    link = await link_of(factory, "C-1")
    assert link is not None and result is not None
    assert (entity.canonical_name, entity.canonical_email) == ("Jon Smith", "jon.smith@example.com")
    assert (link.status, link.match_method, link.match_confidence) == (
        "auto_matched",
        "blocking_score",
        Decimal("1.000"),
    )
    assert result.touched_entities == {entity.id}
    assert entity.detection_requested_at is not None


async def test_a_matching_account_joins_the_entity(factory: Factory) -> None:
    await ingest(
        factory, "crm", "C-1", account("Jon Smith", "jon.smith@example.com", "098765 43210")
    )

    result = await ingest(
        factory,
        "billing",
        "B-1",
        account("Jonathan Smith", "jon.smith@example.com", "+919876543210"),
    )

    crm, billing = await entity_of(factory, "C-1"), await entity_of(factory, "B-1")
    link = await link_of(factory, "B-1")
    assert link is not None and result is not None
    assert crm.id == billing.id
    assert (link.status, link.match_method) == ("auto_matched", "blocking_score")
    assert link.match_confidence == Decimal("1.000")
    assert link.match_features["email_exact"] == 1.0
    assert result.review_links == []
    assert await entity_count(factory) == 1


async def test_unrelated_accounts_found_separate_entities(factory: Factory) -> None:
    await ingest(factory, "crm", "C-1", account("Jon Smith", "jon@a.com"))
    await ingest(factory, "billing", "B-1", account("Priya Patel", "priya@b.com"))

    assert (await entity_of(factory, "C-1")).id != (await entity_of(factory, "B-1")).id


async def test_an_uncertain_match_needs_review(factory: Factory) -> None:
    await ingest(factory, "crm", "C-1", account("Rekha Iyer", phone="98400 33333"))

    result = await ingest(factory, "billing", "B-1", account("Mohan Iyer", phone="98400 33333"))

    link = await link_of(factory, "B-1")
    assert link is not None and result is not None
    assert link.status == "needs_review"
    assert Decimal("0.6") <= link.match_confidence < Decimal("0.85")
    assert result.review_links == [link.id]
    assert (await entity_of(factory, "B-1")).id == (await entity_of(factory, "C-1")).id


async def test_an_equal_external_ref_links_despite_other_emails(factory: Factory) -> None:
    await ingest(factory, "crm", "C-1042", account("Ravi Kumar", "ravi@old.com"))

    await ingest(
        factory,
        "billing",
        "B-1",
        account("Ravi Kumar", "ravi@new.com", external_refs={"crm_id": "C-1042"}),
    )

    link = await link_of(factory, "B-1")
    assert link is not None
    assert (link.status, link.match_method, link.match_confidence) == (
        "auto_matched",
        "external_ref",
        Decimal("1.000"),
    )


async def test_a_same_system_duplicate_joins_as_an_extra(factory: Factory) -> None:
    await ingest(factory, "crm", "C-1", account("Pooja Reddy", "pooja@reddy.in"))
    await ingest(factory, "crm", "C-2", account("Pooja Reddy", "pooja@reddy.in"))

    assert (await entity_of(factory, "C-1")).id == (await entity_of(factory, "C-2")).id


async def test_strong_matches_in_two_entities_need_review(factory: Factory) -> None:
    # Two entities that do not match each other (only a name in common: thin evidence).
    await ingest(factory, "crm", "C-1", account("Jon Smith", "jon@a.com"))
    await ingest(factory, "support", "S-1", account("Jon Smith", phone="98765 43210"))
    assert await entity_count(factory) == 2

    result = await ingest(
        factory, "billing", "B-1", account("Jon Smith", "jon@a.com", "98765 43210")
    )

    link = await link_of(factory, "B-1")
    assert link is not None and result is not None
    assert link.status == "needs_review"  # a possible merge: never automatic
    assert result.review_links == [link.id]
    assert await entity_count(factory) == 2


async def test_canonical_fields_come_from_the_highest_authority(factory: Factory) -> None:
    await ingest(
        factory, "billing", "B-1", account("J. Smith", "jon.smith@example.com", "98765 43210")
    )
    await ingest(
        factory, "crm", "C-1", account("Jonathan Smith", "Jon.Smith@example.com", "98765 43210")
    )

    entity = await entity_of(factory, "B-1")
    assert entity.canonical_name == "Jonathan Smith"  # CRM name authority 0.9 > Billing 0.6


# ----------------------------------------------------------------------------- rejections


async def make_user(factory: Factory) -> uuid.UUID:
    async with factory() as session:
        user = User(
            email=f"{uuid.uuid4().hex[:8]}@resolution.test",
            password_hash="x",
            full_name="Analyst",
            role="analyst",
        )
        session.add(user)
        await session.commit()
        return user.id


async def record_id(factory: Factory, external_id: str) -> uuid.UUID:
    async with factory() as session:
        found = await session.scalar(
            select(SourceRecord.id).where(SourceRecord.external_id == external_id)
        )
        assert found is not None
        return found


async def test_rejected_pairs_are_never_linked(factory: Factory) -> None:
    await ingest(factory, "crm", "C-1", account("Pooja Reddy", "pooja@reddy.in"))
    await ingest(factory, "billing", "B-1", account("Somebody", "other@x.in"))
    a, b = sorted([await record_id(factory, "C-1"), await record_id(factory, "B-1")])
    async with factory() as session:
        session.add(
            RejectedPair(record_a_id=a, record_b_id=b, rejected_by=await make_user(factory))
        )
        await session.commit()

    # B-1 now looks exactly like C-1, but the pair was rejected.
    await ingest(factory, "billing", "B-1", account("Pooja Reddy", "pooja@reddy.in"))

    assert (await entity_of(factory, "B-1")).id != (await entity_of(factory, "C-1")).id


async def test_a_rejected_link_is_not_proposed_again(factory: Factory) -> None:
    await ingest(factory, "crm", "C-1", account("Pooja Reddy", "pooja@reddy.in"))
    await ingest(factory, "billing", "B-1", account("Pooja Reddy", "pooja@reddy.in"))
    entity = await entity_of(factory, "C-1")
    async with factory() as session:  # what the review endpoint (T-018) does
        await session.execute(
            update(EntityLink)
            .where(EntityLink.source_record_id == await record_id(factory, "B-1"))
            .values(status="rejected")
        )
        await session.commit()

    await ingest(factory, "billing", "B-1", account("Pooja Reddy", "pooja@reddy.in", "98490 12121"))

    assert (await entity_of(factory, "B-1")).id != entity.id


# ------------------------------------------------------------------------------- children


async def test_children_follow_their_parent(factory: Factory) -> None:
    await ingest(factory, "billing", "B-1", account("Jon Smith", "jon@a.com"))

    await ingest(
        factory, "billing", "SUB-1", SUBSCRIPTION, record_type="subscription", parent="B-1"
    )

    link = await link_of(factory, "SUB-1")
    assert link is not None
    assert (link.match_method, link.status, link.match_confidence) == (
        "parent",
        "auto_matched",
        Decimal("1.000"),
    )
    assert link.entity_id == (await entity_of(factory, "B-1")).id


async def test_waiting_children_attach_when_their_parent_links(factory: Factory) -> None:
    result = await ingest(factory, "support", "T-1", TICKET, record_type="ticket", parent="S-1")
    assert result is not None and result.touched_entities == set()
    assert await link_of(factory, "T-1") is None  # waits: no entity, no findings

    await ingest(factory, "support", "S-1", account("Jon Smith", "jon@a.com"))

    assert (await link_of(factory, "T-1")) is not None
    assert (await entity_of(factory, "T-1")).id == (await entity_of(factory, "S-1")).id


async def test_children_only_attach_to_a_parent_in_their_own_system(factory: Factory) -> None:
    await ingest(factory, "crm", "X-1", account("Jon Smith", "jon@a.com"))

    await ingest(
        factory, "billing", "SUB-1", SUBSCRIPTION, record_type="subscription", parent="X-1"
    )

    assert await link_of(factory, "SUB-1") is None


async def test_a_child_moves_when_its_parent_changes(factory: Factory) -> None:
    await ingest(factory, "billing", "B-1", account("Jon Smith", "jon@a.com"))
    await ingest(factory, "billing", "B-2", account("Priya Patel", "priya@b.com"))
    await ingest(
        factory, "billing", "SUB-1", SUBSCRIPTION, record_type="subscription", parent="B-1"
    )
    first = await entity_of(factory, "B-1")
    await clear_requests(factory)

    await ingest(
        factory, "billing", "SUB-1", SUBSCRIPTION, record_type="subscription", parent="B-2"
    )

    second = await entity_of(factory, "B-2")
    assert (await entity_of(factory, "SUB-1")).id == second.id
    assert await requested(factory) == {first.id, second.id}

    await ingest(
        factory, "billing", "SUB-1", SUBSCRIPTION, record_type="subscription", parent="B-404"
    )
    assert await link_of(factory, "SUB-1") is None  # unknown parent: waits again


# --------------------------------------------------------------------------- re-evaluation


async def test_an_identity_change_that_breaks_the_match_needs_review(factory: Factory) -> None:
    await ingest(factory, "crm", "C-1", account("Pooja Reddy", "pooja@reddy.in"))
    await ingest(factory, "billing", "B-1", account("Pooja Reddy", "pooja@reddy.in"))

    result = await ingest(factory, "billing", "B-1", account("Pooja Reddy", "p.reddy@elsewhere.in"))

    link = await link_of(factory, "B-1")
    assert link is not None and result is not None
    assert link.status == "needs_review"  # stays in its entity, flagged (03 §M3 step 6)
    assert link.match_confidence < Decimal("0.6")
    assert result.review_links == [link.id]
    assert (await entity_of(factory, "B-1")).id == (await entity_of(factory, "C-1")).id


async def test_a_confirmed_link_survives_identity_changes(factory: Factory) -> None:
    await ingest(factory, "crm", "C-1", account("Pooja Reddy", "pooja@reddy.in"))
    await ingest(factory, "billing", "B-1", account("Pooja Reddy", "pooja@reddy.in"))
    async with factory() as session:
        await session.execute(
            update(EntityLink)
            .where(EntityLink.source_record_id == await record_id(factory, "B-1"))
            .values(status="confirmed")
        )
        await session.commit()

    await ingest(factory, "billing", "B-1", account("Somebody Else", "else@where.in"))

    link = await link_of(factory, "B-1")
    assert link is not None and link.status == "confirmed"


async def test_other_changes_only_request_detection(factory: Factory) -> None:
    await ingest(factory, "crm", "C-1", account("Pooja Reddy", "pooja@reddy.in"))
    await ingest(factory, "billing", "B-1", account("Pooja Reddy", "pooja@reddy.in"))
    before = await link_of(factory, "B-1")
    await clear_requests(factory)

    result = await ingest(
        factory, "billing", "B-1", account("Pooja Reddy", "pooja@reddy.in", plan="pro")
    )

    after = await link_of(factory, "B-1")
    assert before is not None and after is not None and result is not None
    assert (after.id, after.updated_at) == (before.id, before.updated_at)
    assert await requested(factory) == {after.entity_id}


async def test_an_account_alone_in_its_entity_moves_to_a_better_one(factory: Factory) -> None:
    await ingest(factory, "crm", "C-1", account("Jon Smith", "jon.smith@example.com"))
    await ingest(factory, "billing", "B-1", account("Jon Smith", "typo@exampel.com"))
    await ingest(
        factory, "billing", "SUB-1", SUBSCRIPTION, record_type="subscription", parent="B-1"
    )
    old = await entity_of(factory, "B-1")
    target = await entity_of(factory, "C-1")
    assert old.id != target.id
    await clear_requests(factory)

    await ingest(factory, "billing", "B-1", account("Jon Smith", "jon.smith@example.com"))

    assert (await entity_of(factory, "B-1")).id == target.id
    assert (await entity_of(factory, "SUB-1")).id == target.id  # children move along
    assert await requested(factory) == {old.id, target.id}


async def test_a_deleted_account_is_no_candidate(factory: Factory) -> None:
    await ingest(factory, "crm", "C-1", account("Pooja Reddy", "pooja@reddy.in"))
    entity = await entity_of(factory, "C-1")
    await clear_requests(factory)

    await ingest(factory, "crm", "C-1", {}, event_type="delete")
    assert await requested(factory) == {entity.id}

    await ingest(factory, "billing", "B-1", account("Pooja Reddy", "pooja@reddy.in"))
    assert (await entity_of(factory, "B-1")).id != entity.id


# ------------------------------------------------------------------- concurrency and replay


async def test_concurrent_accounts_of_one_new_customer_found_one_entity(factory: Factory) -> None:
    """Without the blocking-key locks both would see no candidate and found two entities."""
    people = [(f"Person{i} Example", f"person{i}@example.com") for i in range(8)]

    await asyncio.gather(
        *(
            ingest(factory, system, f"{system}-{i}", account(name, email))
            for i, (name, email) in enumerate(people)
            for system in ("crm", "billing", "support")
        )
    )

    assert await entity_count(factory) == len(people)
    for i in range(len(people)):
        ids = {(await entity_of(factory, f"{s}-{i}")).id for s in ("crm", "billing", "support")}
        assert len(ids) == 1


async def snapshot(factory: Factory) -> list[tuple[Any, ...]]:
    async with factory() as session:
        rows = await session.execute(
            select(SourceRecord.external_id, EntityLink, Entity)
            .join(EntityLink, EntityLink.source_record_id == SourceRecord.id)
            .join(Entity, Entity.id == EntityLink.entity_id)
            .order_by(SourceRecord.external_id)
        )
        return [
            (
                ext,
                str(link.entity_id),
                link.status,
                link.match_method,
                link.match_confidence,
                link.match_features,
                entity.canonical_name,
                entity.canonical_email,
            )
            for ext, link, entity in rows
        ]


async def build_world(factory: Factory) -> None:
    await ingest(factory, "crm", "C-1", account("Jon Smith", "jon@a.com", "98765 43210"))
    await ingest(factory, "billing", "B-1", account("Jon Smith", "jon@a.com"))
    await ingest(factory, "support", "S-1", account("Rekha Iyer", phone="98400 33333"))
    await ingest(factory, "support", "S-2", account("Mohan Iyer", phone="98400 33333"))
    await ingest(
        factory, "billing", "SUB-1", SUBSCRIPTION, record_type="subscription", parent="B-1"
    )


async def test_replaying_the_events_changes_nothing(factory: Factory) -> None:
    await build_world(factory)
    before = await snapshot(factory)

    await build_world(factory)  # the same states again: no new version, no resolution

    assert await snapshot(factory) == before


async def resolve_everything(factory: Factory) -> None:
    """Re-run resolution for every record as if all its identity fields had changed."""
    async with factory() as session:
        records = list(
            await session.scalars(select(SourceRecord).order_by(SourceRecord.external_id))
        )
    for record in records:
        async with factory() as session:
            change = RecordChanged(
                record_id=record.id,
                source_system_id=record.source_system_id,
                record_type=record.record_type,
                external_id=record.external_id,
                parent_external_id=record.parent_external_id,
                outcome="updated",
                version=record.version,
                changed_fields=tuple(record.normalized),
            )
            await resolution_service.resolve(session, change, auto=AUTO, review=REVIEW)
            await session.commit()


async def test_resolution_reaches_a_fixed_point(factory: Factory) -> None:
    """Re-resolving re-scores founders against their peers once; after that it is stable."""
    await build_world(factory)
    await resolve_everything(factory)
    once = await snapshot(factory)

    await resolve_everything(factory)

    assert await snapshot(factory) == once
    assert await entity_count(factory) == 2  # Iyers share one entity via a review link
