"""Timestamps and amounts (03 §M2; FR-NRM-004)."""

from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from app.domain.normalize import (
    InvalidAmount,
    InvalidTimestamp,
    NormalizedAmount,
    normalize_amount,
    normalize_ts,
)

IST = timezone(timedelta(hours=5, minutes=30))
NOON_UTC = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
NOON_EPOCH = 1792065600

# ---------------------------------------------------------------------------- timestamps


@pytest.mark.parametrize(
    "raw",
    [
        "2026-10-15T12:00:00Z",
        "2026-10-15T12:00:00+00:00",
        "2026-10-15T17:30:00+05:30",
        "2026-10-15 12:00:00.000+00:00",
        "20261015T120000Z",  # ISO 8601 basic format
        " 2026-10-15T08:00:00-04:00 ",
        datetime(2026, 10, 15, 17, 30, tzinfo=IST),
        NOON_EPOCH,  # epoch seconds are UTC
        float(NOON_EPOCH),
    ],
)
def test_timestamps_become_aware_utc(raw: Any) -> None:
    result = normalize_ts(raw)

    assert result == NOON_UTC
    assert result is not None and result.utcoffset() == timedelta(0)


def test_fractional_epoch_seconds() -> None:
    assert normalize_ts(NOON_EPOCH + 0.25) == NOON_UTC + timedelta(milliseconds=250)


def test_none_stays_none() -> None:
    assert normalize_ts(None) is None


@pytest.mark.parametrize(
    "raw",
    [
        "2026-10-15T12:00:00",  # naive string
        "2026-10-15",  # a date has no offset either
        datetime(2026, 10, 15, 12, 0),  # noqa: DTZ001 - naive on purpose
    ],
)
def test_naive_timestamps_are_rejected(raw: Any) -> None:
    with pytest.raises(InvalidTimestamp, match="time zone"):
        normalize_ts(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "26-10-15T12:00:00Z",  # two-digit year
        "15/10/26 12:00",
        "10/15/2026",
        "yesterday",
        "",
        "2026-13-45T12:00:00Z",
        "２０２６-10-15T12:00:00Z",  # full-width digits
    ],
)
def test_unreadable_timestamps_are_rejected(raw: str) -> None:
    with pytest.raises(InvalidTimestamp):
        normalize_ts(raw)


@pytest.mark.parametrize("raw", [True, float("nan"), float("inf"), 10**20, date(2026, 10, 15)])
def test_wrong_types_and_ranges_are_rejected(raw: Any) -> None:
    with pytest.raises(InvalidTimestamp):
        normalize_ts(raw)


def test_invalid_timestamp_is_a_value_error() -> None:
    assert issubclass(InvalidTimestamp, ValueError)


# ------------------------------------------------------------------------------- amounts


@pytest.mark.parametrize(
    ("raw", "currency", "expected"),
    [
        ("₹1,299.00", None, ("1299.00", "INR")),  # the 03 §M2 example
        ("₹1,299.00", "inr", ("1299.00", "INR")),
        ("1299", "INR", ("1299.00", "INR")),
        ("1,29,900.5", "INR", ("129900.50", "INR")),  # Indian digit grouping
        ("129,900.50", "INR", ("129900.50", "INR")),
        ("1,234,567", "INR", ("1234567.00", "INR")),
        ("Rs. 499", None, ("499.00", "INR")),
        ("INR 4999.00", None, ("4999.00", "INR")),
        ("$12.345", None, ("12.35", "USD")),  # rounded half-up
        ("-499.00", "INR", ("-499.00", "INR")),  # refunds
        (Decimal(1299), "INR", ("1299.00", "INR")),
        (1299, "INR", ("1299.00", "INR")),
        (0.1, "INR", ("0.10", "INR")),
        ("0.005", "INR", ("0.01", "INR")),
    ],
)
def test_normalize_amount(raw: Any, currency: str | None, expected: tuple[str, str]) -> None:
    amount, code = expected

    assert normalize_amount(raw, currency) == NormalizedAmount(Decimal(amount), code)


def test_none_amount_stays_none() -> None:
    assert normalize_amount(None, "INR") is None


@pytest.mark.parametrize(
    ("raw", "currency", "message"),
    [
        ("1.299,00", "INR", "not a number"),  # comma decimals are not guessed
        ("12,34", "INR", "not a number"),
        ("1,2,3", "INR", "not a number"),
        ("abc", "INR", "not a number"),
        ("", "INR", "not a number"),
        ("💰100", "INR", "not a number"),
        ("١٢٣", "INR", "not a number"),  # Arabic-Indic digits are not guessed either
        ("1299", None, "currency is required"),
        ("1299", "rupees", "three-letter"),
        ("1299", "₹", "three-letter"),
        ("$100", "INR", "does not match"),
        (True, "INR", "boolean"),
        (Decimal("NaN"), "INR", "finite"),
        (float("inf"), "INR", "finite"),
        ([1299], "INR", "unsupported"),
    ],
)
def test_invalid_amounts_are_rejected(raw: Any, currency: str | None, message: str) -> None:
    with pytest.raises(InvalidAmount, match=message):
        normalize_amount(raw, currency)
