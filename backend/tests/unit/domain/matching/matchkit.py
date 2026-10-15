"""Builds `AccountIdentity` values the way ingest does (normalize → identity fields)."""

from typing import Any

from app.domain.matching import AccountIdentity
from app.domain.normalize import name_block, normalize_email, normalize_name, normalize_phone


def normalized(
    name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    company: str | None = None,
    refs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    n = normalize_name(name)
    e = normalize_email(email)
    p = normalize_phone(phone, "IN")
    return {
        "name": n.full if n else None,
        "name_block": name_block(n) if n else None,
        "email_canonical": e.canonical if e else None,
        "email_domain": e.domain if e else None,
        "phone_e164": p.e164 if p else None,
        "company": " ".join(company.casefold().split()) if company else None,
        "external_refs": refs,
    }


def identity(system: str = "crm", external_id: str = "C-1", **fields: Any) -> AccountIdentity:
    return AccountIdentity.from_normalized(system, external_id, normalized(**fields))
