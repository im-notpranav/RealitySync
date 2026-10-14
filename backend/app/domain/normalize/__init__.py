"""Normalization (03 §M2): pure, deterministic functions from messy source values to comparable
canonical forms. No I/O, settings, clock or randomness (FR-NRM-006).

Missing input (`None`, blank) gives `None`. Values that cannot be read give `None` for names,
emails, plans and priorities, a flagged result for phones (`e164 is None`) and statuses
(`unmapped`), and raise `InvalidTimestamp` / `InvalidAmount` (both `ValueError`) for timestamps
and amounts, which ingest rejects with `VALIDATION_ERROR`.
"""

from app.domain.normalize.amounts import InvalidAmount, NormalizedAmount, normalize_amount
from app.domain.normalize.emails import NormalizedEmail, normalize_email
from app.domain.normalize.names import NormalizedName, name_block, normalize_name
from app.domain.normalize.nicknames import NICKNAMES, expand_nickname, nicknames_for
from app.domain.normalize.phones import NormalizedPhone, normalize_phone
from app.domain.normalize.plans import PLAN_CATALOG, PLANS, Plan, normalize_plan
from app.domain.normalize.statuses import (
    CANONICAL_STATUSES,
    PRIORITIES,
    NormalizedStatus,
    normalize_priority,
    normalize_status,
)
from app.domain.normalize.timestamps import InvalidTimestamp, normalize_ts

__all__ = [
    "CANONICAL_STATUSES",
    "NICKNAMES",
    "PLANS",
    "PLAN_CATALOG",
    "PRIORITIES",
    "InvalidAmount",
    "InvalidTimestamp",
    "NormalizedAmount",
    "NormalizedEmail",
    "NormalizedName",
    "NormalizedPhone",
    "NormalizedStatus",
    "Plan",
    "expand_nickname",
    "name_block",
    "nicknames_for",
    "normalize_amount",
    "normalize_email",
    "normalize_name",
    "normalize_phone",
    "normalize_plan",
    "normalize_priority",
    "normalize_status",
    "normalize_ts",
]
