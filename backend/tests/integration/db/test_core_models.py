"""Core tables enforce the constraints 05 §2.3-2.23 specify (T-009)."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Entity,
    EntityLink,
    EntityRisk,
    Finding,
    IngestEvent,
    InjectedIssue,
    Investigation,
    InvestigationCheckpoint,
    RecordVersion,
    RejectedPair,
    Rule,
    SimulationGroundTruth,
    SimulationRun,
    SourceRecord,
    SourceSystem,
    User,
)

pytestmark = [pytest.mark.db, pytest.mark.asyncio]

NOW = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


async def add(session: AsyncSession, *rows: object) -> None:
    session.add_all(rows)
    await session.flush()


async def rejects(session: AsyncSession, constraint: str, *rows: object) -> None:
    """Adding `rows` fails on `constraint`; the savepoint keeps the test's session usable."""
    with pytest.raises(IntegrityError, match=constraint):
        async with session.begin_nested():
            await add(session, *rows)


async def make_system(session: AsyncSession, key: str = "crm") -> SourceSystem:
    # Reuse the row if the startup bootstrap already created it in this database.
    system = await session.scalar(select(SourceSystem).where(SourceSystem.key == key))
    if system is None:
        system = SourceSystem(key=key, name=key.upper())
        await add(session, system)
    return system


async def make_user(session: AsyncSession) -> User:
    user = User(
        email=f"user-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="argon2id$test",
        full_name="Test User",
        role="analyst",
    )
    await add(session, user)
    return user


def record(system: SourceSystem, external_id: str = "C-1", **extra: Any) -> SourceRecord:
    values: dict[str, Any] = {
        "source_system_id": system.id,
        "record_type": "account",
        "external_id": external_id,
        "payload": {"name": "Ana Lopez"},
        "normalized": {"name": "ana lopez", "email_canonical": "ana@example.com"},
        "record_hash": sha(external_id),
        "source_updated_at": NOW,
    }
    return SourceRecord(**(values | extra))


async def make_record(
    session: AsyncSession, system: SourceSystem, external_id: str = "C-1"
) -> SourceRecord:
    row = record(system, external_id)
    await add(session, row)
    return row


def version(row: SourceRecord, number: int) -> RecordVersion:
    return RecordVersion(
        source_record_id=row.id,
        source_system_id=row.source_system_id,
        version=number,
        payload={},
        normalized={},
        source_updated_at=NOW,
    )


async def make_entity(session: AsyncSession) -> Entity:
    entity = Entity(canonical_name="ana lopez")
    await add(session, entity)
    return entity


def link(entity: Entity, row: SourceRecord, status: str = "auto_matched") -> EntityLink:
    return EntityLink(
        entity_id=entity.id,
        source_record_id=row.id,
        match_confidence=Decimal("0.950"),
        match_method="blocking_score",
        status=status,
    )


async def count(session: AsyncSession, table: str, column: str, value: uuid.UUID) -> int:
    # Table and column names come from the test itself, never from input.
    query = text(f"SELECT count(*) FROM {table} WHERE {column} = :value")
    return await session.scalar(query, {"value": value}) or 0


# ------------------------------------------------------------------------- records


async def test_source_record_defaults_and_uniqueness(db_session: AsyncSession) -> None:
    crm = await make_system(db_session)
    first = await make_record(db_session, crm)
    await db_session.refresh(first)

    assert (first.version, first.is_deleted) == (1, False)
    assert first.ingested_at.tzinfo is not None
    await rejects(
        db_session,
        "uq_source_records_system_type_external_id",
        record(crm, record_hash=sha("again")),
    )


async def test_record_type_is_checked(db_session: AsyncSession) -> None:
    crm = await make_system(db_session)

    await rejects(db_session, "ck_source_records_record_type", record(crm, record_type="contact"))


async def test_record_versions_are_unique_per_record(db_session: AsyncSession) -> None:
    row = await make_record(db_session, await make_system(db_session))
    first = version(row, 1)
    await add(db_session, first)
    await db_session.refresh(first)

    assert (first.changed_fields, first.is_deleted, first.out_of_order) == ([], False, False)
    await rejects(db_session, "uq_record_versions_record_version", version(row, 1))


async def test_ingest_event_defaults_and_idempotency(db_session: AsyncSession) -> None:
    crm = await make_system(db_session)

    def event() -> IngestEvent:
        return IngestEvent(
            batch_id=uuid.uuid4(),
            source_system_id=crm.id,
            record_type="account",
            external_id="C-1",
            event_type="upsert",
            payload={"name": "Ana Lopez"},
            source_updated_at=NOW,
            idempotency_key=sha("C-1|upsert"),
        )

    first = event()
    await add(db_session, first)
    await db_session.refresh(first)

    assert (first.status, first.attempts) == ("pending", 0)
    await rejects(db_session, "uq_ingest_events_idempotency_key", event())


async def test_source_system_key_and_reliability_are_checked(db_session: AsyncSession) -> None:
    await rejects(db_session, "ck_source_systems_key", SourceSystem(key="erp", name="ERP"))
    await rejects(
        db_session,
        "ck_source_systems_reliability_weight",
        SourceSystem(key="support", name="Support", reliability_weight=Decimal("1.50")),
    )


async def test_deleting_a_record_cascades_to_links_and_versions(db_session: AsyncSession) -> None:
    row = await make_record(db_session, await make_system(db_session))
    await add(db_session, link(await make_entity(db_session), row), version(row, 1))

    await db_session.execute(text("DELETE FROM source_records WHERE id = :id"), {"id": row.id})

    assert await count(db_session, "entity_links", "source_record_id", row.id) == 0
    assert await count(db_session, "record_versions", "source_record_id", row.id) == 0


# -------------------------------------------------------------------------- links


async def test_a_record_has_at_most_one_non_rejected_link(db_session: AsyncSession) -> None:
    row = await make_record(db_session, await make_system(db_session))
    first, second = await make_entity(db_session), await make_entity(db_session)
    await add(db_session, link(first, row))

    await rejects(db_session, "uq_entity_links_active_record", link(second, row, "needs_review"))


async def test_rejected_links_do_not_block_a_new_link(db_session: AsyncSession) -> None:
    row = await make_record(db_session, await make_system(db_session))
    first, second = await make_entity(db_session), await make_entity(db_session)

    await add(db_session, link(first, row, "rejected"), link(second, row, "confirmed"))

    statuses = await db_session.scalars(
        select(EntityLink.status).where(EntityLink.source_record_id == row.id)
    )
    assert sorted(statuses) == ["confirmed", "rejected"]


async def test_link_status_and_confidence_are_checked(db_session: AsyncSession) -> None:
    row = await make_record(db_session, await make_system(db_session))
    entity = await make_entity(db_session)
    too_sure = link(entity, row)
    too_sure.match_confidence = Decimal("1.200")

    await rejects(db_session, "ck_entity_links_status", link(entity, row, "maybe"))
    await rejects(db_session, "ck_entity_links_match_confidence", too_sure)


async def test_rejected_pairs_must_be_ordered_and_unique(db_session: AsyncSession) -> None:
    crm = await make_system(db_session)
    a, b = await make_record(db_session, crm, "C-1"), await make_record(db_session, crm, "C-2")
    low, high = sorted((a.id, b.id))
    user = await make_user(db_session)

    def pair(first: uuid.UUID, second: uuid.UUID) -> RejectedPair:
        return RejectedPair(record_a_id=first, record_b_id=second, rejected_by=user.id)

    await rejects(db_session, "ck_rejected_pairs_ordered", pair(high, low))
    await add(db_session, pair(low, high))
    await rejects(db_session, "uq_rejected_pairs_pair", pair(low, high))


# ----------------------------------------------------------------------- findings


async def make_rule(session: AsyncSession) -> Rule:
    rule = Rule(
        key="R999",
        name="Test rule",
        description="Used by tests only",
        category="missing_evidence",
        default_severity="medium",
        severity="medium",
        certainty=Decimal("0.90"),
    )
    await add(session, rule)
    return rule


def finding(entity: Entity, rule: Rule, **extra: Any) -> Finding:
    values: dict[str, Any] = {
        "entity_id": entity.id,
        "rule_id": rule.id,
        "rule_key": rule.key,
        "fingerprint": sha("fp"),
        "title": "Email differs",
        "severity": "medium",
        "confidence": Decimal("0.800"),
        "confidence_breakdown": {},
        "priority_score": Decimal("1.200"),
        "evidence": {"facts": []},
        "evidence_hash": sha("evidence"),
        "systems": ["crm", "billing"],
        "first_detected_at": NOW,
        "last_detected_at": NOW,
    }
    return Finding(**(values | extra))


async def test_finding_defaults_and_fingerprint_uniqueness(db_session: AsyncSession) -> None:
    entity, rule = await make_entity(db_session), await make_rule(db_session)
    first = finding(entity, rule)
    await add(db_session, first)
    await db_session.refresh(first)

    assert (first.status, first.reopen_count) == ("open", 0)
    assert (first.resolved_evidence_hash, first.explained_evidence_hash) == (None, None)
    await rejects(db_session, "uq_findings_entity_fingerprint", finding(entity, rule))


async def test_finding_evidence_must_be_an_object(db_session: AsyncSession) -> None:
    entity, rule = await make_entity(db_session), await make_rule(db_session)

    await rejects(db_session, "ck_findings_evidence_object", finding(entity, rule, evidence=[1]))


async def test_finding_status_is_checked(db_session: AsyncSession) -> None:
    entity, rule = await make_entity(db_session), await make_rule(db_session)

    await rejects(db_session, "ck_findings_status", finding(entity, rule, status="snoozed"))


# --------------------------------------------------------------------- simulation


async def make_run(session: AsyncSession) -> SimulationRun:
    run = SimulationRun(
        seed=42,
        config={"customers": 10},
        status="running",
        started_by=(await make_user(session)).id,
        started_at=NOW,
    )
    await add(session, run)
    return run


def issue(run: SimulationRun, **extra: Any) -> InjectedIssue:
    values: dict[str, Any] = {
        "simulation_run_id": run.id,
        "issue_type": "email_mismatch",
        "ground_truth_key": "GT-0001",
        "expected_rule_key": "R001",
        "system_key": "crm",
        "details": {},
    }
    return InjectedIssue(**(values | extra))


def truth(run: SimulationRun, key: str = "GT-0001") -> SimulationGroundTruth:
    return SimulationGroundTruth(
        simulation_run_id=run.id,
        system_key="billing",
        record_type="invoice",
        external_id="INV-1",
        ground_truth_key=key,
    )


async def test_injected_issue_defaults(db_session: AsyncSession) -> None:
    row = issue(await make_run(db_session))
    await add(db_session, row)
    await db_session.refresh(row)

    assert (row.acceptable_rule_keys, row.is_decoy, row.is_scenario) == ([], False, False)


async def test_only_scenarios_may_omit_the_system(db_session: AsyncSession) -> None:
    run = await make_run(db_session)

    await rejects(db_session, "ck_injected_issues_system_key_required", issue(run, system_key=None))
    await add(
        db_session,
        issue(
            run,
            issue_type="churn_with_early_signals",
            expected_rule_key=None,
            system_key=None,
            is_scenario=True,
            details={"incident_at": None, "expected_crossing_at": None},
        ),
    )


async def test_a_scenario_is_never_a_decoy(db_session: AsyncSession) -> None:
    run = await make_run(db_session)

    await rejects(
        db_session,
        "ck_injected_issues_scenario_not_decoy",
        issue(run, expected_rule_key=None, is_scenario=True, is_decoy=True),
    )


async def test_ground_truth_is_one_row_per_source_record(db_session: AsyncSession) -> None:
    run = await make_run(db_session)
    await add(db_session, truth(run, "GT-0001"))

    await rejects(db_session, "pk_simulation_ground_truth", truth(run, "GT-0002"))


async def test_deleting_a_run_cascades_to_its_labels(db_session: AsyncSession) -> None:
    run = await make_run(db_session)
    await add(db_session, issue(run), truth(run))

    await db_session.execute(text("DELETE FROM simulation_runs WHERE id = :id"), {"id": run.id})

    assert await count(db_session, "injected_issues", "simulation_run_id", run.id) == 0
    assert await count(db_session, "simulation_ground_truth", "simulation_run_id", run.id) == 0


# ------------------------------------------------------------ risk & investigations


def investigation(entity: Entity, inputs_hash: str, **extra: Any) -> Investigation:
    values: dict[str, Any] = {
        "entity_id": entity.id,
        "incident_kind": "churn",
        "incident_at": NOW,
        "lookback_days": 120,
        "warning_threshold": Decimal("0.60"),
        "inputs_hash": inputs_hash,
        "rule_set": {"R001": 1},
        "checkpoints_total": 120,
    }
    return Investigation(**(values | extra))


async def test_entity_risk_score_and_level_are_checked(db_session: AsyncSession) -> None:
    entity = await make_entity(db_session)

    def risk(**extra: Any) -> EntityRisk:
        values: dict[str, Any] = {
            "entity_id": entity.id,
            "score": Decimal("0.500"),
            "level": "watch",
            "confidence": Decimal("0.700"),
            "signals": {},
            "trail": {},
            "model_version": 1,
            "assessed_at": NOW,
        }
        return EntityRisk(**(values | extra))

    await rejects(db_session, "ck_entity_risk_level", risk(level="severe"))
    await rejects(db_session, "ck_entity_risk_score", risk(score=Decimal("1.500")))
    await add(db_session, risk())


async def test_two_non_failed_investigations_cannot_share_inputs(db_session: AsyncSession) -> None:
    entity = await make_entity(db_session)
    first = investigation(entity, sha("inputs"))
    await add(db_session, first)
    await db_session.refresh(first)

    assert (first.status, first.checkpoints_done) == ("queued", 0)
    await rejects(db_session, "uq_investigations_inputs", investigation(entity, sha("inputs")))


async def test_a_failed_investigation_can_be_retried(db_session: AsyncSession) -> None:
    entity = await make_entity(db_session)

    await add(
        db_session,
        investigation(entity, sha("inputs"), status="failed", error_code="TIMEOUT"),
        investigation(entity, sha("inputs"), status="failed", error_code="TIMEOUT"),
        investigation(entity, sha("inputs")),
    )


async def test_finding_investigations_need_a_fingerprint(db_session: AsyncSession) -> None:
    entity = await make_entity(db_session)

    await rejects(
        db_session,
        "ck_investigations_finding_fingerprint_required",
        investigation(entity, sha("a"), incident_kind="finding"),
    )
    await add(
        db_session,
        investigation(entity, sha("b"), incident_kind="finding", finding_fingerprint=sha("fp")),
    )


@pytest.mark.parametrize(
    ("field", "value", "constraint"),
    [
        ("lookback_days", 0, "ck_investigations_lookback_days"),
        ("lookback_days", 366, "ck_investigations_lookback_days"),
        ("warning_threshold", Decimal(0), "ck_investigations_warning_threshold"),
        ("outcome", "maybe", "ck_investigations_outcome"),
    ],
)
async def test_investigation_ranges_are_checked(
    db_session: AsyncSession, field: str, value: object, constraint: str
) -> None:
    entity = await make_entity(db_session)

    await rejects(db_session, constraint, investigation(entity, sha(field), **{field: value}))


async def test_checkpoints_are_unique_per_time(db_session: AsyncSession) -> None:
    inv = investigation(await make_entity(db_session), sha("inputs"))
    await add(db_session, inv)

    def checkpoint(seq: int, at: datetime) -> InvestigationCheckpoint:
        return InvestigationCheckpoint(
            investigation_id=inv.id,
            seq=seq,
            at=at,
            risk_score=Decimal("0.100"),
            risk_level="low",
            risk_confidence=Decimal("0.500"),
        )

    first = checkpoint(0, NOW)
    await add(db_session, first, checkpoint(1, NOW + timedelta(days=1)))
    await db_session.refresh(first)

    assert first.finding_fingerprints == []
    await rejects(db_session, "uq_investigation_checkpoints_at", checkpoint(2, NOW))
