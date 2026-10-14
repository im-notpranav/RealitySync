"""Timestamps (03 §M2, FR-NRM-004)."""

import math
import re
from datetime import UTC, datetime

# ISO 8601 with a four-digit year; "26-10-15" or "15/10/26" never reach the parser.
_ISO_PREFIX = re.compile(r"^[0-9]{4}-?[0-9]{2}")


class InvalidTimestamp(ValueError):
    """Not an aware ISO 8601 string, aware datetime or epoch seconds. Ingest answers with
    `VALIDATION_ERROR` (04 §1.5)."""


def normalize_ts(value: datetime | str | float | None) -> datetime | None:
    """An aware UTC datetime; `None` stays `None` (optional dates such as `due_at`).

    Accepts aware datetimes, ISO 8601 strings with an offset (`Z` included) and epoch seconds
    (taken as UTC). Naive values are rejected, never assumed to be UTC.
    """
    if value is None:
        return None
    if isinstance(value, bool):  # bool is an int subclass; True is not a timestamp
        raise InvalidTimestamp("expected a timestamp, got a boolean")
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, int | float):
        return _from_epoch(value)
    elif isinstance(value, str):
        parsed = _from_iso(value.strip())
    else:
        raise InvalidTimestamp(f"unsupported timestamp type: {type(value).__name__}")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InvalidTimestamp("timestamp has no time zone offset")
    return parsed.astimezone(UTC)


def _from_iso(text: str) -> datetime:
    if not _ISO_PREFIX.match(text):
        raise InvalidTimestamp("expected ISO 8601 with a four-digit year")
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise InvalidTimestamp("not an ISO 8601 timestamp") from exc


def _from_epoch(seconds: float) -> datetime:
    if isinstance(seconds, float) and not math.isfinite(seconds):
        raise InvalidTimestamp("epoch seconds must be finite")
    try:
        return datetime.fromtimestamp(seconds, UTC)
    except (OverflowError, OSError, ValueError) as exc:
        raise InvalidTimestamp("epoch seconds out of range") from exc
