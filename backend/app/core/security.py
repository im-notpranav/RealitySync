"""Password hashing, access tokens, refresh tokens and WebSocket tickets (02 §5)."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

JWT_ALGORITHM = "HS256"
WS_TICKET_TTL_SECONDS = 60
WS_TICKET_PREFIX = "wst_"

_hasher = PasswordHasher()  # argon2-cffi defaults are Argon2id (RFC 9106 low-memory profile)
# Verified against when the email is unknown, so a miss costs as much time as a wrong password.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def burn_password_check(password: str) -> None:
    """Spend the time of one verification without a user, against timing-based email probing."""
    verify_password(_DUMMY_HASH, password)


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    role: str
    expires_at: datetime
    jti: str


def create_access_token(user_id: uuid.UUID, role: str, now: datetime) -> tuple[str, int]:
    """Signed HS256 JWT with `sub`, `role`, `exp`, `jti`. Returns the token and its lifetime."""
    lifetime = timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    claims = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(claims, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str, now: datetime) -> AccessClaims | None:
    """Claims of a valid, unexpired token; None otherwise.

    Expiry is checked against the injected clock rather than PyJWT's wall clock so tests and
    the rest of the app agree on "now".
    """
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": False, "require": ["sub", "role", "exp", "jti"]},
        )
        user_id = uuid.UUID(str(claims["sub"]))
        expires_at = datetime.fromtimestamp(int(claims["exp"]), tz=now.tzinfo)
    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None
    if expires_at <= now:
        return None
    return AccessClaims(user_id, str(claims["role"]), expires_at, str(claims["jti"]))


def new_refresh_token() -> str:
    """Opaque 256-bit token; only its hash is stored."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class _Ticket:
    user_id: uuid.UUID
    expires_at: datetime


class WsTicketStore:
    """Single-use WebSocket tickets kept in this API process's memory (02 §5).

    A ticket only works on the process that issued it; that is acceptable while the API runs as
    one process, and the WebSocket endpoint (T-026) consumes it.
    """

    def __init__(self, ttl_seconds: int = WS_TICKET_TTL_SECONDS) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._tickets: dict[str, _Ticket] = {}

    @property
    def ttl_seconds(self) -> int:
        return int(self._ttl.total_seconds())

    def issue(self, user_id: uuid.UUID, now: datetime) -> str:
        self._prune(now)
        ticket = WS_TICKET_PREFIX + secrets.token_urlsafe(24)
        self._tickets[ticket] = _Ticket(user_id, now + self._ttl)
        return ticket

    def consume(self, ticket: str, now: datetime) -> uuid.UUID | None:
        """The ticket's user if it is known and unexpired. A ticket works once."""
        entry = self._tickets.pop(ticket, None)
        if entry is None or entry.expires_at <= now:
            return None
        return entry.user_id

    def clear(self) -> None:
        self._tickets.clear()

    def _prune(self, now: datetime) -> None:
        for key in [k for k, t in self._tickets.items() if t.expires_at <= now]:
            del self._tickets[key]


ws_tickets = WsTicketStore()
