"""Statuses, ticket priorities and plans (03 §M2; FR-NRM-005)."""

from decimal import Decimal

import pytest

from app.db.seed import CANONICAL_STATUSES as SEEDED_STATUSES
from app.db.seed import default_status_mapping
from app.domain.normalize import (
    CANONICAL_STATUSES,
    PLAN_CATALOG,
    PLANS,
    NormalizedStatus,
    normalize_plan,
    normalize_priority,
    normalize_status,
)

CRM = default_status_mapping("crm")
BILLING = default_status_mapping("billing")
SUPPORT = default_status_mapping("support")
UNMAPPED = NormalizedStatus(value=None, unmapped=True)


def status(value: str | None) -> NormalizedStatus:
    return NormalizedStatus(value=value, unmapped=False)


# ------------------------------------------------------------------------------ statuses


@pytest.mark.parametrize(
    ("mapping", "record_type", "raw", "expected"),
    [
        (BILLING, "subscription", "canceled", "cancelled"),  # 03 §M2 examples
        (CRM, "account", "Customer", "active"),
        (CRM, "account", "  CUSTOMER ", "active"),
        (CRM, "account", "Former  Customer", "churned"),
        (BILLING, "subscription", "Past Due", "past_due"),
        (SUPPORT, "ticket", "On Hold", "pending"),
        (BILLING, "invoice", "paid", "paid"),
    ],
)
def test_statuses_map_to_the_canonical_vocabulary(
    mapping: dict[str, dict[str, str]], record_type: str, raw: str, expected: str
) -> None:
    assert normalize_status(mapping, record_type, raw) == status(expected)


def test_unknown_statuses_are_unmapped() -> None:
    assert normalize_status(CRM, "account", "VIP") == UNMAPPED
    assert normalize_status(CRM, "account", "😀") == UNMAPPED


def test_the_vocabulary_is_per_record_type() -> None:
    # `cancelled` is a subscription status, not an account status.
    assert normalize_status(BILLING, "account", "cancelled") == UNMAPPED
    assert normalize_status(BILLING, "subscription", "cancelled") == status("cancelled")


def test_a_misconfigured_mapping_never_leaks_a_non_canonical_value() -> None:
    mapping = {"account": {"gold": "vip", "ok": "active"}}

    assert normalize_status(mapping, "account", "gold") == UNMAPPED
    assert normalize_status(mapping, "account", "ok") == status("active")
    assert normalize_status({}, "account", "active") == UNMAPPED


@pytest.mark.parametrize("raw", [None, "", "  "])
def test_missing_statuses_are_none_but_not_unmapped(raw: str | None) -> None:
    assert normalize_status(CRM, "account", raw) == status(None)


def test_an_unknown_record_type_is_a_programming_error() -> None:
    with pytest.raises(ValueError, match="record type"):
        normalize_status(CRM, "contact", "active")


@pytest.mark.parametrize("mapping", [CRM, BILLING, SUPPORT])
def test_default_mappings_only_produce_canonical_statuses(
    mapping: dict[str, dict[str, str]],
) -> None:
    for record_type, values in mapping.items():
        for raw in values:
            result = normalize_status(mapping, record_type, raw)
            assert result.value in CANONICAL_STATUSES[record_type], (record_type, raw)


def test_seed_and_domain_share_one_vocabulary() -> None:
    """`app/db/seed.py` keeps its own copy of the vocabulary; it must not drift."""
    assert dict(SEEDED_STATUSES) == dict(CANONICAL_STATUSES)


# ---------------------------------------------------------------------------- priorities


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("P1", "urgent"),
        ("critical", "urgent"),
        ("p2", "high"),
        ("P3", "normal"),
        ("Medium", "normal"),
        ("p4", "low"),
        (" HIGH ", "high"),
        ("normal", "normal"),
        ("urgent", "urgent"),
        ("low", "low"),
    ],
)
def test_normalize_priority(raw: str, expected: str) -> None:
    assert normalize_priority(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "p5", "asap", "🔥"])
def test_unknown_priorities_are_none_never_high(raw: str | None) -> None:
    assert normalize_priority(raw) is None


# --------------------------------------------------------------------------------- plans


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("PRO plan", "pro"),  # the 03 §M2 example
        ("pro", "pro"),
        ("Professional", "pro"),
        ("  pro   plan ", "pro"),
        ("proplan", "pro"),
        ("Basic", "starter"),
        ("Starter Plan", "starter"),
        ("ENT", "enterprise"),
        ("enterprise plan", "enterprise"),
    ],
)
def test_normalize_plan(raw: str, expected: str) -> None:
    assert normalize_plan(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "gold", "pro max", "🚀"])
def test_unknown_plans_are_none(raw: str | None) -> None:
    assert normalize_plan(raw) is None


def test_plan_catalog_prices() -> None:
    assert {p.key: p.monthly_price_inr for p in PLANS} == {
        "starter": Decimal("499.00"),
        "pro": Decimal("1299.00"),
        "enterprise": Decimal("4999.00"),
    }
    assert PLAN_CATALOG["pro"].aliases == ("professional", "pro plan")
