"""Record statuses and ticket priorities (03 §M2, FR-NRM-005)."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# Canonical statuses per record type. Rules only ever see these values.
CANONICAL_STATUSES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "account": ("active", "inactive", "churned", "prospect"),
        "subscription": ("trialing", "active", "past_due", "cancelled"),
        "invoice": ("draft", "issued", "paid", "void", "refunded"),
        "ticket": ("open", "pending", "solved", "closed"),
    }
)

PRIORITIES = ("low", "normal", "high", "urgent")
_PRIORITY_ALIASES: Mapping[str, str] = MappingProxyType(
    {
        **{p: p for p in PRIORITIES},
        "p1": "urgent",
        "critical": "urgent",
        "p2": "high",
        "p3": "normal",
        "medium": "normal",
        "p4": "low",
    }
)


@dataclass(frozen=True, slots=True)
class NormalizedStatus:
    """`value` is canonical or `None`. `unmapped` marks a present value the mapping does not know;
    such a status never matches anything (03 §M2)."""

    value: str | None
    unmapped: bool


def _key(value: str) -> str:
    return " ".join(value.split()).casefold()


def normalize_status(
    status_mapping: Mapping[str, Mapping[str, str]], record_type: str, value: str | None
) -> NormalizedStatus:
    """Map a raw status through one system's `status_mapping` (`source_systems.status_mapping`).

    The mapping is `{record_type: {raw (lower case) → canonical}}` (D-058); the raw value is
    trimmed and case-folded before the lookup. A mapped value outside the record type's
    canonical vocabulary (a misconfigured mapping) counts as unmapped too.
    """
    if record_type not in CANONICAL_STATUSES:
        raise ValueError(f"unknown record type: {record_type!r}")
    if value is None or not value.strip():
        return NormalizedStatus(value=None, unmapped=False)
    canonical = status_mapping.get(record_type, {}).get(_key(value))
    if canonical not in CANONICAL_STATUSES[record_type]:
        return NormalizedStatus(value=None, unmapped=True)
    return NormalizedStatus(value=canonical, unmapped=False)


def normalize_priority(value: str | None) -> str | None:
    """Ticket priority: `low`, `normal`, `high` or `urgent`. Unknown or missing → `None`, never
    a guess such as `high`."""
    if value is None:
        return None
    return _PRIORITY_ALIASES.get(_key(value))
