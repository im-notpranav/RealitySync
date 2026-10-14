import uuid
from typing import Literal

from pydantic import EmailStr

from app.schemas.common import NewPassword, Password, RequestModel, ResponseModel, Role


class LoginRequest(RequestModel):
    email: EmailStr
    password: Password


class TokenUser(ResponseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: Role


class TokenResponse(ResponseModel):
    """Body of `POST /auth/login` and `/auth/refresh` (04 §2)."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: TokenUser


class ChangePasswordRequest(RequestModel):
    current_password: Password
    new_password: NewPassword


class WsTicketResponse(ResponseModel):
    ticket: str
    expires_in: int
