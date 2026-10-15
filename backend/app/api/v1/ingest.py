"""Ingest endpoints (04 §5): admin JWT or `X-API-Key` for sending, admin for the event list."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AwareDatetime

from app.core.deps import ClockDep, SessionDep, get_current_user, require_role
from app.core.errors import PermissionDenied
from app.models import User
from app.schemas.api_key import SystemKey
from app.schemas.ingest import (
    IngestAccepted,
    IngestBatchIn,
    IngestEventOut,
    IngestEventPage,
    IngestStatus,
)
from app.services import ingest_service
from app.services.ingest_service import IngestCaller

AdminUser = Annotated[User, Depends(require_role("admin"))]

_api_key = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer = HTTPBearer(auto_error=False)


async def ingest_caller(
    session: SessionDep,
    clock: ClockDep,
    api_key: Annotated[str | None, Security(_api_key)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> IngestCaller:
    """An API key when `X-API-Key` is sent (it wins over a bearer token), else an admin JWT."""
    if api_key is not None:
        key = await ingest_service.authenticate_api_key(session, api_key, clock.now())
        return IngestCaller(api_key=key)
    user = await get_current_user(session, clock, credentials)
    if user.role != "admin":
        raise PermissionDenied("Requires role admin or an API key")
    return IngestCaller(user_id=user.id)


router = APIRouter(prefix="/ingest/events", tags=["ingest"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def ingest_events(
    body: IngestBatchIn,
    caller: Annotated[IngestCaller, Depends(ingest_caller)],
    session: SessionDep,
    clock: ClockDep,
) -> IngestAccepted:
    return await ingest_service.ingest_batch(
        session, caller=caller, events=body.events, now=clock.now()
    )


@router.get("", dependencies=[Depends(require_role("admin"))])
async def list_events(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    status: IngestStatus | None = None,
    source: SystemKey | None = None,
    received_from: Annotated[AwareDatetime | None, Query(alias="from")] = None,
    received_to: Annotated[AwareDatetime | None, Query(alias="to")] = None,
    sort: Annotated[str | None, Query(max_length=64)] = None,
) -> IngestEventPage:
    items, total = await ingest_service.list_events(
        session,
        page=page,
        page_size=page_size,
        status=status,
        source=source,
        received_from=received_from,
        received_to=received_to,
        sort=sort,
    )
    return IngestEventPage(items=items, page=page, page_size=page_size, total=total)


@router.post("/{event_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_event(event_id: uuid.UUID, actor: AdminUser, session: SessionDep) -> IngestEventOut:
    return await ingest_service.retry_event(session, actor=actor, event_id=event_id)
