"""Names, nicknames and the name blocking key (03 §M2, §M3; FR-NRM-001)."""

import pytest

from app.domain.normalize import (
    NICKNAMES,
    NormalizedName,
    expand_nickname,
    name_block,
    nicknames_for,
    normalize_name,
)

# Invisible characters, spelled out so the source shows no hidden text.
RLM, LRM, ZWJ = chr(0x200F), chr(0x200E), chr(0x200D)


def full(value: str | None) -> str | None:
    name = normalize_name(value)
    return None if name is None else name.full


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Dr. Jonathan  SMITH Jr.", "jonathan smith"),  # the 03 §M2 example
        ("  ana   lópez ", "ana lópez"),
        ("MRS. MARY-JANE WATSON", "mary jane watson"),
        ("Seán O'Brien", "seán obrien"),
        ("Patrick O’Neil III", "patrick oneil"),
        ("Prof Dr Alan Turing PhD", "alan turing"),
        ("ＡＮＡ　ＬＯＰＥＺ", "ana lopez"),  # full-width letters and space (NFKC)
        ("Straße", "strasse"),  # case-folded, not just lower-cased
        ("Ana\tLopez\n", "ana lopez"),
    ],
)
def test_normalize_name(raw: str, expected: str) -> None:
    assert full(raw) == expected


def test_tokens_are_sorted_for_token_sort_comparison() -> None:
    a, b = normalize_name("Smith, Jonathan"), normalize_name("Jonathan Smith")

    assert a is not None and b is not None
    assert a.full == "smith jonathan"
    assert a.tokens == b.tokens == ("jonathan", "smith")
    assert a.sorted == "jonathan smith"


@pytest.mark.parametrize("raw", [None, "", "   ", "...", "👍🏽", RLM + LRM])
def test_empty_names_are_none(raw: str | None) -> None:
    assert normalize_name(raw) is None


def test_emoji_and_bidi_marks_are_removed() -> None:
    assert full("Ana 😀️ López") == "ana lópez"
    assert full(ZWJ.join("👨👩👧") + " Ana") == "ana"
    # Right-to-left text keeps its letters; the direction marks around it go.
    assert full(RLM + "محمد علي" + RLM) == "محمد علي"


def test_titles_and_suffixes_never_empty_a_name() -> None:
    assert full("Dr") == "dr"
    assert full("Mr Jr") == "jr"


def test_is_deterministic() -> None:
    assert normalize_name("Dr. Ana Lopez") == normalize_name("Dr. Ana Lopez")
    assert isinstance(normalize_name("Ana"), NormalizedName)


# ------------------------------------------------------------------------------ nicknames


@pytest.mark.parametrize(
    ("token", "expected"),
    [("jon", "jonathan"), ("bob", "robert"), ("liz", "elizabeth"), ("ana", "ana"), ("al", "al")],
)
def test_expand_nickname(token: str, expected: str) -> None:
    assert expand_nickname(token) == expected


def test_nickname_table_is_consistent() -> None:
    for nickname, canonical in NICKNAMES.items():
        assert nickname != canonical
        assert nickname == nickname.casefold()
        assert nickname in nicknames_for(canonical)
        # A nickname is never itself a canonical name, so expansion never chains.
        assert canonical not in NICKNAMES
    assert nicknames_for("ana") == ()


# ------------------------------------------------------------------------------ blocking


def block(raw: str) -> str:
    name = normalize_name(raw)
    assert name is not None
    return name_block(name)


def test_name_block_is_metaphone_of_last_token_and_first_initial() -> None:
    assert block("Jonathan Smith") == "SM0:j"
    assert block("Jon Smyth") == block("Jonathan Smith")


def test_name_block_expands_the_first_name() -> None:
    assert block("Bob Smith") == block("Robert Smith") == "SM0:r"


def test_name_block_uses_written_order_not_sorted_tokens() -> None:
    assert block("Ana Lopez") == "LPS:a"
    assert block("Lopez Ana") == "AN:l"


def test_name_block_for_one_token_and_non_latin_names() -> None:
    assert block("Cher") == "XR:c"
    # Metaphone has no code for Arabic letters, so the token itself is the key.
    assert block("محمد علي") == "علي:م"
