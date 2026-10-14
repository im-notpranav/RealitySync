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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import RISK_LEVELS, between_0_and_1, one_of


class EntityRisk(Base):
    """Current live risk of an entity (05 §2.20, 03 §M12). Written only by live detection."""

    __tablename__ = "entity_risk"
    __table_args__ = (
        CheckConstraint(between_0_and_1("score"), name="score"),
        CheckConstraint(one_of("level", RISK_LEVELS), name="level"),
        CheckConstraint(between_0_and_1("confidence"), name="confidence"),
        Index("idx_entity_risk_level", "level", text("score DESC")),
    )

    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True
    )
    score: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    level: Mapped[str] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    signals: Mapped[dict[str, Any]] = mapped_column(JSONB)
    trail: Mapped[dict[str, Any]] = mapped_column(JSONB)
    model_version: Mapped[int] = mapped_column(Integer)
    # The detection context's `now`, not the wall clock.
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RiskEvent(Base):
    """A change of an entity's risk level (05 §2.21). `from_level` is NULL on the first one."""

    __tablename__ = "risk_events"
    __table_args__ = (
        CheckConstraint(one_of("from_level", RISK_LEVELS), name="from_level"),
        CheckConstraint(one_of("to_level", RISK_LEVELS), name="to_level"),
        Index("ix_risk_events_entity_at", "entity_id", text("at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE")
    )
    from_level: Mapped[str | None] = mapped_column(Text)
    to_level: Mapped[str] = mapped_column(Text)
    score: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
