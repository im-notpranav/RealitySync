"""Entity matching (03 §M3): which account records describe the same customer. Pure: no I/O,
settings, clock or randomness. Inputs are the `normalized` JSON of account records (D-067).
"""

from app.domain.matching.blocking import BLOCKING_FIELDS, blocking_keys, share_a_block
from app.domain.matching.features import AccountIdentity
from app.domain.matching.primary import LinkedAccount, split_primary
from app.domain.matching.scorer import (
    AUTO_MATCHED,
    NEEDS_REVIEW,
    NO_LINK,
    THIN_EVIDENCE_CAP,
    THIN_EVIDENCE_WEIGHT,
    WEIGHTS,
    Decision,
    MatchScore,
    decide,
    score_pair,
)

__all__ = [
    "AUTO_MATCHED",
    "BLOCKING_FIELDS",
    "NEEDS_REVIEW",
    "NO_LINK",
    "THIN_EVIDENCE_CAP",
    "THIN_EVIDENCE_WEIGHT",
    "WEIGHTS",
    "AccountIdentity",
    "Decision",
    "LinkedAccount",
    "MatchScore",
    "blocking_keys",
    "decide",
    "score_pair",
    "share_a_block",
    "split_primary",
]
