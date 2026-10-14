"""User administration endpoints (04 §3). API keys arrive with T-011."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import ClockDep, SessionDep, require_role
from app.models import User
from app.schemas.common import Role
from app.schemas.user import UserCreate, UserOut, UserPage, UserUpdate
from app.services import user_service

AdminUser = Annotated[User, Depends(require_role("admin"))]

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_role("admin"))])


@router.get("")
async def list_users(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    role: Role | None = None,
    is_active: bool | None = None,
    q: Annotated[str | None, Query(max_length=255)] = None,
    sort: Annotated[str | None, Query(max_length=64)] = None,
) -> UserPage:
    items, total = await user_service.list_users(
        session,
        page=page,
        page_size=page_size,
        role=role,
        is_active=is_active,
        q=q.strip() if q else None,
        sort=sort,
    )
    return UserPage(
        items=[UserOut.model_validate(u) for u in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, actor: AdminUser, session: SessionDep) -> UserOut:
    user = await user_service.create_user(session, actor=actor, data=body)
    return UserOut.model_validate(user)


@router.patch("/{user_id}")
async def update_user(
    user_id: uuid.UUID, body: UserUpdate, actor: AdminUser, session: SessionDep, clock: ClockDep
) -> UserOut:
    user = await user_service.update_user(
        session, actor=actor, user_id=user_id, data=body, now=clock.now()
    )
    return UserOut.model_validate(user)
