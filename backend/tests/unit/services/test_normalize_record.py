"""The `normalized` JSON built from a raw payload (03 §M2, T-012)."""

from typing import Any

import pytest

from app.db.seed import default_status_mapping
from app.services.record_service import (
    InvalidRecord,
    changed_fields,
    normalize_record,
    record_hash,
)

KEYS = {
    "account": {
        "name",
        "name_block",
        "email",
        "email_canonical",
        "email_domain",
        "phone_e164",
        "company",
        "plan",
        "created_at",
        "external_refs",
    },
    "subscription": {"plan", "started_at", "cancelled_at", "quantity", "amount", "currency"},
    "invoice": {"issued_at", "paid_at", "due_at", "subscription_external_id", "amount", "currency"},
    "ticket": {"subject", "priority", "opened_at", "closed_at", "first_response_at"},
}
COMMON = {"status", "status_unmapped", "parent_external_id"}


def normalize(
    record_type: str, payload: dict[str, Any], system: str = "crm", parent: str | None = None
) -> dict[str, Any]:
    return normalize_record(
        record_type,
        payload,
        parent_external_id=parent,
        status_mapping=default_status_mapping(system),
        phone_region="IN",
    )


def test_the_documented_account() -> None:
    normalized = normalize(
        "account",
        {
            "name": "Jon Smith",
            "email": "Jon.Smith@Example.com",
            "phone": "098765 43210",
            "status": "Customer",
            "plan": "Pro",
            "company": "Acme  Pvt Ltd",
            "created_at": "2025-11-02T15:30:00+05:30",
            "external_refs": {"billing_id": "B-5521"},
        },
    )

    assert normalized == {
        "name": "jon smith",
        "name_block": "SM0:j",
        "email": "jon.smith@example.com",
        "email_canonical": "jon.smith@example.com",
        "email_domain": "example.com",
        "phone_e164": "+919876543210",
        "company": "acme pvt ltd",
        "plan": "pro",
        "created_at": "2025-11-02T10:00:00Z",
        "external_refs": {"billing_id": "B-5521"},
        "status": "active",
        "status_unmapped": False,
        "parent_external_id": None,
    }


def test_the_documented_subscription() -> None:
    normalized = normalize(
        "subscription",
        {
            "plan": "pro",
            "status": "canceled",
            "amount": "1299.00",
            "currency": "inr",
            "started_at": "2025-11-02T10:00:00Z",
            "cancelled_at": "2026-08-02T10:15:00Z",
        },
        system="billing",
        parent="B-5521",
    )

    assert normalized == {
        "plan": "pro",
        "started_at": "2025-11-02T10:00:00Z",
        "cancelled_at": "2026-08-02T10:15:00Z",
        "quantity": None,
        "amount": "1299.00",
        "currency": "INR",
        "status": "cancelled",
        "status_unmapped": False,
        "parent_external_id": "B-5521",
    }


def test_invoices_and_tickets() -> None:
    invoice = normalize(
        "invoice",
        {"amount": "₹1,299", "status": "paid", "issued_at": 1760000000, "paid_at": None},
        system="billing",
        parent="B-1",
    )
    ticket = normalize(
        "ticket",
        {
            "subject": "  Invoice\tquestion ",
            "status": "Open",
            "opened_at": "2026-10-01T00:00:00Z",
            "priority": "P1",
        },
        system="support",
        parent="S-1",
    )

    assert (invoice["amount"], invoice["currency"], invoice["status"]) == ("1299.00", "INR", "paid")
    assert (invoice["issued_at"], invoice["paid_at"]) == ("2025-10-09T08:53:20Z", None)
    assert (ticket["subject"], ticket["priority"], ticket["status"]) == (
        "Invoice question",
        "urgent",
        "open",
    )


@pytest.mark.parametrize("record_type", sorted(KEYS))
def test_every_key_is_always_present(record_type: str) -> None:
    normalized = normalize(record_type, {})

    assert normalized.keys() == KEYS[record_type] | COMMON
    assert normalized["status_unmapped"] is False
    assert all(v is None for k, v in normalized.items() if k != "status_unmapped")


def test_unknown_statuses_are_flagged() -> None:
    normalized = normalize("account", {"status": "Platinum VIP"})

    assert (normalized["status"], normalized["status_unmapped"]) == (None, True)


def test_unreadable_values_become_none() -> None:
    normalized = normalize(
        "account", {"email": "not-an-email", "phone": "12", "plan": "gold", "external_refs": []}
    )

    assert normalized["email"] is None
    assert normalized["phone_e164"] is None
    assert normalized["plan"] is None
    assert normalized["external_refs"] is None


def test_unknown_payload_keys_are_ignored() -> None:
    assert normalize("account", {"name": "Jon", "favourite_colour": "teal"}) == normalize(
        "account", {"name": "Jon"}
    )


@pytest.mark.parametrize(
    ("record_type", "payload", "field"),
    [
        ("account", {"created_at": "2025-11-02 10:00"}, "created_at"),
        ("subscription", {"amount": "12,34", "currency": "INR"}, "amount"),
        ("invoice", {"amount": "10.00"}, "amount"),  # no currency
        ("ticket", {"opened_at": True}, "opened_at"),
    ],
)
def test_unreadable_timestamps_and_amounts_name_the_field_only(
    record_type: str, payload: dict[str, Any], field: str
) -> None:
    with pytest.raises(InvalidRecord) as caught:
        normalize(record_type, payload)

    assert str(caught.value) == f"payload.{field} is invalid"


def test_the_hash_ignores_key_order() -> None:
    assert record_hash({"a": 1, "b": None}) == record_hash({"b": None, "a": 1})
    assert record_hash({"a": 1}) != record_hash({"a": 2})


def test_changed_fields() -> None:
    assert changed_fields(None, {"name": "jon", "email": None}) == ["name"]
    assert changed_fields({"name": "jon", "plan": "pro"}, {"name": "jon", "plan": "starter"}) == [
        "plan"
    ]
    assert changed_fields({"a": 1}, {"b": 1}) == ["a", "b"]
