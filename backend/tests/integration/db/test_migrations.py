import asyncio

import pytest
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import command

REQUIRED_EXTENSIONS = {"pgcrypto", "citext", "pg_trgm"}


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


@pytest.mark.db
@pytest.mark.asyncio
async def test_models_match_migrations(db_engine: AsyncEngine, alembic_cfg: Config) -> None:
    """`alembic check`: models must not have changes that no migration captures."""
    await asyncio.to_thread(command.check, alembic_cfg)
