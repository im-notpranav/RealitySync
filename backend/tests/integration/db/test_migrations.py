import asyncio

import pytest
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import command

REQUIRED_EXTENSIONS = {"pgcrypto", "citext", "pg_trgm"}
AUTH_TABLES = {"users", "refresh_tokens", "audit_logs"}
CORE_TABLES = {
    "api_keys",
    "source_systems",
    "ingest_events",
    "source_records",
    "record_versions",
    "entities",
    "entity_links",
    "rejected_pairs",
    "rules",
    "findings",
    "finding_events",
    "finding_explanations",
    "alerts",
    "alert_reads",
    "simulation_runs",
    "injected_issues",
    "simulation_ground_truth",
    "evaluation_runs",
    "entity_risk",
    "risk_events",
    "investigations",
    "investigation_checkpoints",
}
# Indexes 05 refers to by name (hot paths, 05 §8).
NAMED_INDEXES = {
    "idx_ingest_pending",
    "idx_ingest_processing",
    "idx_ingest_status_received",
    "idx_versions_system_recorded",
    "idx_entities_detection_due",
    "idx_findings_status_priority",
    "idx_findings_entity",
    "idx_findings_rule_status",
    "idx_findings_open",
    "idx_findings_created",
    "idx_findings_needs_explanation",
    "idx_explanations_cache",
    "idx_entity_risk_level",
    "uq_investigations_inputs",
}


async def installed_extensions(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as conn:
        rows = await conn.execute(text("SELECT extname FROM pg_extension"))
        return {row[0] for row in rows}


@pytest.mark.db
@pytest.mark.asyncio
async def test_migrations_round_trip(db_engine: AsyncEngine, alembic_cfg: Config) -> None:
    """Every migration must be reversible (07 §14): head → base → head leaves the same state."""
    assert REQUIRED_EXTENSIONS <= await installed_extensions(db_engine)

    await asyncio.to_thread(command.downgrade, alembic_cfg, "base")
    assert not REQUIRED_EXTENSIONS & await installed_extensions(db_engine)

    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
    assert REQUIRED_EXTENSIONS <= await installed_extensions(db_engine)


async def existing_tables(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        return {row[0] for row in rows}


@pytest.mark.db
@pytest.mark.asyncio
async def test_auth_tables_migration_is_reversible(
    db_engine: AsyncEngine, alembic_cfg: Config
) -> None:
    """T-006: downgrading past the auth migration drops its tables; `upgrade head` restores them."""
    assert AUTH_TABLES <= await existing_tables(db_engine)

    await asyncio.to_thread(command.downgrade, alembic_cfg, "6804bb1df3a9")
    assert not AUTH_TABLES & await existing_tables(db_engine)
    assert REQUIRED_EXTENSIONS <= await installed_extensions(db_engine)

    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
    assert AUTH_TABLES <= await existing_tables(db_engine)


@pytest.mark.db
@pytest.mark.asyncio
async def test_models_match_migrations(db_engine: AsyncEngine, alembic_cfg: Config) -> None:
    """`alembic check`: models must not have changes that no migration captures."""
    await asyncio.to_thread(command.check, alembic_cfg)


@pytest.mark.db
@pytest.mark.asyncio
async def test_core_schema_migration_is_reversible(
    db_engine: AsyncEngine, alembic_cfg: Config
) -> None:
    """T-009: downgrading past the core migration drops only its tables; `upgrade head` restores."""
    assert CORE_TABLES <= await existing_tables(db_engine)

    await asyncio.to_thread(command.downgrade, alembic_cfg, "202610141000")
    remaining = await existing_tables(db_engine)
    assert not CORE_TABLES & remaining
    assert AUTH_TABLES <= remaining

    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
    assert CORE_TABLES <= await existing_tables(db_engine)


@pytest.mark.db
@pytest.mark.asyncio
async def test_named_indexes_exist(db_engine: AsyncEngine) -> None:
    async with db_engine.connect() as conn:
        rows = await conn.execute(
            text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")
        )
        assert NAMED_INDEXES <= {row[0] for row in rows}
