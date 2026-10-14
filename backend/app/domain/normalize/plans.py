"""Plan catalog (03 §M2). Pure data: the single source for `normalize_plan`, the simulator's
generator (`simulation/catalog.py`), R006 and R014's default price table."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class Plan:
    key: str
    aliases: tuple[str, ...]
    monthly_price_inr: Decimal


PLANS: tuple[Plan, ...] = (
    Plan("starter", ("basic", "starter plan"), Decimal("499.00")),
    Plan("pro", ("professional", "pro plan"), Decimal("1299.00")),
    Plan("enterprise", ("ent", "enterprise plan"), Decimal("4999.00")),
)

PLAN_CATALOG: Mapping[str, Plan] = MappingProxyType({plan.key: plan for plan in PLANS})


def _key(value: str) -> str:
    # Case- and space-insensitive: "PRO plan", "pro  plan" and "proplan" are one name.
    return "".join(value.split()).casefold()


_LOOKUP: Mapping[str, str] = MappingProxyType(
    {_key(name): plan.key for plan in PLANS for name in (plan.key, *plan.aliases)}
)


def normalize_plan(value: str | None) -> str | None:
    """Canonical plan key, e.g. `"PRO plan"` → `pro`; unknown or missing → `None`."""
    if value is None:
        return None
    return _LOOKUP.get(_key(value))
