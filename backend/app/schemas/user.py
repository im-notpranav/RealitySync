import uuid
from datetime import datetime

from pydantic import EmailStr

from app.schemas.common import Name, NewPassword, RequestModel, ResponseModel, Role


class UserOut(ResponseModel):
    """The user object (04 §2 `GET /auth/me`, §3)."""

    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class UserPage(ResponseModel):
    items: list[UserOut]
    page: int
    page_size: int
    total: int


class UserCreate(RequestModel):
    email: EmailStr
    full_name: Name
    role: Role
    password: NewPassword


class UserUpdate(RequestModel):
    """Only the fields that are present change; `null` means "leave as is"."""

    full_name: Name | None = None
    role: Role | None = None
    is_active: bool | None = None
    password: NewPassword | None = None
