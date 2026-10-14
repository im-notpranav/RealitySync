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
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import SEVERITIES, SYSTEM_KEYS, between_0_and_1, one_of

RULE_CATEGORIES = ("field_conflict", "logic", "temporal", "structural", "missing_evidence")
FINDING_STATUSES = ("open", "acknowledged", "resolved", "false_positive", "auto_resolved")
FINDING_ACTIONS = (
    "created",
    "updated",
    "acknowledged",
    "resolved",
    "false_positive",
    "reopened",
    "auto_resolved",
    "explained",
)


class Rule(Base):
    """A detection rule (05 §2.10). Rows are synced from the code registry (T-019)."""

    __tablename__ = "rules"
    __table_args__ = (
        CheckConstraint(one_of("category", RULE_CATEGORIES), name="category"),
        CheckConstraint(one_of("default_severity", SEVERITIES), name="default_severity"),
        CheckConstraint(one_of("severity", SEVERITIES), name="severity"),
        CheckConstraint(between_0_and_1("certainty"), name="certainty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    key: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    default_severity: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text)
    certainty: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    is_enabled: Mapped[bool] = mapped_column(server_default=text("true"))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Finding(Base):
    """A detected contradiction on one entity (05 §2.11), unique per `(entity, fingerprint)`."""

    __tablename__ = "findings"
    __table_args__ = (
        CheckConstraint(one_of("severity", SEVERITIES), name="severity"),
        CheckConstraint(one_of("status", FINDING_STATUSES), name="status"),
        CheckConstraint(between_0_and_1("confidence"), name="confidence"),
        CheckConstraint("jsonb_typeof(evidence) = 'object'", name="evidence_object"),
        UniqueConstraint("entity_id", "fingerprint", name="uq_findings_entity_fingerprint"),
        Index("idx_findings_status_priority", "status", text("priority_score DESC")),
        Index("idx_findings_entity", "entity_id"),
        Index("idx_findings_rule_status", "rule_key", "status"),
        Index(
            "idx_findings_open",
            "severity",
            text("last_detected_at DESC"),
            postgresql_where=text("status IN ('open', 'acknowledged')"),
        ),
        Index("ix_findings_systems", "systems", postgresql_using="gin"),
        Index("idx_findings_created", "first_detected_at"),
        Index(
            "idx_findings_needs_explanation",
            text("priority_score DESC"),
            postgresql_where=text(
                "status IN ('open', 'acknowledged') "
                "AND explained_evidence_hash IS DISTINCT FROM evidence_hash"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE")
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.id"))
    rule_key: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default=text("'open'"))
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    confidence_breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB)
    priority_score: Mapped[Decimal] = mapped_column(Numeric(5, 3))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB)
    evidence_hash: Mapped[str] = mapped_column(Text)
    # Evidence hash at the time a user resolved / marked false positive (reopen rules, 03 §M6).
    resolved_evidence_hash: Mapped[str | None] = mapped_column(Text)
    # Evidence hash the latest saved explanation covers; differs → needs explanation (03 §M8).
    explained_evidence_hash: Mapped[str | None] = mapped_column(Text)
    systems: Mapped[list[str]] = mapped_column(ARRAY(Text))
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)
    reopen_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FindingEvent(Base):
    """History of a finding (05 §2.12)."""

    __tablename__ = "finding_events"
    __table_args__ = (
        CheckConstraint(one_of("action", FINDING_ACTIONS), name="action"),
        Index("ix_finding_events_finding_created", "finding_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE")
    )
    action: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FindingExplanation(Base):
    """A saved explanation of a finding (05 §2.13). The latest per finding is the newest row.

    The cache index is deliberately not unique: "Regenerate" stores a new row for the same input.
    """

    __tablename__ = "finding_explanations"
    __table_args__ = (
        CheckConstraint(
            one_of("likely_correct_system", (*SYSTEM_KEYS, "undetermined")),
            name="likely_correct_system",
        ),
        Index("ix_finding_explanations_finding_created", "finding_id", text("created_at DESC")),
        Index(
            "idx_explanations_cache",
            "input_hash",
            "prompt_version",
            "model",
            text("created_at DESC"),
            postgresql_where=text("is_fallback = false"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE")
    )
    input_hash: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    root_cause: Mapped[str] = mapped_column(Text)
    likely_correct_system: Mapped[str] = mapped_column(Text)
    suggested_actions: Mapped[list[str]] = mapped_column(JSONB)
    caveats: Mapped[str | None] = mapped_column(Text)
    cited_fact_ids: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'::text[]")
    )
    is_fallback: Mapped[bool] = mapped_column(server_default=text("false"))
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
