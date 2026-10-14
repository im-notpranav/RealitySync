"""Startup bootstrap data (05 §6). Idempotent; never overwrites what an admin has edited."""

from typing import Any

import structlog
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import SourceSystem

log = structlog.get_logger(__name__)

# 03 §M1. The keys are exactly the documented ones; values are per system.
_AUTHORITY_GROUPS: dict[tuple[str, ...], dict[str, float]] = {
    ("name", "email", "phone", "company"): {"crm": 0.9, "billing": 0.6, "support": 0.4},
    ("status", "plan"): {"crm": 0.5, "billing": 0.95, "support": 0.2},
    ("amount", "invoice_dates"): {"crm": 0.2, "billing": 1.0, "support": 0.0},
    ("ticket",): {"crm": 0.0, "billing": 0.0, "support": 1.0},
}

# 03 §M2: canonical statuses per record type. Every canonical value maps to itself.
CANONICAL_STATUSES: dict[str, tuple[str, ...]] = {
    "account": ("active", "inactive", "churned", "prospect"),
    "subscription": ("trialing", "active", "past_due", "cancelled"),
    "invoice": ("draft", "issued", "paid", "void", "refunded"),
    "ticket": ("open", "pending", "solved", "closed"),
}

# Vocabulary each system uses besides the canonical words (03 §M2 examples: billing `canceled`,
# crm `Customer`). Keys are lower case: the lookup trims and case-folds the raw value (D-058).
_SYSTEM_SYNONYMS: dict[str, dict[str, dict[str, str]]] = {
    "crm": {
        "account": {"customer": "active", "lead": "prospect", "former customer": "churned"},
    },
    "billing": {
        "subscription": {"trial": "trialing", "canceled": "cancelled", "past due": "past_due"},
        "invoice": {"open": "issued", "voided": "void"},
    },
    "support": {
        "ticket": {"new": "open", "on hold": "pending", "resolved": "solved"},
    },
}

_NAMES = {"crm": "CRM", "billing": "Billing", "support": "Support"}


def default_field_authority(system_key: str) -> dict[str, float]:
    return {
        field: values[system_key]
        for fields, values in _AUTHORITY_GROUPS.items()
        for field in fields
    }


def default_status_mapping(system_key: str) -> dict[str, dict[str, str]]:
    """`{record_type: {raw status (lower case) → canonical status}}` for one system."""
    synonyms = _SYSTEM_SYNONYMS[system_key]
    return {
        record_type: {**{s: s for s in canonical}, **synonyms.get(record_type, {})}
        for record_type, canonical in CANONICAL_STATUSES.items()
    }


def default_source_systems() -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "name": name,
            "field_authority": default_field_authority(key),
            "status_mapping": default_status_mapping(key),
        }
        for key, name in _NAMES.items()
    ]


async def bootstrap_source_systems(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Create `crm`, `billing` and `support` when missing (05 §6).

    Existing rows are left untouched, so admin edits survive restarts. Skips with a warning,
    instead of stopping the API, when the database is not migrated yet.
    """
    try:
        async with session_factory() as session:
            result = await session.execute(
                insert(SourceSystem)
                .values(default_source_systems())
                .on_conflict_do_nothing(index_elements=["key"])
                .returning(SourceSystem.key)
            )
            created = sorted(result.scalars())
            await session.commit()
        if created:
            log.info("source_systems_bootstrapped", created=created)
    except (DBAPIError, OSError) as exc:
        log.warning("source_systems_bootstrap_skipped", reason=type(exc).__name__)
