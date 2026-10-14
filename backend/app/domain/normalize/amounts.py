"""Money amounts (03 §M2)."""

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_CENTS = Decimal("0.01")
_SYMBOLS = {"₹": "INR", "rs.": "INR", "rs": "INR", "$": "USD", "€": "EUR", "£": "GBP"}
# Plain digits, or digits grouped by commas: Western "129,900" or Indian "1,29,900" (the last
# group always has three digits). "1.299,00" and "12,34" (comma decimals) are rejected rather
# than misread.
_NUMBER = re.compile(
    r"^[+-]?([0-9]+|[0-9]{1,3}(,[0-9]{3})+|[0-9]{1,2}(,[0-9]{2})+,[0-9]{3})(\.[0-9]+)?$"
)
_CURRENCY = re.compile(r"^[A-Z]{3}$")


class InvalidAmount(ValueError):
    """Not a number, or the currency is missing, malformed or contradicts the symbol."""


@dataclass(frozen=True, slots=True)
class NormalizedAmount:
    amount: Decimal  # two decimal places
    currency: str  # ISO 4217 code


def normalize_amount(
    value: Decimal | float | str | None, currency: str | None
) -> NormalizedAmount | None:
    """`"₹1,299.00"` → `Decimal("1299.00")`, `INR`. `None` stays `None`.

    The currency comes from the record's `currency` field or, failing that, the symbol in the
    value; one of them is required. Amounts are rounded half-up to two decimals.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise InvalidAmount("expected an amount, got a boolean")
    symbol_currency: str | None = None
    if isinstance(value, str):
        text, symbol_currency = _strip_symbol(value.strip())
        if not _NUMBER.match(text):
            raise InvalidAmount("not a number")
        number = Decimal(text.replace(",", ""))
    elif isinstance(value, Decimal | int | float):
        # str() first, so 0.1 stays 0.1 instead of its binary expansion.
        number = Decimal(str(value))
    else:
        raise InvalidAmount(f"unsupported amount type: {type(value).__name__}")
    if not number.is_finite():
        raise InvalidAmount("amount must be finite")
    return NormalizedAmount(
        amount=number.quantize(_CENTS, rounding=ROUND_HALF_UP),
        currency=_currency(currency, symbol_currency),
    )


def _strip_symbol(text: str) -> tuple[str, str | None]:
    lowered = text.casefold()
    for symbol, code in _SYMBOLS.items():
        if lowered.startswith(symbol):
            return text[len(symbol) :].strip(), code
    if len(text) > 3 and text[:3].isalpha():  # "INR 1299", "usd1299"
        return text[3:].strip(), text[:3].upper()
    return text, None


def _currency(given: str | None, from_symbol: str | None) -> str:
    code = given.strip().upper() if given and given.strip() else from_symbol
    if code is None:
        raise InvalidAmount("currency is required")
    if not _CURRENCY.match(code):
        raise InvalidAmount("currency must be a three-letter ISO 4217 code")
    if from_symbol is not None and from_symbol != code:
        raise InvalidAmount("currency does not match the amount's symbol")
    return code
