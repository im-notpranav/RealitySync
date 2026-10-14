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
from app.models.enums import RISK_LEVELS, one_of

INVESTIGATION_STATUSES = ("queued", "running", "completed", "failed")


class Investigation(Base):
    """A replay of an entity's history before an incident (05 §2.22, 03 §M14).

    An identical request (same `inputs_hash`) returns the existing investigation unless that one
    failed, so failed ones can be retried (`uq_investigations_inputs`).
    """

    __tablename__ = "investigations"
    __table_args__ = (
        CheckConstraint(one_of("incident_kind", ("churn", "finding")), name="incident_kind"),
        CheckConstraint("lookback_days >= 1 AND lookback_days <= 365", name="lookback_days"),
        CheckConstraint(
            "warning_threshold > 0 AND warning_threshold <= 1", name="warning_threshold"
        ),
        CheckConstraint(one_of("status", INVESTIGATION_STATUSES), name="status"),
        CheckConstraint(one_of("outcome", ("crossed", "never_crossed")), name="outcome"),
        CheckConstraint(
            "incident_kind = 'churn' OR finding_fingerprint IS NOT NULL",
            name="finding_fingerprint_required",
        ),
        Index(
            "uq_investigations_inputs",
            "inputs_hash",
            unique=True,
            postgresql_where=text("status <> 'failed'"),
        ),
        Index("ix_investigations_entity_created", "entity_id", text("created_at DESC")),
        # Restart sweep: queued and running ones become failed (02 §3.7).
        Index(
            "ix_investigations_active_status",
            "status",
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE")
    )
    incident_kind: Mapped[str] = mapped_column(Text)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="SET NULL")
    )
    # Copied at request time, so it survives deletion of the finding.
    finding_fingerprint: Mapped[str | None] = mapped_column(Text)
    incident_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lookback_days: Mapped[int] = mapped_column(Integer)
    warning_threshold: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    status: Mapped[str] = mapped_column(Text, server_default=text("'queued'"))
    inputs_hash: Mapped[str] = mapped_column(Text)
    rule_set: Mapped[dict[str, Any]] = mapped_column(JSONB)
    checkpoints_total: Mapped[int] = mapped_column(Integer)
    checkpoints_done: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    outcome: Mapped[str | None] = mapped_column(Text)
    first_detectable_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lead_time_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 1))
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InvestigationCheckpoint(Base):
    """One evaluated point in time of an investigation (05 §2.23). `seq` is 0-based by `at`."""

    __tablename__ = "investigation_checkpoints"
    __table_args__ = (
        CheckConstraint(one_of("risk_level", RISK_LEVELS), name="risk_level"),
        UniqueConstraint("investigation_id", "at", name="uq_investigation_checkpoints_at"),
    )

    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    risk_score: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    risk_level: Mapped[str] = mapped_column(Text)
    risk_confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    finding_fingerprints: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'::text[]")
    )
    # Only for `finding` incidents.
    target_present: Mapped[bool | None] = mapped_column()
