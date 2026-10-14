"""Auth endpoints (04 §2)."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response, status

from app.core.config import settings
from app.core.deps import ClockDep, SessionDep, require_role
from app.core.errors import UnauthenticatedError
from app.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    TokenUser,
    WsTicketResponse,
)
from app.schemas.user import UserOut
from app.services import auth_service
from app.services.auth_service import IssuedTokens

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

AnyUser = Annotated[User, Depends(require_role("viewer"))]
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


@router.post("/login")
async def login(
    body: LoginRequest, request: Request, response: Response, session: SessionDep, clock: ClockDep
) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    tokens = await auth_service.login(
        session, email=body.email, password=body.password, client_ip=client_ip, now=clock.now()
    )
    return _token_response(tokens, response)


@router.post("/refresh")
async def refresh(
    response: Response,
    session: SessionDep,
    clock: ClockDep,
    refresh_token: RefreshCookie = None,
    x_requested_with: Annotated[str | None, Header()] = None,
) -> TokenResponse:
    # The custom header cannot be sent cross-site without CORS approval (02 §5 CSRF).
    if x_requested_with != "fetch":
        raise UnauthenticatedError("Missing X-Requested-With header")
    tokens = await auth_service.refresh(session, refresh_token=refresh_token, now=clock.now())
    return _token_response(tokens, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: AnyUser, session: SessionDep, clock: ClockDep, refresh_token: RefreshCookie = None
) -> Response:
    await auth_service.logout(session, user=user, refresh_token=refresh_token, now=clock.now())
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        REFRESH_COOKIE,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=_secure_cookies(),
    )
    return response


@router.get("/me")
async def me(user: AnyUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    user: AnyUser,
    session: SessionDep,
    clock: ClockDep,
    refresh_token: RefreshCookie = None,
) -> Response:
    await auth_service.change_password(
        session,
        user=user,
        current_password=body.current_password,
        new_password=body.new_password,
        refresh_token=refresh_token,
        now=clock.now(),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/ws-ticket")
async def ws_ticket(user: AnyUser, clock: ClockDep) -> WsTicketResponse:
    ticket, expires_in = auth_service.issue_ws_ticket(user, clock.now())
    return WsTicketResponse(ticket=ticket, expires_in=expires_in)


def _token_response(tokens: IssuedTokens, response: Response) -> TokenResponse:
    response.set_cookie(
        REFRESH_COOKIE,
        tokens.refresh_token,
        max_age=settings.REFRESH_TOKEN_DAYS * 24 * 3600,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=_secure_cookies(),
    )
    response.headers["Cache-Control"] = "no-store"
    return TokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
        user=TokenUser.model_validate(tokens.user),
    )


def _secure_cookies() -> bool:
    return settings.APP_ENV == "production"
