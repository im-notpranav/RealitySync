"""Plain helpers shared by the ingest and API key tests (T-011)."""

import copy
import hashlib
import json
from typing import Any

# The two events of the 04 §5 request example.
ACCOUNT_EVENT: dict[str, Any] = {
    "source": "crm",
    "record_type": "account",
    "external_id": "C-1042",
    "event_type": "upsert",
    "source_updated_at": "2026-10-08T09:58:00Z",
    "idempotency_key": None,
    "payload": {
        "name": "Jon Smith",
        "email": "Jon.Smith@Example.com",
        "phone": "098765 43210",
        "status": "Customer",
        "plan": "Pro",
        "company": "Acme Pvt Ltd",
        "created_at": "2025-11-02T10:00:00Z",
    },
}
SUBSCRIPTION_EVENT: dict[str, Any] = {
    "source": "billing",
    "record_type": "subscription",
    "external_id": "SUB-7781",
    "parent_external_id": "B-5521",
    "event_type": "upsert",
    "source_updated_at": "2026-10-08T09:59:00Z",
    "payload": {
        "plan": "pro",
        "status": "canceled",
        "amount": "1299.00",
        "currency": "INR",
        "started_at": "2025-11-02T10:00:00Z",
        "cancelled_at": "2026-08-02T10:15:00Z",
    },
}
INVOICE_EVENT: dict[str, Any] = {
    "source": "billing",
    "record_type": "invoice",
    "external_id": "INV-1",
    "parent_external_id": "B-5521",
    "event_type": "upsert",
    "source_updated_at": "2026-10-08T10:00:00Z",
    "payload": {
        "amount": "1299.00",
        "currency": "INR",
        "status": "paid",
        "issued_at": "2026-10-01T00:00:00Z",
    },
}
TICKET_EVENT: dict[str, Any] = {
    "source": "support",
    "record_type": "ticket",
    "external_id": "T-1",
    "parent_external_id": "S-77",
    "event_type": "upsert",
    "source_updated_at": "2026-10-08T10:01:00Z",
    "payload": {"subject": "Cannot log in", "status": "open", "opened_at": "2026-10-08T10:00:00Z"},
}
EVENTS_BY_TYPE = {
    "account": ACCOUNT_EVENT,
    "subscription": SUBSCRIPTION_EVENT,
    "invoice": INVOICE_EVENT,
    "ticket": TICKET_EVENT,
}


def event(base: dict[str, Any] = ACCOUNT_EVENT, **changes: Any) -> dict[str, Any]:
    """A deep copy of `base`; `payload__<field>` keys change one payload field (None removes)."""
    result = copy.deepcopy(base)
    for key, value in changes.items():
        if key.startswith("payload__"):
            field = key.removeprefix("payload__")
            if value is None:
                result["payload"].pop(field, None)
            else:
                result["payload"][field] = value
        else:
            result[key] = value
    return result


def expected_idempotency_key(e: dict[str, Any], recorded_utc: str) -> str:
    """03 §M1, written out independently of the service."""
    payload = json.dumps(e["payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    payload_hash = hashlib.sha256(payload.encode()).hexdigest()
    parts = [e["source"], e["record_type"], e["external_id"], e["event_type"], recorded_utc]
    return hashlib.sha256("|".join([*parts, payload_hash]).encode()).hexdigest()


def api_key(secret: str) -> dict[str, str]:
    return {"X-API-Key": secret}
