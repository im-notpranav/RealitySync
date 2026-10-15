"""Entity resolution (03 §M3, FR-ENT-001/004…008, FR-DET-004).

Runs in the ingest transaction after a record's state changed (`RecordChanged`):

- **Account**, not linked yet → candidates sharing a blocking key (any system, its own included)
  are scored; the record joins the best entity (`auto_matched` or `needs_review`) or founds a
  new one. Strong candidates in two different entities make the link `needs_review` (a
  possible merge); entities are never merged automatically.
- **Account** whose identity fields changed → its link is re-scored against the other accounts
  of its entity: `needs_review` when it drops below `MATCH_AUTO` (03 §M3 step 6). Confirmed links
  stay. An account alone in its entity may move to a better one (its children move with it).
- **Child** record (`subscription`, `invoice`, `ticket`) → follows its parent account in the same
  system (`match_method = parent`); without a linked parent it waits, and is attached when the
  parent links.

Every touched entity gets its canonical name/email from the highest-authority account and a
detection request (`entities.detection_requested_at`), in the same transaction.
"""

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, delete, exists, func, literal_column, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.matching import (
    AUTO_MATCHED,
    BLOCKING_FIELDS,
    NO_LINK,
    AccountIdentity,
    MatchScore,
    blocking_keys,
    decide,
    score_pair,
)
from app.models import Entity, EntityLink, RejectedPair, SourceRecord, SourceSystem
from app.services.record_service import DELETED_FIELD, RecordChanged

# Changes to these normalized fields re-run matching for an account (03 §M3 step 6).
IDENTITY_FIELDS = frozenset(
    {"name", "name_block", "email", "email_canonical", "phone_e164", DELETED_FIELD}
)
FOUNDER_CONFIDENCE = Decimal("1.000")


@dataclass
class ResolutionResult:
    """Entities whose detection was requested and the links that now need review (alerts)."""

    touched_entities: set[uuid.UUID] = field(default_factory=set)
    review_links: list[uuid.UUID] = field(default_factory=list)


@dataclass(frozen=True)
class _Candidate:
    record: SourceRecord
    link: EntityLink
    score: MatchScore


def _confidence(score: float) -> Decimal:
    return Decimal(str(round(score, 3)))


def _active() -> Any:
    return EntityLink.status != "rejected"


async def _systems(session: AsyncSession) -> dict[uuid.UUID, SourceSystem]:
    return {s.id: s for s in await session.scalars(select(SourceSystem))}


async def _active_link(session: AsyncSession, record_id: uuid.UUID) -> EntityLink | None:
    link: EntityLink | None = await session.scalar(
        select(EntityLink).where(EntityLink.source_record_id == record_id, _active())
    )
    return link


async def lock_blocking_keys(session: AsyncSession, normalized: dict[str, Any]) -> None:
    """Advisory locks on the record's blocking keys, sorted (02 §3.3, concurrency rule 2):
    two records of one new customer cannot both found an entity."""
    for key in blocking_keys(normalized):
        await session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key})


def _identity(record: SourceRecord, systems: dict[uuid.UUID, SourceSystem]) -> AccountIdentity:
    return AccountIdentity.from_normalized(
        systems[record.source_system_id].key, record.external_id, record.normalized
    )


async def _candidates(
    session: AsyncSession,
    record: SourceRecord,
    systems: dict[uuid.UUID, SourceSystem],
    auto: float,
    review: float,
) -> list[_Candidate]:
    """Linked, live accounts sharing a blocking key and worth a link, minus rejected pairs."""
    shared = [
        literal_column(f"source_records.normalized ->> '{name}'") == value
        for name in BLOCKING_FIELDS
        if isinstance(value := record.normalized.get(name), str) and value
    ]
    if not shared:
        return []
    rejected = exists().where(
        or_(
            and_(
                RejectedPair.record_a_id == record.id, RejectedPair.record_b_id == SourceRecord.id
            ),
            and_(
                RejectedPair.record_b_id == record.id, RejectedPair.record_a_id == SourceRecord.id
            ),
        )
    )
    rows = await session.execute(
        select(SourceRecord, EntityLink)
        .join(EntityLink, and_(EntityLink.source_record_id == SourceRecord.id, _active()))
        .where(
            SourceRecord.record_type == "account",
            SourceRecord.is_deleted.is_(False),
            SourceRecord.id != record.id,
            or_(*shared),
            ~rejected,
        )
    )
    me = _identity(record, systems)
    found = []
    for other, link in rows:
        score = score_pair(me, _identity(other, systems))
        if decide(score.score, auto=auto, review=review) != NO_LINK:
            found.append(_Candidate(other, link, score))
    return found


def _best_by_entity(
    candidates: Iterable[_Candidate], excluded: set[uuid.UUID]
) -> dict[uuid.UUID, _Candidate]:
    best: dict[uuid.UUID, _Candidate] = {}
    for candidate in candidates:
        entity_id = candidate.link.entity_id
        if entity_id in excluded:
            continue
        current = best.get(entity_id)
        if current is None or (candidate.score.score, str(candidate.record.id)) > (
            current.score.score,
            str(current.record.id),
        ):
            best[entity_id] = candidate
    return best


def _pick(best: dict[uuid.UUID, _Candidate]) -> _Candidate | None:
    """Highest score, then the lower entity id (deterministic)."""
    if not best:
        return None
    return min(best.values(), key=lambda c: (-c.score.score, str(c.link.entity_id)))


def _status(
    score: MatchScore,
    *,
    auto: float,
    review: float,
    rivals: Iterable[_Candidate],
    entity_id: uuid.UUID,
) -> str:
    """`auto_matched` only when the score is strong and no other entity is also strong."""
    if decide(score.score, auto=auto, review=review) != AUTO_MATCHED:
        return "needs_review"
    if any(c.link.entity_id != entity_id and c.score.score >= auto for c in rivals):
        return "needs_review"  # strong candidates in two entities: a possible merge
    return "auto_matched"


def _apply_score(link: EntityLink, score: MatchScore, status: str) -> None:
    link.match_confidence = _confidence(score.score)
    link.match_features = score.features
    link.match_method = "external_ref" if score.shortcut else "blocking_score"
    link.status = status


async def _rejected_entities(session: AsyncSession, record_id: uuid.UUID) -> set[uuid.UUID]:
    """Entities an analyst rejected this record from: never proposed again (FR-ENT-006)."""
    rows = await session.scalars(
        select(EntityLink.entity_id).where(
            EntityLink.source_record_id == record_id, EntityLink.status == "rejected"
        )
    )
    return set(rows)


async def _peers(
    session: AsyncSession, entity_id: uuid.UUID, record_id: uuid.UUID
) -> list[SourceRecord]:
    rows = await session.scalars(
        select(SourceRecord)
        .join(EntityLink, and_(EntityLink.source_record_id == SourceRecord.id, _active()))
        .where(
            EntityLink.entity_id == entity_id,
            SourceRecord.record_type == "account",
            SourceRecord.is_deleted.is_(False),
            SourceRecord.id != record_id,
        )
    )
    return list(rows)


async def _attach_children(
    session: AsyncSession, account: SourceRecord, entity_id: uuid.UUID, result: ResolutionResult
) -> None:
    """Attach the account's children (same system, `parent_external_id`) to its entity: the
    ones waiting for it, and the ones still on the entity it left."""
    rows = await session.execute(
        select(SourceRecord.id, EntityLink)
        .outerjoin(EntityLink, and_(EntityLink.source_record_id == SourceRecord.id, _active()))
        .where(
            SourceRecord.source_system_id == account.source_system_id,
            SourceRecord.record_type != "account",
            SourceRecord.parent_external_id == account.external_id,
        )
    )
    for child_id, link in rows:
        if link is None:
            session.add(_parent_link(entity_id, child_id))
        elif link.match_method == "parent" and link.entity_id != entity_id:
            result.touched_entities.add(link.entity_id)
            link.entity_id = entity_id


def _parent_link(entity_id: uuid.UUID, record_id: uuid.UUID) -> EntityLink:
    return EntityLink(
        entity_id=entity_id,
        source_record_id=record_id,
        match_confidence=FOUNDER_CONFIDENCE,
        match_method="parent",
        match_features={},
        status="auto_matched",
    )


def _display_name(record: SourceRecord) -> str | None:
    raw = record.payload.get("name")
    return " ".join(raw.split()) if isinstance(raw, str) and raw.strip() else None


async def _found_entity(
    session: AsyncSession, record: SourceRecord, result: ResolutionResult
) -> uuid.UUID:
    entity = Entity(
        canonical_name=_display_name(record) or record.external_id,
        canonical_email=record.normalized.get("email"),
    )
    session.add(entity)
    await session.flush()
    session.add(
        EntityLink(
            entity_id=entity.id,
            source_record_id=record.id,
            match_confidence=FOUNDER_CONFIDENCE,
            match_method="blocking_score",
            match_features={},
            status="auto_matched",
        )
    )
    result.touched_entities.add(entity.id)
    return entity.id


async def _join(
    session: AsyncSession,
    record: SourceRecord,
    target: _Candidate,
    status: str,
    result: ResolutionResult,
) -> EntityLink:
    link = EntityLink(entity_id=target.link.entity_id, source_record_id=record.id)
    _apply_score(link, target.score, status)
    session.add(link)
    await session.flush()
    if status == "needs_review":
        result.review_links.append(link.id)
    result.touched_entities.add(target.link.entity_id)
    return link


async def _resolve_account(
    session: AsyncSession, change: RecordChanged, auto: float, review: float
) -> ResolutionResult:
    result = ResolutionResult()
    record = await session.get(SourceRecord, change.record_id)
    assert record is not None
    link = await _active_link(session, record.id)
    identity_changed = bool(IDENTITY_FIELDS & set(change.changed_fields))

    if record.is_deleted or (
        link is not None and (link.status == "confirmed" or not identity_changed)
    ):
        if link is not None:
            result.touched_entities.add(link.entity_id)
        return result  # a deleted account is no candidate; a confirmed link stays

    await lock_blocking_keys(session, record.normalized)
    systems = await _systems(session)
    candidates = await _candidates(session, record, systems, auto, review)
    excluded = await _rejected_entities(session, record.id)

    if link is not None:
        peers = await _peers(session, link.entity_id, record.id)
        if peers:  # re-score in place; never split or merge entities automatically
            me = _identity(record, systems)
            score = max(
                (score_pair(me, _identity(peer, systems)) for peer in peers),
                key=lambda s: s.score,
            )
            was = link.status
            status = _status(
                score, auto=auto, review=review, rivals=candidates, entity_id=link.entity_id
            )
            _apply_score(link, score, status)
            if status == "needs_review" and was != "needs_review":
                result.review_links.append(link.id)
            result.touched_entities.add(link.entity_id)
            return result
        excluded.add(link.entity_id)  # alone in its entity: it may move to a better one

    best = _best_by_entity(candidates, excluded)
    target = _pick(best)
    if target is None:
        if link is not None:
            result.touched_entities.add(link.entity_id)
            return result
        entity_id = await _found_entity(session, record, result)
    else:
        status = _status(
            target.score,
            auto=auto,
            review=review,
            rivals=best.values(),
            entity_id=target.link.entity_id,
        )
        if link is None:
            await _join(session, record, target, status, result)
        else:
            result.touched_entities.add(link.entity_id)  # the entity it leaves
            link.entity_id = target.link.entity_id
            _apply_score(link, target.score, status)
            if status == "needs_review":
                result.review_links.append(link.id)
            result.touched_entities.add(target.link.entity_id)
        entity_id = target.link.entity_id
    await _attach_children(session, record, entity_id, result)
    return result


async def _resolve_child(session: AsyncSession, change: RecordChanged) -> ResolutionResult:
    result = ResolutionResult()
    link = await _active_link(session, change.record_id)
    parent_link = None
    if change.parent_external_id is not None:
        parent_link = await session.scalar(
            select(EntityLink)
            .join(SourceRecord, SourceRecord.id == EntityLink.source_record_id)
            .where(
                SourceRecord.source_system_id == change.source_system_id,
                SourceRecord.record_type == "account",
                SourceRecord.external_id == change.parent_external_id,
                _active(),
            )
        )
    if parent_link is None:
        if link is not None and link.match_method == "parent":
            result.touched_entities.add(link.entity_id)  # its parent changed to an unknown one
            await session.execute(delete(EntityLink).where(EntityLink.id == link.id))
        return result
    if link is None:
        session.add(_parent_link(parent_link.entity_id, change.record_id))
    elif link.match_method == "parent" and link.entity_id != parent_link.entity_id:
        result.touched_entities.add(link.entity_id)
        link.entity_id = parent_link.entity_id
    result.touched_entities.add(parent_link.entity_id)
    return result


def _authority(system: SourceSystem, field_name: str) -> float:
    value = system.field_authority.get(field_name, 0.0)
    return float(value) if isinstance(value, int | float) else 0.0


async def refresh_canonical(session: AsyncSession, entity_ids: Sequence[uuid.UUID]) -> None:
    """Canonical name and email from the live account with the highest field authority
    (`name`, `email`), ties broken by the primary-account order (03 §M3 step 4)."""
    if not entity_ids:
        return
    systems = await _systems(session)
    rows = await session.execute(
        select(EntityLink, SourceRecord)
        .join(SourceRecord, SourceRecord.id == EntityLink.source_record_id)
        .where(
            EntityLink.entity_id.in_(entity_ids),
            _active(),
            SourceRecord.record_type == "account",
            SourceRecord.is_deleted.is_(False),
        )
    )
    accounts: dict[uuid.UUID, list[tuple[EntityLink, SourceRecord]]] = {}
    for link, record in rows:
        accounts.setdefault(link.entity_id, []).append((link, record))

    def order(item: tuple[EntityLink, SourceRecord], field_name: str) -> tuple[Any, ...]:
        link, record = item
        created = record.source_created_at
        return (
            -_authority(systems[record.source_system_id], field_name),
            link.status != "confirmed",
            -link.match_confidence,
            created is None,
            created.timestamp() if created else 0.0,
            record.external_id,
            str(record.id),
        )

    for entity_id, items in accounts.items():
        names = [
            n for _, r in sorted(items, key=lambda i: order(i, "name")) if (n := _display_name(r))
        ]
        emails = [
            e
            for _, r in sorted(items, key=lambda i: order(i, "email"))
            if isinstance(e := r.normalized.get("email"), str) and e
        ]
        values: dict[str, Any] = {"canonical_email": emails[0] if emails else None}
        if names:
            values["canonical_name"] = names[0]
        await session.execute(update(Entity).where(Entity.id == entity_id).values(**values))


async def request_detection(session: AsyncSession, entity_ids: Iterable[uuid.UUID]) -> None:
    """Queue the entities for the detection loop (02 §3.3, D-013): it runs once their request
    is 500 ms old, so a burst of changes is detected once."""
    ids = sorted(set(entity_ids), key=str)
    if ids:
        await session.execute(
            update(Entity).where(Entity.id.in_(ids)).values(detection_requested_at=func.now())
        )


async def resolve(
    session: AsyncSession, change: RecordChanged, *, auto: float, review: float
) -> ResolutionResult:
    """Link the changed record (03 §M3), refresh canonical fields and request detection for
    every touched entity. Flushes; the caller commits."""
    if change.record_type == "account":
        result = await _resolve_account(session, change, auto, review)
    else:
        result = await _resolve_child(session, change)
    await session.flush()
    touched = sorted(result.touched_entities, key=str)
    await refresh_canonical(session, touched)
    await request_detection(session, touched)
    await session.flush()
    return result
