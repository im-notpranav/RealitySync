import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    JWT_ALGORITHM,
    WsTicketStore,
    create_access_token,
    decode_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)

NOW = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)
USER_ID = uuid.UUID("7c1e0000-0000-4000-8000-000000000001")


def test_password_hash_is_argon2id_and_verifies() -> None:
    hashed = hash_password("correct horse battery")

    assert hashed.startswith("$argon2id$")
    assert verify_password(hashed, "correct horse battery")
    assert not verify_password(hashed, "correct horse batter")


def test_verify_rejects_a_malformed_hash() -> None:
    assert not verify_password("not-a-hash", "anything")


def test_access_token_round_trip() -> None:
    token, expires_in = create_access_token(USER_ID, "analyst", NOW)

    claims = decode_access_token(token, NOW + timedelta(minutes=14))

    assert expires_in == settings.ACCESS_TOKEN_MINUTES * 60 == 900
    assert claims is not None
    assert (claims.user_id, claims.role) == (USER_ID, "analyst")
    assert claims.expires_at == NOW + timedelta(minutes=15)
    assert claims.jti


def test_access_token_carries_the_documented_claims() -> None:
    token, _ = create_access_token(USER_ID, "viewer", NOW)

    header = jwt.get_unverified_header(token)
    claims = jwt.decode(token, options={"verify_signature": False})

    assert header["alg"] == "HS256"
    assert {"sub", "role", "exp", "jti"} <= claims.keys()


def test_access_token_expires_after_15_minutes() -> None:
    token, _ = create_access_token(USER_ID, "admin", NOW)

    assert decode_access_token(token, NOW + timedelta(minutes=15)) is None


def test_each_access_token_has_its_own_jti() -> None:
    first, _ = create_access_token(USER_ID, "admin", NOW)
    second, _ = create_access_token(USER_ID, "admin", NOW)

    a, b = decode_access_token(first, NOW), decode_access_token(second, NOW)
    assert a is not None and b is not None
    assert a.jti != b.jti


@pytest.mark.parametrize(
    "token",
    [
        "garbage",
        jwt.encode(
            {"sub": str(USER_ID), "role": "admin", "exp": 4102444800, "jti": "x"},
            "wrong-secret-of-at-least-32-bytes!",
        ),
        jwt.encode({"sub": str(USER_ID), "role": "admin"}, settings.JWT_SECRET),
        jwt.encode(
            {"sub": "not-a-uuid", "role": "admin", "exp": 4102444800, "jti": "x"},
            settings.JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        ),
    ],
    ids=["malformed", "wrong-secret", "missing-claims", "bad-subject"],
)
def test_invalid_access_tokens_are_rejected(token: str) -> None:
    assert decode_access_token(token, NOW) is None


def test_none_algorithm_is_rejected() -> None:
    token = jwt.encode(
        {"sub": str(USER_ID), "role": "admin", "exp": 4102444800, "jti": "x"},
        key=None,
        algorithm="none",
    )

    assert decode_access_token(token, NOW) is None


def test_refresh_tokens_are_random_256_bit_and_hashed() -> None:
    first, second = new_refresh_token(), new_refresh_token()

    assert first != second
    assert len(first) >= 43  # 32 bytes, URL-safe base64
    assert hash_token(first) == hash_token(first)
    assert len(hash_token(first)) == 64
    assert hash_token(first) != first


def test_ws_ticket_is_single_use() -> None:
    store = WsTicketStore()
    ticket = store.issue(USER_ID, NOW)

    assert ticket.startswith("wst_")
    assert store.ttl_seconds == 60
    assert store.consume(ticket, NOW + timedelta(seconds=59)) == USER_ID
    assert store.consume(ticket, NOW + timedelta(seconds=59)) is None


def test_ws_ticket_expires_after_60_seconds() -> None:
    store = WsTicketStore()
    ticket = store.issue(USER_ID, NOW)

    assert store.consume(ticket, NOW + timedelta(seconds=60)) is None


def test_unknown_ws_ticket_is_rejected() -> None:
    assert WsTicketStore().consume("wst_unknown", NOW) is None


def test_issuing_prunes_expired_tickets() -> None:
    store = WsTicketStore()
    old = store.issue(USER_ID, NOW)
    store.issue(USER_ID, NOW + timedelta(seconds=61))

    assert store.consume(old, NOW) is None  # pruned, although `now` here is before its expiry
