"""Primary account per system (03 §M3 step 4): derived, never stored.

Order: `confirmed` links first → higher `match_confidence` → older `source_created_at` (unknown
last) → lower `external_id` (→ record id, so the order is total). The first account of each
system is its primary; the rest are `extra_accounts` (duplicate candidates, R012).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class LinkedAccount:
    record_id: Any  # opaque here (a UUID in the services); only used as the last tie-break
    system: str
    external_id: str
    link_status: str  # auto_matched | needs_review | confirmed (rejected links never get here)
    match_confidence: float
    source_created_at: datetime | None


def _order(account: LinkedAccount) -> tuple[Any, ...]:
    created = account.source_created_at
    return (
        account.link_status != "confirmed",
        -account.match_confidence,
        created is None,
        created.timestamp() if created is not None else 0.0,
        account.external_id,
        str(account.record_id),
    )


def split_primary(
    accounts: Iterable[LinkedAccount],
) -> tuple[dict[str, LinkedAccount], list[LinkedAccount]]:
    """`(primary by system, extras)`; extras keep the same order."""
    primary: dict[str, LinkedAccount] = {}
    extras: list[LinkedAccount] = []
    for account in sorted(accounts, key=_order):
        if account.system in primary:
            extras.append(account)
        else:
            primary[account.system] = account
    return primary, extras
