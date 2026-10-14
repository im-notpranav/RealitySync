import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import RECORD_TYPES, one_of


class IngestEvent(Base):
    """One received record event; the durable ingest queue (05 §2.5). `error` never holds PII."""

    __tablename__ = "ingest_events"
    __table_args__ = (
        CheckConstraint(one_of("record_type", RECORD_TYPES), name="record_type"),
        CheckConstraint(one_of("event_type", ("upsert", "delete")), name="event_type"),
        CheckConstraint(
            one_of("status", ("pending", "processing", "processed", "failed")), name="status"
        ),
        Index("idx_ingest_pending", "received_at", postgresql_where=text("status = 'pending'")),
        Index("idx_ingest_processing", "locked_at", postgresql_where=text("status = 'processing'")),
        Index("idx_ingest_status_received", "status", text("received_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    source_system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_systems.id")
    )
    record_type: Mapped[str] = mapped_column(Text)
    external_id: Mapped[str] = mapped_column(Text)
    parent_external_id: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(Text, unique=True)
    status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    error: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourceRecord(Base):
    """Current state of one source record (05 §2.6). Parents are logical (`parent_external_id`
    within the same system), not a foreign key, because events arrive out of order (05 §4).
    """

    __tablename__ = "source_records"
    __table_args__ = (
        CheckConstraint(one_of("record_type", RECORD_TYPES), name="record_type"),
        UniqueConstraint(
            "source_system_id",
            "record_type",
            "external_id",
            name="uq_source_records_system_type_external_id",
        ),
        Index(
            "ix_source_records_system_type_parent",
            "source_system_id",
            "record_type",
            "parent_external_id",
        ),
        Index(
            "ix_source_records_normalized",
            "normalized",
            postgresql_using="gin",
            postgresql_ops={"normalized": "jsonb_path_ops"},
        ),
        # Blocking keys for entity resolution (03 §M3).
        Index("ix_source_records_email_canonical", text("(normalized ->> 'email_canonical')")),
        Index("ix_source_records_phone_e164", text("(normalized ->> 'phone_e164')")),
        Index("ix_source_records_name_block", text("(normalized ->> 'name_block')")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    source_system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_systems.id")
    )
    record_type: Mapped[str] = mapped_column(Text)
    external_id: Mapped[str] = mapped_column(Text)
    parent_external_id: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    normalized: Mapped[dict[str, Any]] = mapped_column(JSONB)
    record_hash: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    source_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_deleted: Mapped[bool] = mapped_column(server_default=text("false"))
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RecordVersion(Base):
    """One version of a source record (05 §2.6.1). Insert-only and never pruned (FR-TMX-007).

    `source_updated_at` is the recorded time, the Time Machine's only time axis.
    """

    __tablename__ = "record_versions"
    __table_args__ = (
        UniqueConstraint("source_record_id", "version", name="uq_record_versions_record_version"),
        Index(
            "ix_record_versions_record_recorded",
            "source_record_id",
            text("source_updated_at DESC"),
        ),
        Index("idx_versions_system_recorded", "source_system_id", text("source_updated_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_records.id", ondelete="CASCADE")
    )
    source_system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_systems.id")
    )
    version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    normalized: Mapped[dict[str, Any]] = mapped_column(JSONB)
    changed_fields: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'::text[]")
    )
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_deleted: Mapped[bool] = mapped_column(server_default=text("false"))
    out_of_order: Mapped[bool] = mapped_column(server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
