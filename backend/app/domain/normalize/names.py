"""Person names (03 §M2, FR-NRM-001)."""

import unicodedata
from dataclasses import dataclass

import jellyfish

from app.domain.normalize.nicknames import expand_nickname

TITLES = frozenset(
    {"mr", "mrs", "ms", "miss", "mx", "dr", "prof", "sir", "dame", "madam", "rev", "shri", "smt"}
)
SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "phd", "md", "esq"})

_APOSTROPHES = frozenset("'’ʼ`")  # O'Brien → obrien, not "o brien"


@dataclass(frozen=True, slots=True)
class NormalizedName:
    """`full` keeps the written order; `tokens` are sorted (token-sort comparison)."""

    full: str
    tokens: tuple[str, ...]

    @property
    def sorted(self) -> str:
        return " ".join(self.tokens)


def _clean_char(ch: str) -> str:
    if ch in _APOSTROPHES:
        return ""
    category = unicodedata.category(ch)
    if category == "Cf" or 0xFE00 <= ord(ch) <= 0xFE0F:
        return ""  # bidi marks, zero-width joiners, emoji variation selectors
    if category[0] in "PSZC":
        return " "  # punctuation, symbols (emoji), separators, control characters
    return ch


def normalize_name(value: str | None) -> NormalizedName | None:
    """NFKC, case-fold, drop titles / suffixes and punctuation, collapse spaces.

    `"Dr. Jonathan  SMITH Jr."` → `"jonathan smith"`. `None` when nothing is left.
    """
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", value).casefold()
    words = "".join(_clean_char(ch) for ch in text).split()
    # Titles lead, suffixes trail; a name made only of them is kept as written.
    while len(words) > 1 and words[0] in TITLES:
        words.pop(0)
    while len(words) > 1 and words[-1] in SUFFIXES:
        words.pop()
    if not words:
        return None
    return NormalizedName(full=" ".join(words), tokens=tuple(sorted(words)))


def name_block(name: NormalizedName) -> str:
    """Blocking key `metaphone(last token) + ':' + first initial` (03 §M3).

    The first token is nickname-expanded first, so "Bob Smith" and "Robert Smith" share a block.
    Metaphone only codes Latin letters; for other scripts the last token itself is used.
    """
    words = name.full.split()
    last = words[-1]
    first = expand_nickname(words[0])
    return f"{jellyfish.metaphone(last) or last}:{first[0]}"
