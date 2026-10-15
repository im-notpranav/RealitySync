"""Pair features (03 §M3 step 2). Each is a similarity in [0, 1], or `None` when the data it
needs is missing on either side (missing data neither helps nor hurts the score)."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

from app.domain.normalize import expand_nickname


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


@dataclass(frozen=True, slots=True)
class AccountIdentity:
    """The identity fields of one account record, from its `normalized` JSON (D-067)."""

    system: str
    external_id: str
    name: str | None = None
    email_canonical: str | None = None
    email_domain: str | None = None
    phone_e164: str | None = None
    company: str | None = None
    external_refs: Mapping[str, Any] | None = None

    @classmethod
    def from_normalized(
        cls, system: str, external_id: str, normalized: Mapping[str, Any]
    ) -> "AccountIdentity":
        refs = normalized.get("external_refs")
        return cls(
            system=system,
            external_id=external_id,
            name=_text(normalized.get("name")),
            email_canonical=_text(normalized.get("email_canonical")),
            email_domain=_text(normalized.get("email_domain")),
            phone_e164=_text(normalized.get("phone_e164")),
            company=_text(normalized.get("company")),
            external_refs=refs if isinstance(refs, Mapping) and refs else None,
        )


def email_exact(a: AccountIdentity, b: AccountIdentity) -> float | None:
    if a.email_canonical is None or b.email_canonical is None:
        return None
    return 1.0 if a.email_canonical == b.email_canonical else 0.0


def email_local_sim(a: AccountIdentity, b: AccountIdentity) -> float | None:
    """Jaro-Winkler of the local parts, only when both emails are on the same domain."""
    if a.email_canonical is None or b.email_canonical is None:
        return None
    local_a, _, domain_a = a.email_canonical.rpartition("@")
    local_b, _, domain_b = b.email_canonical.rpartition("@")
    if domain_a != domain_b or not local_a or not local_b:
        return None
    return float(JaroWinkler.similarity(local_a, local_b))


def phone_exact(a: AccountIdentity, b: AccountIdentity) -> float | None:
    if a.phone_e164 is None or b.phone_e164 is None:
        return None
    return 1.0 if a.phone_e164 == b.phone_e164 else 0.0


def _expanded(name: str) -> str:
    return " ".join(expand_nickname(token) for token in name.split())


def name_sim(a: AccountIdentity, b: AccountIdentity) -> float | None:
    """Token-sort ratio of the names with nicknames expanded (D-068).

    03 §M3 first said max(token-sort ratio, Jaro-Winkler). Jaro-Winkler of whole names scores
    unrelated names around 0.55 and different first names with a shared surname around 0.80,
    which auto-linked family members on a shared phone and colleagues on a shared mailbox.
    """
    if a.name is None or b.name is None:
        return None
    return float(fuzz.token_sort_ratio(_expanded(a.name), _expanded(b.name)) / 100)


def company_sim(a: AccountIdentity, b: AccountIdentity) -> float | None:
    if a.company is None or b.company is None:
        return None
    return float(fuzz.token_set_ratio(a.company, b.company) / 100)


def _ref_to(refs: Mapping[str, Any] | None, system: str) -> str | None:
    """The id `refs` holds for `system`, under the key `<system>_id` or `<system>` (D-068)."""
    if refs is None:
        return None
    for key in (f"{system}_id", system):
        value = refs.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def external_ref(a: AccountIdentity, b: AccountIdentity) -> float | None:
    """1 when one side names the other's id, or both carry the same reference; 0 when a
    reference points elsewhere; `None` when neither side refers to the other's system."""
    verdicts: list[bool] = []
    for this, other in ((a, b), (b, a)):
        ref = _ref_to(this.external_refs, other.system)
        if ref is not None:
            verdicts.append(ref == other.external_id)
    if a.external_refs and b.external_refs:
        for key in a.external_refs.keys() & b.external_refs.keys():
            left, right = a.external_refs[key], b.external_refs[key]
            if left is not None and right is not None and str(left).strip():
                verdicts.append(str(left).strip() == str(right).strip())
    if not verdicts:
        return None
    return 1.0 if any(verdicts) else 0.0


FEATURES = {
    "email_exact": email_exact,
    "email_local_sim": email_local_sim,
    "phone_exact": phone_exact,
    "name_sim": name_sim,
    "company_sim": company_sim,
    "external_ref": external_ref,
}
