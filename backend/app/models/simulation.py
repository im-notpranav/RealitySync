import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import RECORD_TYPES, SYSTEM_KEYS, one_of

RUN_STATUSES = ("running", "completed", "stopped", "failed")


class SimulationRun(Base):
    """One simulator run (05 §2.16)."""

    __tablename__ = "simulation_runs"
    __table_args__ = (CheckConstraint(one_of("status", RUN_STATUSES), name="status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    seed: Mapped[int] = mapped_column(Integer)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text)
    events_sent: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    events_total: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    started_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)


class InjectedIssue(Base):
    """A ground-truth label for evaluation (05 §2.17).

    Scenarios span systems, so only they may leave `system_key` empty; a scenario is never a decoy.
    """

    __tablename__ = "injected_issues"
    __table_args__ = (
        CheckConstraint(one_of("system_key", SYSTEM_KEYS), name="system_key"),
        CheckConstraint("is_scenario OR system_key IS NOT NULL", name="system_key_required"),
        CheckConstraint("NOT (is_scenario AND is_decoy)", name="scenario_not_decoy"),
        Index("ix_injected_issues_run_issue_type", "simulation_run_id", "issue_type"),
        Index("ix_injected_issues_ground_truth_key", "ground_truth_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    simulation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_runs.id", ondelete="CASCADE")
    )
    issue_type: Mapped[str] = mapped_column(Text)
    ground_truth_key: Mapped[str] = mapped_column(Text)
    expected_rule_key: Mapped[str | None] = mapped_column(Text)
    acceptable_rule_keys: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'::text[]")
    )
    is_decoy: Mapped[bool] = mapped_column(server_default=text("false"))
    is_scenario: Mapped[bool] = mapped_column(server_default=text("false"))
    system_key: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB)
    injected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SimulationGroundTruth(Base):
    """Which source record belongs to which ground-truth customer (05 §2.17.1).

    Written by the runner before a record's first event; never sent through ingest.
    """

    __tablename__ = "simulation_ground_truth"
    __table_args__ = (
        CheckConstraint(one_of("system_key", SYSTEM_KEYS), name="system_key"),
        CheckConstraint(one_of("record_type", RECORD_TYPES), name="record_type"),
        Index("ix_simulation_ground_truth_run_key", "simulation_run_id", "ground_truth_key"),
    )

    simulation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_runs.id", ondelete="CASCADE"), primary_key=True
    )
    system_key: Mapped[str] = mapped_column(Text, primary_key=True)
    record_type: Mapped[str] = mapped_column(Text, primary_key=True)
    external_id: Mapped[str] = mapped_column(Text, primary_key=True)
    ground_truth_key: Mapped[str] = mapped_column(Text)


class EvaluationRun(Base):
    """Precision / recall of one simulation run (05 §2.18; metrics in 03 §M9)."""

    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    simulation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_runs.id", ondelete="CASCADE")
    )
    precision: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    recall: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    f1: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    true_positives: Mapped[int] = mapped_column(Integer)
    false_positives: Mapped[int] = mapped_column(Integer)
    false_negatives: Mapped[int] = mapped_column(Integer)
    ignored: Mapped[int] = mapped_column(Integer)
    matching: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    investigation: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    by_type: Mapped[dict[str, Any]] = mapped_column(JSONB)
    misses: Mapped[list[Any]] = mapped_column(JSONB)
    false_positive_findings: Mapped[list[Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
