"""Phone numbers (03 §M2, FR-NRM-003)."""

from dataclasses import dataclass

import phonenumbers


@dataclass(frozen=True, slots=True)
class NormalizedPhone:
    """`e164` is `None` when the value is not a valid number; `raw` is always kept."""

    e164: str | None
    raw: str

    @property
    def valid(self) -> bool:
        return self.e164 is not None


def normalize_phone(value: str | None, region: str) -> NormalizedPhone | None:
    """Parse to E.164 using `region` for numbers without a country code.

    `"098765 43210"` with region `IN` → `+919876543210`. The caller passes the configured
    region (`DEFAULT_PHONE_REGION`); the domain never reads settings. `None` when missing.
    """
    if value is None or not value.strip():
        return None
    raw = value.strip()
    try:
        number = phonenumbers.parse(raw, region.upper())
    except phonenumbers.NumberParseException:
        return NormalizedPhone(e164=None, raw=raw)
    if not phonenumbers.is_valid_number(number):
        return NormalizedPhone(e164=None, raw=raw)
    e164 = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
    return NormalizedPhone(e164=e164, raw=raw)
