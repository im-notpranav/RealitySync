"""Labeled account pairs (T-016 acceptance): recall ≥ 0.95 (auto + review) on true matches,
and no false auto-match. Each pair is (note, a, b, same customer?)."""

from dataclasses import dataclass
from typing import Any

import pytest
from matchkit import identity, normalized

from app.domain.matching import AccountIdentity, decide, score_pair, share_a_block

AUTO, REVIEW = 0.85, 0.60  # the 02 §8 defaults (MATCH_AUTO, MATCH_REVIEW)


@dataclass(frozen=True)
class Pair:
    note: str
    a: dict[str, Any]
    b: dict[str, Any]
    same: bool
    a_system: str = "crm"
    b_system: str = "billing"

    def identities(self) -> tuple[AccountIdentity, AccountIdentity]:
        b_id = "B-2" if self.b_system != self.a_system else "C-2"
        return (
            identity(self.a_system, "C-1", **self.a),
            identity(self.b_system, b_id, **self.b),
        )


def p(note: str, a: dict[str, Any], b: dict[str, Any], **kw: Any) -> Pair:
    return Pair(note, a, b, True, **kw)


def n(note: str, a: dict[str, Any], b: dict[str, Any], **kw: Any) -> Pair:
    return Pair(note, a, b, False, **kw)


E, PH = "email", "phone"
POSITIVES = [
    p(
        "identical",
        {"name": "Jon Smith", E: "jon.smith@example.com", PH: "098765 43210"},
        {"name": "Jon Smith", E: "jon.smith@example.com", PH: "098765 43210"},
    ),
    p(
        "email case and spaces",
        {"name": "Priya Sharma", E: " Priya.Sharma@Example.COM "},
        {"name": "Priya Sharma", E: "priya.sharma@example.com"},
    ),
    p(
        "gmail dots and +tag",
        {"name": "Rahul Verma", E: "Rahul.Verma+crm@Gmail.com"},
        {"name": "Rahul Verma", E: "rahulverma@gmail.com"},
    ),
    p(
        "googlemail alias",
        {"name": "Anita Desai", E: "anita.desai@googlemail.com"},
        {"name": "Anita Desai", E: "anitadesai@gmail.com"},
    ),
    p(
        "nickname Bob",
        {"name": "Bob Thomas", E: "bthomas@acme.com"},
        {"name": "Robert Thomas", E: "bthomas@acme.com"},
    ),
    p(
        "nickname Bill, no phone one side",
        {"name": "Bill Carter", E: "carter@globex.com", PH: "98200 11223"},
        {"name": "William Carter", E: "carter@globex.com"},
    ),
    p(
        "nickname Liz",
        {"name": "Liz Fernandes", E: "liz.f@example.org"},
        {"name": "Elizabeth Fernandes", E: "liz.f@example.org", PH: "98111 22334"},
    ),
    p(
        "nickname Jim + phone only",
        {"name": "Jim Brown", PH: "+91 99887 66554"},
        {"name": "James Brown", PH: "099887 66554"},
    ),
    p(
        "name typo",
        {"name": "Jonathon Smith", E: "jsmith@initech.com", PH: "98450 12345"},
        {"name": "Jonathan Smith", E: "jsmith@initech.com", PH: "98450 12345"},
    ),
    p(
        "transposed letters",
        {"name": "Meera Iyre", E: "meera.iyer@example.com"},
        {"name": "Meera Iyer", E: "meera.iyer@example.com"},
    ),
    p(
        "name order swapped",
        {"name": "Smith, Jonathan", E: "jonathan@smith.io"},
        {"name": "Jonathan Smith", E: "jonathan@smith.io"},
    ),
    p(
        "title and suffix",
        {"name": "Dr. Kavita Rao Jr.", E: "kavita.rao@example.com"},
        {"name": "Kavita Rao", E: "kavita.rao@example.com"},
    ),
    p(
        "middle initial",
        {"name": "Arjun K Mehta", E: "arjun.mehta@example.com"},
        {"name": "Arjun Mehta", E: "arjun.mehta@example.com"},
    ),
    p(
        "apostrophe",
        {"name": "Sean O'Brien", E: "sobrien@example.ie"},
        {"name": "Sean OBrien", E: "sobrien@example.ie"},
    ),
    p(
        "hyphenated surname",
        {"name": "Anna Lopez-Garcia", E: "anna.lg@example.es"},
        {"name": "Anna Lopez Garcia", E: "anna.lg@example.es"},
    ),
    p(
        "transliteration",
        {"name": "Mohammed Ali", E: "m.ali@example.com"},
        {"name": "Muhammad Ali", E: "m.ali@example.com"},
    ),
    p(
        "upper case name",
        {"name": "NEHA GUPTA", E: "neha@guptaco.in"},
        {"name": "Neha Gupta", E: "neha@guptaco.in"},
    ),
    p(
        "unicode width",
        {"name": "Ｒａｊ Ｐａｔｅｌ", E: "raj.patel@example.com"},
        {"name": "Raj Patel", E: "raj.patel@example.com"},
    ),
    p(
        "phone formats",
        {"name": "Sanjay Nair", PH: "+91-98765-11111", E: "sanjay@nair.dev"},
        {"name": "Sanjay Nair", PH: "09876511111", E: "sanjay@nair.dev"},
    ),
    p(
        "missing email one side",
        {"name": "Deepa Menon", PH: "98470 55555"},
        {"name": "Deepa Menon", PH: "98470 55555", E: "deepa@menon.in"},
    ),
    p(
        "missing phone one side",
        {"name": "Vikram Singh", E: "vikram@singh.co"},
        {"name": "Vikram Singh", E: "vikram@singh.co", PH: "98111 99999"},
    ),
    p(
        "company variants",
        {"name": "Tara Joshi", E: "tara@acme.in", "company": "Acme Pvt Ltd"},
        {"name": "Tara Joshi", E: "tara@acme.in", "company": "ACME"},
    ),
    p(
        "external ref, different email",
        {"name": "Ravi Kumar", E: "ravi@old.com"},
        {"name": "Ravi Kumar", E: "ravi.kumar@new.com", "refs": {"crm_id": "C-1"}},
    ),
    p(
        "external ref, no shared fields",
        {"name": "Lakshmi Iyer"},
        {"name": "L. Iyer Holdings", "refs": {"crm_id": "C-1"}},
    ),
    p(
        "support account, email only",
        {"name": "Imran Khan", E: "imran.khan@example.com"},
        {"name": "Imran Khan", E: "imran.khan@example.com"},
        b_system="support",
    ),
    p(
        "support ticket name variant",
        {"name": "Catherine Dsouza", E: "cathy.d@example.com"},
        {"name": "Kathy Dsouza", E: "cathy.d@example.com"},
        b_system="support",
    ),
    p(
        "same-system duplicate",
        {"name": "Pooja Reddy", E: "pooja@reddy.in", PH: "98490 12121"},
        {"name": "Pooja Reddy", E: "pooja@reddy.in", PH: "98490 12121"},
        b_system="crm",
    ),
    p(
        "same-system duplicate, typo",
        {"name": "Suresh Pillai", E: "suresh.pillai@example.com"},
        {"name": "Suresh Pilai", E: "suresh.pillai@example.com"},
        b_system="crm",
    ),
    p(
        "same-system duplicate, nickname",
        {"name": "Tom Wilson", PH: "98200 33344", E: "tw@wilson.uk"},
        {"name": "Thomas Wilson", PH: "98200 33344", E: "tw@wilson.uk"},
        b_system="crm",
    ),
    p(
        "billing duplicate",
        {"name": "Farah Sheikh", E: "farah@sheikh.ae"},
        {"name": "Farah Sheikh", E: "farah@sheikh.ae"},
        a_system="billing",
    ),
    p(
        "everything but phone differs in format",
        {
            "name": "Gopal Krishnan",
            PH: "+919845011111",
            E: "gk@example.com",
            "company": "GK Traders",
        },
        {
            "name": "Gopal Krishnan",
            PH: "9845011111",
            E: "GK@example.com",
            "company": "G.K. Traders",
        },
    ),
    p(
        "name typo + nickname",
        {"name": "Bobby Jhonson", E: "bob.j@example.com"},
        {"name": "Robert Johnson", E: "bob.j@example.com"},
    ),
    p(
        "email typo, same name and phone",
        {"name": "Nisha Bose", E: "nisha.bose@example.com", PH: "98300 45454"},
        {"name": "Nisha Bose", E: "nisha.bsoe@example.com", PH: "98300 45454"},
    ),
    p(
        "short name",
        {"name": "Li Na", E: "lina@example.cn"},
        {"name": "Na Li", E: "lina@example.cn"},
    ),
    p(
        "arabic script",
        {"name": "محمد علي", E: "m.ali@example.ae"},
        {"name": "محمد علي", E: "m.ali@example.ae"},
    ),
    p(
        "trailing whitespace and dots",
        {"name": "  Asha  Patil. ", E: "asha.patil@example.com"},
        {"name": "Asha Patil", E: "asha.patil@example.com"},
    ),
]

NEGATIVES = [
    n(
        "same common name",
        {"name": "Rahul Sharma", E: "rahul1@example.com", PH: "98111 00001"},
        {"name": "Rahul Sharma", E: "rahul.s@other.com", PH: "98222 00002"},
    ),
    n(
        "same name, other emails",
        {"name": "John Smith", E: "john@smith.com"},
        {"name": "John Smith", E: "jsmith@acme.com"},
    ),
    n(
        "same name and company",
        {"name": "Priya Patel", E: "priya@acme.in", "company": "Acme"},
        {"name": "Priya Patel", E: "ppatel@acme.in", "company": "Acme"},
    ),
    n(
        "same name, other phones",
        {"name": "Amit Kumar", PH: "98111 12345"},
        {"name": "Amit Kumar", PH: "98111 54321"},
    ),
    n("same name, nothing else", {"name": "Anjali Singh"}, {"name": "Anjali Singh"}),
    n(
        "nickname collision",
        {"name": "Bob Smith", E: "bob@smith.org", PH: "98100 10101"},
        {"name": "Robert Smith", E: "robert.smith@corp.com", PH: "98100 20202"},
    ),
    n(
        "family shared phone",
        {"name": "Anil Kumar", PH: "98765 43210", E: "anil@kumar.in"},
        {"name": "Sunita Kumar", PH: "98765 43210", E: "sunita@kumar.in"},
    ),
    n(
        "office shared phone",
        {"name": "Karan Malhotra", PH: "022 2345 6789", E: "karan@firm.in"},
        {"name": "Divya Shetty", PH: "022 2345 6789", E: "divya@firm.in"},
    ),
    n(
        "same surname, same domain",
        {"name": "Arun Kumar", E: "a.kumar@acme.com"},
        {"name": "Ravi Kumar", E: "r.kumar@acme.com"},
    ),
    n(
        "one letter apart, other emails",
        {"name": "Jon Smith", E: "jon@a.com"},
        {"name": "Jan Smith", E: "jan@b.com"},
    ),
    n(
        "similar names, other phones",
        {"name": "Sunil Mehta", PH: "98111 11111"},
        {"name": "Anil Mehta", PH: "98222 22222"},
    ),
    n(
        "father and son (Jr.)",
        {"name": "Raj Malhotra", E: "raj@malhotra.in", PH: "98200 11111"},
        {"name": "Raj Malhotra Jr.", E: "rajjr@malhotra.in", PH: "98200 22222"},
    ),
    n(
        "ref points to someone else",
        {"name": "Meena Das", E: "meena@das.in"},
        {"name": "Meena Das", E: "m.das@corp.in", "refs": {"crm_id": "C-999"}},
    ),
    n(
        "same company only",
        {"name": "Harish Rao", "company": "Initech"},
        {"name": "Leela Rao", "company": "Initech"},
    ),
    n(
        "same email domain only",
        {"name": "Zoya Khan", E: "zoya@bigcorp.com"},
        {"name": "Pradeep Shah", E: "pradeep@bigcorp.com"},
    ),
    n(
        "same first name",
        {"name": "Priya Nair", E: "priya.nair@x.com"},
        {"name": "Priya Menon", E: "priya.menon@y.com"},
    ),
    n(
        "same-system, same name",
        {"name": "Vijay Kumar", E: "vijay1@a.com", PH: "98400 11111"},
        {"name": "Vijay Kumar", E: "vijay2@b.com", PH: "98400 22222"},
        b_system="crm",
    ),
    n(
        "same-system, shared phone",
        {"name": "Rekha Iyer", PH: "98400 33333"},
        {"name": "Mohan Iyer", PH: "98400 33333"},
        b_system="crm",
    ),
    n(
        "support, same name",
        {"name": "Kiran Rao", E: "kiran@rao.in"},
        {"name": "Kiran Rao", E: "kiran.rao@other.in"},
        b_system="support",
    ),
    n(
        "generic mailbox, different people",
        {"name": "Neeraj Gupta", E: "info@shop.in", "company": "Shop"},
        {"name": "Fatima Begum", E: "info@shop.in", "company": "Shop"},
    ),
    n(
        "thin evidence: name and company",
        {"name": "Om Prakash", "company": "Prakash Traders"},
        {"name": "Om Prakash", "company": "Prakash Traders"},
    ),
    n(
        "swapped first and last of two people",
        {"name": "Kumar Ravi", E: "kr@a.com"},
        {"name": "Ravi Kumar", E: "rk@b.com"},
    ),
    n(
        "twins",
        {"name": "Aman Verma", E: "aman@verma.in", PH: "98100 77777"},
        {"name": "Naman Verma", E: "naman@verma.in", PH: "98100 88888"},
    ),
    n(
        "different people, typo-close emails",
        {"name": "Ria Sen", E: "ria.sen@example.com"},
        {"name": "Tia Sen", E: "tia.sen@example.com"},
    ),
    n(
        "common name, gmail",
        {"name": "Mohammed Ali", E: "mali1987@gmail.com"},
        {"name": "Mohammed Ali", E: "mohd.ali@gmail.com"},
    ),
    n("empty records", {}, {}),
    n(
        "only phones differ",
        {"name": "Sita Ram", PH: "98100 00011"},
        {"name": "Gita Ram", PH: "98100 00022"},
    ),
    n(
        "only company shared, refs elsewhere",
        {"name": "Ajay Dev", "company": "Zeta"},
        {"name": "Vinod Pal", "company": "Zeta", "refs": {"crm_id": "C-5"}},
    ),
]

PAIRS = POSITIVES + NEGATIVES


def decision(pair: Pair) -> str:
    a, b = pair.identities()
    return decide(score_pair(a, b).score, auto=AUTO, review=REVIEW)


def test_the_fixture_is_big_enough() -> None:
    assert len(PAIRS) >= 60
    assert len(POSITIVES) >= 30 and len(NEGATIVES) >= 25
    assert sum(pair.a_system == pair.b_system for pair in PAIRS) >= 5  # same-system duplicates


def test_recall_is_at_least_95_percent() -> None:
    missed = [pair.note for pair in POSITIVES if decision(pair) == "no_link"]
    recall = 1 - len(missed) / len(POSITIVES)

    assert recall >= 0.95, f"recall {recall:.3f}, missed: {missed}"


def test_no_false_auto_match() -> None:
    false_auto = [pair.note for pair in NEGATIVES if decision(pair) == "auto_matched"]

    assert false_auto == []


@pytest.mark.parametrize(
    "pair", [p for p in POSITIVES if "ref" not in p.note], ids=lambda p: p.note
)
def test_true_matches_share_a_block(pair: Pair) -> None:
    """Otherwise blocking would never put them side by side."""
    assert share_a_block(normalized(**pair.a), normalized(**pair.b))
