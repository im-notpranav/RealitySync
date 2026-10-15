"""Ingest request and response bodies (04 §5)."""

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal, Self

from pydantic import BeforeValidator, Field, StringConstraints, model_validator

from app.domain.normalize import InvalidTimestamp, normalize_ts
from app.schemas.api_key import SystemKey
from app.schemas.common import RequestModel, ResponseModel

RecordType = Literal["account", "subscription", "invoice", "ticket"]
EventType = Literal["upsert", "delete"]
IngestStatus = Literal["pending", "processing", "processed", "failed"]

MAX_BATCH = 500
MAX_PAYLOAD_BYTES = 16 * 1024
CHILD_RECORD_TYPES = frozenset({"subscription", "invoice", "ticket"})


def _aware_utc(value: Any) -> datetime:
    """ISO 8601 with an offset or epoch seconds, as UTC; naive values are rejected (FR-NRM-004)."""
    try:
        parsed = normalize_ts(value)
    except InvalidTimestamp as exc:
        raise ValueError(str(exc)) from exc
    if parsed is None:
        raise ValueError("timestamp is required")
    return parsed


Timestamp = Annotated[datetime, BeforeValidator(_aware_utc)]
Identifier = Annotated[str, StringConstraints(min_length=1, max_length=255)]


class IngestEventIn(RequestModel):
    """One event of a batch. Validated one by one, so a bad event rejects only itself.

    `payload` is kept exactly as sent: unknown keys are stored raw and ignored by normalization
    (04 §1.5). Its per-record-type fields are checked by the ingest service (04 §5.1).
    """

    source: SystemKey
    record_type: RecordType
    external_id: Identifier
    parent_external_id: Identifier | None = None
    event_type: EventType
    source_updated_at: Timestamp
    idempotency_key: Identifier | None = None
    payload: dict[str, Any]

    @model_validator(mode="after")
    def _parent_for_children(self) -> Self:
        if self.record_type in CHILD_RECORD_TYPES and self.parent_external_id is None:
            raise ValueError(f"parent_external_id is required for {self.record_type}")
        return self


class IngestBatchIn(RequestModel):
    """Events stay untyped here; more than 500 is `413`, a bad event is a partial rejection."""

    events: list[Any] = Field(min_length=1)


class Rejection(ResponseModel):
    index: int
    code: str
    message: str


class IngestAccepted(ResponseModel):
    accepted: int
    duplicates: int
    rejected: list[Rejection]
    batch_id: uuid.UUID


class IngestEventOut(ResponseModel):
    id: uuid.UUID
    source: SystemKey
    record_type: RecordType
    external_id: str
    status: IngestStatus
    attempts: int
    error: str | None
    received_at: datetime
    processed_at: datetime | None


class IngestEventPage(ResponseModel):
    items: list[IngestEventOut]
    page: int
    page_size: int
    total: int
