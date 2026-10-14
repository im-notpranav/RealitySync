import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import SEVERITIES, one_of

ALERT_TYPES = (
    "finding_created",
    "finding_escalated",
    "finding_resolved",
    "link_needs_review",
    "risk_threshold_crossed",
)


class Alert(Base):
    """A notification shown to users (05 §2.14). `dedup_key` follows 03 §M7."""

    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(one_of("type", ALERT_TYPES), name="type"),
        CheckConstraint(one_of("severity", SEVERITIES), name="severity"),
        Index("ix_alerts_created_at", text("created_at DESC")),
        Index("ix_alerts_dedup_key_created_at", "dedup_key", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    type: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE")
    )
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE")
    )
    link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entity_links.id", ondelete="CASCADE")
    )
    dedup_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlertRead(Base):
    """Marks an alert as read by one user (05 §2.15)."""

    __tablename__ = "alert_reads"
    __table_args__ = (Index("ix_alert_reads_user_id", "user_id"),)

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
