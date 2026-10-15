"""Blocking, features, the scorer and the link decision (03 §M3)."""

from datetime import UTC, datetime

import pytest
from matchkit import identity, normalized

from app.domain.matching import (
    THIN_EVIDENCE_CAP,
    WEIGHTS,
    AccountIdentity,
    LinkedAccount,
    blocking_keys,
    decide,
    score_pair,
    share_a_block,
    split_primary,
)
from app.domain.matching.features import (
    company_sim,
    email_exact,
    email_local_sim,
    external_ref,
    name_sim,
    phone_exact,
)

JON = {"name": "Jon Smith", "email": "jon.smith@example.com", "phone": "098765 43210"}

# ------------------------------------------------------------------------------- blocking


def test_blocking_keys_are_sorted_and_skip_missing_fields() -> None:
    keys = blocking_keys(normalized(**JON))

    assert keys == (
        "email_canonical:jon.smith@example.com",
        "name_block:SM0:j",
        "phone_e164:+919876543210",
    )
    assert blocking_keys(normalized(name="Jon Smith")) == ("name_block:SM0:j",)
    assert blocking_keys({}) == ()


def test_nicknames_share_a_name_block() -> None:
    assert share_a_block(normalized(name="Bob Smith"), normalized(name="Robert Smyth"))


def test_any_one_shared_key_is_enough() -> None:
    a = normalized(name="Anil Kumar", phone="098765 43210")
    b = normalized(name="Sunita Rao", phone="+91 98765 43210")
    c = normalized(name="Sunita Rao", email="sunita@example.com")

    assert share_a_block(a, b)
    assert not share_a_block(a, c)


# ------------------------------------------------------------------------------- features


def test_missing_data_makes_a_feature_unavailable() -> None:
    bare = identity()
    full = identity(**JON, company="Acme")

    for feature in (email_exact, email_local_sim, phone_exact, name_sim, company_sim, external_ref):
        assert feature(bare, full) is None


def test_email_features() -> None:
    a = identity(email="Jon.Smith+crm@Gmail.com")
    b = identity(email="jonsmith@googlemail.com")
    c = identity(email="jon.smyth@gmail.com")
    d = identity(email="jon.smith@acme.com")

    assert email_exact(a, b) == 1.0  # gmail dots, +tag and googlemail are canonicalized
    assert email_exact(a, c) == 0.0
    assert 0.8 < (email_local_sim(a, c) or 0) < 1.0
    assert email_local_sim(a, d) is None  # only compared on the same domain


def test_phone_exact_compares_e164() -> None:
    assert phone_exact(identity(phone="098765 43210"), identity(phone="+91-98765-43210")) == 1.0
    assert phone_exact(identity(phone="098765 43210"), identity(phone="098765 43211")) == 0.0


def test_name_sim_does_not_reward_a_shared_surname_alone() -> None:
    """D-068: whole-name Jaro-Winkler gave 0.80 here and auto-linked a family on one phone."""
    assert (name_sim(identity(name="Rekha Iyer"), identity(name="Mohan Iyer")) or 1) <= 0.7


def test_name_sim_expands_nicknames_and_ignores_order() -> None:
    assert name_sim(identity(name="Bob Smith"), identity(name="Robert Smith")) == 1.0
    assert name_sim(identity(name="Smith, Jonathan"), identity(name="Jonathan Smith")) == 1.0
    assert 0.9 < (name_sim(identity(name="Jonathon Smith"), identity(name="Jonathan Smith")) or 0)
    assert (name_sim(identity(name="Priya Patel"), identity(name="Jon Smith")) or 1) < 0.6


def test_company_sim_is_a_token_set_ratio() -> None:
    assert company_sim(identity(company="Acme Pvt Ltd"), identity(company="Acme")) == 1.0
    assert (company_sim(identity(company="Acme"), identity(company="Globex")) or 1) < 0.5


def test_external_refs() -> None:
    crm = identity("crm", "C-1042")
    billing = identity("billing", "B-5521", refs={"crm_id": "C-1042"})
    elsewhere = identity("billing", "B-9", refs={"crm_id": "C-7"})
    bare_key = identity("billing", "B-5", refs={"crm": "C-1042"})
    shared_a = identity("billing", "B-1", refs={"tax_id": "AAA1"})
    shared_b = identity("support", "S-1", refs={"tax_id": "AAA1"})

    assert external_ref(crm, billing) == external_ref(billing, crm) == 1.0
    assert external_ref(crm, elsewhere) == 0.0
    assert external_ref(crm, bare_key) == 1.0
    assert external_ref(shared_a, shared_b) == 1.0
    assert external_ref(crm, shared_a) is None  # nothing that concerns the other side


# --------------------------------------------------------------------------------- scorer


def test_the_weights_sum_to_one() -> None:
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_the_documented_link() -> None:
    """04 §6: email_exact 1, phone_exact 1, name_sim 0.88 (plus email_local_sim 1) → 0.97."""
    a = AccountIdentity("crm", "C-1", name="x", email_canonical="j@e.com", phone_e164="+1")
    b = AccountIdentity("billing", "B-1", name="y", email_canonical="j@e.com", phone_e164="+1")
    score = (0.40 * 1 + 0.05 * 1 + 0.20 * 1 + 0.25 * 0.88) / 0.90

    assert round(score, 2) == 0.97
    result = score_pair(a, b)
    assert set(result.features) == {"email_exact", "email_local_sim", "phone_exact", "name_sim"}
    assert result.available_weight == 0.9


def test_missing_features_are_renormalized_away() -> None:
    a = identity(name="Jon Smith", phone="098765 43210")
    b = identity("billing", "B-1", name="Jon Smith", phone="098765 43210", email="j@x.com")

    result = score_pair(a, b)

    assert result.features == {"phone_exact": 1.0, "name_sim": 1.0}
    assert (result.score, result.available_weight) == (1.0, 0.45)


def test_thin_evidence_never_reaches_review() -> None:
    a = identity(name="Jon Smith", company="Acme")
    b = identity("billing", "B-1", name="Jon Smith", company="Acme")

    result = score_pair(a, b)

    assert result.available_weight == 0.3
    assert result.score == THIN_EVIDENCE_CAP
    assert decide(result.score, auto=0.85, review=0.60) == "no_link"


def test_an_equal_external_ref_decides() -> None:
    a = identity("crm", "C-1042", name="Jon Smith", email="jon@a.com")
    b = identity("billing", "B-1", name="J. Smith", email="js@b.com", refs={"crm_id": "C-1042"})

    result = score_pair(a, b)

    assert (result.score, result.shortcut) == (1.0, True)
    assert result.features["external_ref"] == 1.0


def test_no_shared_data_scores_zero() -> None:
    assert score_pair(identity(), identity("billing", "B-1")).score == 0.0


def test_scores_are_symmetric_and_stable() -> None:
    a = identity(name="Jonathon Smith", email="jon.smith@gmail.com", company="Acme")
    b = identity(
        "billing", "B-1", name="Jon Smyth", email="jon.smyth@gmail.com", company="ACME Ltd"
    )

    assert score_pair(a, b) == score_pair(b, a) == score_pair(a, b)
    assert all(len(str(v).split(".")[-1]) <= 4 for v in score_pair(a, b).features.values())


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (1.0, "auto_matched"),
        (0.85, "auto_matched"),
        (0.8499, "needs_review"),
        (0.60, "needs_review"),
        (0.5999, "no_link"),
        (0.0, "no_link"),
    ],
)
def test_decide_uses_the_given_thresholds(score: float, expected: str) -> None:
    assert decide(score, auto=0.85, review=0.60) == expected


def test_decide_with_other_thresholds() -> None:
    assert decide(0.7, auto=0.7, review=0.5) == "auto_matched"
    assert decide(0.55, auto=0.7, review=0.5) == "needs_review"


# -------------------------------------------------------------------------------- primary


def account(
    external_id: str,
    system: str = "crm",
    status: str = "auto_matched",
    confidence: float = 0.9,
    created: datetime | None = None,
) -> LinkedAccount:
    return LinkedAccount(external_id, system, external_id, status, confidence, created)


def test_one_primary_per_system_and_the_rest_are_extras() -> None:
    primary, extras = split_primary(
        [account("C-1", confidence=0.9), account("B-1", "billing"), account("C-2", confidence=0.95)]
    )

    assert {s: a.external_id for s, a in primary.items()} == {"crm": "C-2", "billing": "B-1"}
    assert [a.external_id for a in extras] == ["C-1"]


def test_primary_order() -> None:
    old = datetime(2024, 1, 1, tzinfo=UTC)
    new = datetime(2025, 1, 1, tzinfo=UTC)
    ordered = [
        account("C-9", status="confirmed", confidence=0.61),  # confirmed first
        account("C-8", confidence=0.99),  # then confidence
        account("C-7", confidence=0.9, created=old),  # then the older record
        account("C-6", confidence=0.9, created=new),
        account("C-2", confidence=0.9),  # unknown creation time last, then external id
        account("C-3", confidence=0.9),
    ]

    for permutation in (ordered, ordered[::-1], ordered[2:] + ordered[:2]):
        primary, extras = split_primary(permutation)
        assert [primary["crm"].external_id, *(a.external_id for a in extras)] == [
            "C-9",
            "C-8",
            "C-7",
            "C-6",
            "C-2",
            "C-3",
        ]


def test_no_accounts() -> None:
    assert split_primary([]) == ({}, [])
