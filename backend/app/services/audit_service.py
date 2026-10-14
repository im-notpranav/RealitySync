"""Audit trail writes (FR-AUT-006, 05 §2.19)."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


def record(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    action: str,
    target_type: str,
    target_id: str | uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Add an audit row to the caller's transaction, so it commits or rolls back with the action.

    `metadata` must hold ids and enum values only, never emails, names or other PII.
    """
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=None if target_id is None else str(target_id),
        metadata_=metadata or {},
    )
    session.add(entry)
    return entry
