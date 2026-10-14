"""Emails and phones (03 §M2; FR-NRM-002, FR-NRM-003)."""

import pytest

from app.domain.normalize import normalize_email, normalize_phone

# ------------------------------------------------------------------------------ emails


def test_gmail_dots_and_tags_are_ignored_for_matching_only() -> None:
    email = normalize_email("John.Smith+crm@Gmail.com")  # the 03 §M2 example

    assert email is not None
    assert email.display == "john.smith+crm@gmail.com"
    assert email.canonical == "johnsmith@gmail.com"
    assert email.domain == "gmail.com"
    assert email.local_part == "johnsmith"


def test_googlemail_is_gmail() -> None:
    a, b = normalize_email("j.smith@googlemail.com"), normalize_email("jsmith+x@gmail.com")

    assert a is not None and b is not None
    assert a.canonical == b.canonical == "jsmith@gmail.com"
    assert a.display == "j.smith@googlemail.com"


def test_other_domains_keep_dots_and_tags() -> None:
    email = normalize_email("  Ana.Lopez+billing@Example.COM ")

    assert email is not None
    assert email.display == email.canonical == "ana.lopez+billing@example.com"
    assert email.domain == "example.com"


def test_a_tag_only_gmail_address_keeps_its_local_part() -> None:
    email = normalize_email("+promo@gmail.com")

    assert email is not None
    assert email.canonical == "+promo@gmail.com"


def test_international_addresses_are_kept() -> None:
    email = normalize_email("Ünï@Exämple.com")

    assert email is not None
    assert email.canonical == "ünï@exämple.com"


@pytest.mark.parametrize(
    "raw", [None, "", "   ", "not-an-email", "a@b", "bad@@example.com", "ana@example"]
)
def test_missing_or_invalid_emails_are_none(raw: str | None) -> None:
    assert normalize_email(raw) is None


# ------------------------------------------------------------------------------ phones


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("098765 43210", "+919876543210"),  # the 03 §M2 example
        ("9876543210", "+919876543210"),
        ("+91 98765-43210", "+919876543210"),
        ("+1 (415) 555-2671", "+14155552671"),  # an explicit country code wins over the region
        ("+44 20 7946 0958", "+442079460958"),
    ],
)
def test_phones_are_e164(raw: str, expected: str) -> None:
    phone = normalize_phone(raw, "IN")

    assert phone is not None
    assert phone.e164 == expected
    assert phone.valid
    assert phone.raw == raw


def test_region_applies_to_numbers_without_a_country_code() -> None:
    phone = normalize_phone("(415) 555-2671", "us")

    assert phone is not None
    assert phone.e164 == "+14155552671"


@pytest.mark.parametrize("raw", ["12345", "abc", "+91 0000", "☎️ call me"])
def test_invalid_phones_keep_the_raw_value(raw: str) -> None:
    phone = normalize_phone(f" {raw} ", "IN")

    assert phone is not None
    assert phone.e164 is None
    assert not phone.valid
    assert phone.raw == raw


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_missing_phones_are_none(raw: str | None) -> None:
    assert normalize_phone(raw, "IN") is None
