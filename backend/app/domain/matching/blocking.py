"""Blocking (03 §M3 step 1, FR-ENT-002): only accounts sharing a key are compared.

Keys come from every system, the record's own included (same-system duplicates, R012).
"""

from collections.abc import Mapping
from typing import Any

# The normalized fields that are blocking keys; 05 §2.6 indexes each of them.
BLOCKING_FIELDS = ("email_canonical", "phone_e164", "name_block")


def blocking_keys(normalized: Mapping[str, Any]) -> tuple[str, ...]:
    """`field:value` for every blocking field the record has, sorted.

    Sorted, so callers that lock on the keys always take the locks in the same order (02 §3.3,
    concurrency rule 2).
    """
    return tuple(
        sorted(
            f"{field}:{value}"
            for field in BLOCKING_FIELDS
            if isinstance(value := normalized.get(field), str) and value
        )
    )


def share_a_block(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    return bool(set(blocking_keys(a)) & set(blocking_keys(b)))
