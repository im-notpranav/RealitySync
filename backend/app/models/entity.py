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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import SEVERITIES, between_0_and_1, one_of

LINK_STATUSES = ("auto_matched", "needs_review", "confirmed", "rejected")
MATCH_METHODS = ("blocking_score", "external_ref", "parent", "manual")


class Entity(Base):
    """A resolved real-world customer (05 §2.7).

    `detection_requested_at` is the durable detection queue: set when the entity's rules must be
    re-run, cleared by the detection loop (02 §3.3).
    """

    __tablename__ = "entities"
    __table_args__ = (
        CheckConstraint(one_of("entity_type", ("customer",)), name="entity_type"),
        CheckConstraint(one_of("health", ("consistent", "inconsistent", "unknown")), name="health"),
        CheckConstraint(one_of("highest_severity", SEVERITIES), name="highest_severity"),
        Index("ix_entities_health", "health"),
        Index("ix_entities_open_findings_count", text("open_findings_count DESC")),
        Index(
            "idx_entities_detection_due",
            "detection_requested_at",
            postgresql_where=text("detection_requested_at IS NOT NULL"),
        ),
        Index(
            "ix_entities_canonical_name_trgm",
            "canonical_name",
            postgresql_using="gin",
            postgresql_ops={"canonical_name": "gin_trgm_ops"},
        ),
        Index(
            "ix_entities_canonical_email_trgm",
            "canonical_email",
            postgresql_using="gin",
            postgresql_ops={"canonical_email": "gin_trgm_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    entity_type: Mapped[str] = mapped_column(Text, server_default=text("'customer'"))
    canonical_name: Mapped[str] = mapped_column(Text)
    canonical_email: Mapped[str | None] = mapped_column(Text)
    health: Mapped[str] = mapped_column(Text, server_default=text("'unknown'"))
    open_findings_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    highest_severity: Mapped[str | None] = mapped_column(Text)
    detection_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EntityLink(Base):
    """Links a source record to an entity (05 §2.8).

    The partial unique index keeps a record linked to at most one entity unless rejected.
    """

    __tablename__ = "entity_links"
    __table_args__ = (
        CheckConstraint(between_0_and_1("match_confidence"), name="match_confidence"),
        CheckConstraint(one_of("match_method", MATCH_METHODS), name="match_method"),
        CheckConstraint(one_of("status", LINK_STATUSES), name="status"),
        UniqueConstraint("entity_id", "source_record_id", name="uq_entity_links_entity_record"),
        Index(
            "uq_entity_links_active_record",
            "source_record_id",
            unique=True,
            postgresql_where=text("status <> 'rejected'"),
        ),
        Index("ix_entity_links_entity_id", "entity_id"),
        Index("ix_entity_links_status_confidence", "status", text("match_confidence DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE")
    )
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_records.id", ondelete="CASCADE")
    )
    match_confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    match_method: Mapped[str] = mapped_column(Text)
    match_features: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    status: Mapped[str] = mapped_column(Text)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RejectedPair(Base):
    """Do-not-link memory (05 §2.9). Store the pair with `record_a_id < record_b_id`."""

    __tablename__ = "rejected_pairs"
    __table_args__ = (
        CheckConstraint("record_a_id < record_b_id", name="ordered"),
        UniqueConstraint("record_a_id", "record_b_id", name="uq_rejected_pairs_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    record_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_records.id", ondelete="CASCADE")
    )
    record_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_records.id", ondelete="CASCADE")
    )
    rejected_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
