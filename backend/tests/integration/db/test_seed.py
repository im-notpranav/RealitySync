"""Startup bootstrap of the source systems (05 §6, T-009)."""

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.seed import CANONICAL_STATUSES, bootstrap_source_systems
from app.models import SourceSystem

pytestmark = [pytest.mark.db, pytest.mark.asyncio]

AUTHORITY_KEYS = {
    "name",
    "email",
    "phone",
    "company",
    "status",
    "plan",
    "amount",
    "invoice_dates",
    "ticket",
}


def session_factory(db_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    """Sessions on the test's connection, so the bootstrap rolls back with the test."""
    return async_sessionmaker(
        bind=db_session.bind, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )


async def systems(session: AsyncSession) -> dict[str, SourceSystem]:
    session.expire_all()
    rows = await session.scalars(select(SourceSystem))
    return {row.key: row for row in rows}


@pytest_asyncio.fixture
async def empty(db_session: AsyncSession) -> AsyncSession:
    """The test session with no source systems (rolled back afterwards)."""
    await db_session.execute(delete(SourceSystem))
    return db_session


async def test_creates_the_three_systems_with_defaults(empty: AsyncSession) -> None:
    await bootstrap_source_systems(session_factory(empty))

    found = await systems(empty)
    assert {key: s.name for key, s in found.items()} == {
        "crm": "CRM",
        "billing": "Billing",
        "support": "Support",
    }
    for system in found.values():
        assert system.is_active is True
        assert system.reliability_weight == Decimal("0.80")
        assert set(system.field_authority) == AUTHORITY_KEYS


async def test_field_authority_matches_the_module_table(empty: AsyncSession) -> None:
    await bootstrap_source_systems(session_factory(empty))

    found = await systems(empty)
    crm, billing, support = (found[k].field_authority for k in ("crm", "billing", "support"))
    assert (crm["email"], billing["email"], support["email"]) == (0.9, 0.6, 0.4)
    assert (crm["plan"], billing["status"], support["status"]) == (0.5, 0.95, 0.2)
    assert (crm["amount"], billing["invoice_dates"], support["amount"]) == (0.2, 1.0, 0.0)
    assert (crm["ticket"], billing["ticket"], support["ticket"]) == (0.0, 0.0, 1.0)


async def test_status_mapping_only_yields_canonical_statuses(empty: AsyncSession) -> None:
    await bootstrap_source_systems(session_factory(empty))

    for system in (await systems(empty)).values():
        assert set(system.status_mapping) == set(CANONICAL_STATUSES)
        for record_type, mapping in system.status_mapping.items():
            canonical = CANONICAL_STATUSES[record_type]
            assert set(mapping.values()) <= set(canonical)
            assert all(mapping[status] == status for status in canonical)
            assert all(raw == raw.strip().casefold() for raw in mapping)


async def test_documented_status_examples(empty: AsyncSession) -> None:
    await bootstrap_source_systems(session_factory(empty))

    found = await systems(empty)
    assert found["billing"].status_mapping["subscription"]["canceled"] == "cancelled"
    assert found["crm"].status_mapping["account"]["customer"] == "active"


async def test_is_idempotent_and_keeps_admin_edits(empty: AsyncSession) -> None:
    factory = session_factory(empty)
    await bootstrap_source_systems(factory)
    billing = (await systems(empty))["billing"]
    billing.reliability_weight = Decimal("0.95")
    billing.field_authority = {**billing.field_authority, "email": 0.7}
    billing.is_active = False
    await empty.flush()

    await bootstrap_source_systems(factory)

    found = await systems(empty)
    assert len(found) == 3
    edited = found["billing"]
    assert (edited.reliability_weight, edited.is_active) == (Decimal("0.95"), False)
    assert edited.field_authority["email"] == 0.7


async def test_recreates_only_a_missing_system(empty: AsyncSession) -> None:
    factory = session_factory(empty)
    await bootstrap_source_systems(factory)
    ids = {key: s.id for key, s in (await systems(empty)).items()}
    await empty.execute(delete(SourceSystem).where(SourceSystem.key == "support"))

    await bootstrap_source_systems(factory)

    after = {key: s.id for key, s in (await systems(empty)).items()}
    assert set(after) == {"crm", "billing", "support"}
    assert (after["crm"], after["billing"]) == (ids["crm"], ids["billing"])
    assert after["support"] != ids["support"]
