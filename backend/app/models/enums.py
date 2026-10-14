"""Text enumerations shared by several tables (05 conventions: `text` + `CHECK`)."""

from collections.abc import Iterable

SYSTEM_KEYS = ("crm", "billing", "support")
RECORD_TYPES = ("account", "subscription", "invoice", "ticket")
SEVERITIES = ("low", "medium", "high", "critical")
RISK_LEVELS = ("low", "watch", "warning", "critical")


def one_of(column: str, values: Iterable[str]) -> str:
    """SQL for a `CHECK (column IN (...))`; a tuple's repr breaks for one value (`('a',)`)."""
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def between_0_and_1(column: str) -> str:
    return f"{column} >= 0 AND {column} <= 1"
