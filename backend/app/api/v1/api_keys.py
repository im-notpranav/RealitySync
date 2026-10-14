"""API key administration (04 §3, FR-AUT-005). Secrets are shown once, at creation."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import ClockDep, SessionDep, require_role
from app.models import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyPage
from app.services import ingest_service

AdminUser = Annotated[User, Depends(require_role("admin"))]

router = APIRouter(
    prefix="/api-keys", tags=["api-keys"], dependencies=[Depends(require_role("admin"))]
)


@router.get("")
async def list_api_keys(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> ApiKeyPage:
    items, total = await ingest_service.list_api_keys(session, page=page, page_size=page_size)
    return ApiKeyPage(items=items, page=page, page_size=page_size, total=total)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: ApiKeyCreate, actor: AdminUser, session: SessionDep
) -> ApiKeyCreated:
    key, secret = await ingest_service.create_api_key(session, actor=actor, data=body)
    return ApiKeyCreated(id=key.id, name=key.name, key=secret, created_at=key.created_at)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID, actor: AdminUser, session: SessionDep, clock: ClockDep
) -> Response:
    await ingest_service.revoke_api_key(session, actor=actor, key_id=key_id, now=clock.now())
    return Response(status_code=status.HTTP_204_NO_CONTENT)
