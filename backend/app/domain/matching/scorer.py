"""Pair score and link decision (03 §M3 steps 2–3, FR-ENT-003/004/009)."""

from dataclasses import dataclass, field
from typing import Literal

from app.domain.matching.features import FEATURES, AccountIdentity

WEIGHTS = {
    "email_exact": 0.40,
    "email_local_sim": 0.05,
    "phone_exact": 0.20,
    "name_sim": 0.25,
    "company_sim": 0.05,
    "external_ref": 0.05,
}
# Below this much available weight the evidence is thin: the score is capped under review.
THIN_EVIDENCE_WEIGHT = 0.4
THIN_EVIDENCE_CAP = 0.59
_DIGITS = 4  # stored scores and features (stable `match_features`, no float noise)

Decision = Literal["auto_matched", "needs_review", "no_link"]
AUTO_MATCHED: Decision = "auto_matched"
NEEDS_REVIEW: Decision = "needs_review"
NO_LINK: Decision = "no_link"


@dataclass(frozen=True)
class MatchScore:
    """`features` holds the available features only (the link's `match_features`)."""

    score: float
    features: dict[str, float] = field(default_factory=dict)
    available_weight: float = 0.0
    shortcut: bool = False  # an equal external reference decided the score


def score_pair(a: AccountIdentity, b: AccountIdentity) -> MatchScore:
    """Weighted feature similarity, re-normalized by the weight of the features available on
    both sides; capped at 0.59 when that weight is below 0.4; 1.0 on an equal external ref."""
    features = {
        name: round(value, _DIGITS)
        for name, feature in FEATURES.items()
        if (value := feature(a, b)) is not None
    }
    available = round(sum(WEIGHTS[name] for name in features), _DIGITS)
    if features.get("external_ref") == 1.0:
        return MatchScore(score=1.0, features=features, available_weight=available, shortcut=True)
    if available == 0:
        return MatchScore(score=0.0, features=features, available_weight=0.0)
    score = sum(WEIGHTS[name] * value for name, value in features.items()) / available
    if available < THIN_EVIDENCE_WEIGHT:
        score = min(score, THIN_EVIDENCE_CAP)
    return MatchScore(score=round(score, _DIGITS), features=features, available_weight=available)


def decide(score: float, *, auto: float, review: float) -> Decision:
    """`MATCH_AUTO` / `MATCH_REVIEW` come from settings, passed in by the caller."""
    if score >= auto:
        return AUTO_MATCHED
    if score >= review:
        return NEEDS_REVIEW
    return NO_LINK
