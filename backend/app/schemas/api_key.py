import uuid
from datetime import datetime
from typing import Literal

from app.schemas.common import Name, RequestModel, ResponseModel

SystemKey = Literal["crm", "billing", "support"]


class ApiKeyCreate(RequestModel):
    name: Name
    # Bound keys may only send events for this system (04 §5).
    source_system: SystemKey | None = None


class ApiKeyCreated(ResponseModel):
    """`key` is the secret; it is returned here once and never again (04 §3)."""

    id: uuid.UUID
    name: str
    key: str
    created_at: datetime


class ApiKeyOut(ResponseModel):
    """An API key without its secret."""

    id: uuid.UUID
    name: str
    key_prefix: str
    source_system: SystemKey | None
    created_by: uuid.UUID
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class ApiKeyPage(ResponseModel):
    items: list[ApiKeyOut]
    page: int
    page_size: int
    total: int
