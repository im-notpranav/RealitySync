import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

# Settings are read at import time; give tests a dummy secret so a clean checkout needs no .env.
os.environ.setdefault("JWT_SECRET", "test-only-not-a-secret-but-32-bytes-long")
os.environ.setdefault("APP_ENV", "test")

import pytest
import pytest_asyncio
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from alembic import command
from app.core.config import settings
from app.db.session import get_session
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parent.parent
POSTGRES_IMAGE = "postgres:16-alpine"


def alembic_config(db_url: str) -> Config:
    """Alembic config pointing at `db_url`, usable from any working directory."""
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


@pytest.fixture(scope="session")
def database_url() -> Generator[str, None, None]:
    """`DATABASE_URL_TEST` if set (CI), else a throwaway Postgres container.

    Skips DB tests only when neither is available, so CI (which sets the variable) can never
    silently skip them.
    """
    url = os.environ.get("DATABASE_URL_TEST")
    if url:
        yield url
        return

    from testcontainers.community.postgres import PostgresContainer

    try:
        # The constructor already talks to the Docker daemon, so it belongs inside the try.
        container = PostgresContainer(POSTGRES_IMAGE, driver="asyncpg")
        container.start()
    except Exception as exc:  # noqa: BLE001 - docker missing or not running
        pytest.skip(f"no DATABASE_URL_TEST and Docker is unavailable: {type(exc).__name__}")
    try:
        yield container.get_connection_url()
    finally:
        container.stop()


@pytest.fixture(scope="session")
def alembic_cfg(database_url: str) -> Config:
    return alembic_config(database_url)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_engine(database_url: str, alembic_cfg: Config) -> AsyncGenerator[AsyncEngine, None]:
    settings.DATABASE_URL = database_url
    # alembic/env.py calls asyncio.run(), which cannot nest inside the running test loop.
    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
    engine = create_async_engine(database_url, pool_size=5)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Session inside an outer transaction that is rolled back after each test."""
    async with db_engine.connect() as conn:
        await conn.begin()
        factory = async_sessionmaker(
            bind=conn,
            expire_on_commit=False,
            class_=AsyncSession,
            join_transaction_mode="create_savepoint",
        )
        async with factory() as session:
            yield session
        await conn.rollback()


# Not autouse, so tests that do not need a real DB run without Docker.
@pytest.fixture
def override_get_session(db_session: AsyncSession) -> Generator[None, None, None]:
    async def _get_session_override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _get_session_override
    yield
    app.dependency_overrides.pop(get_session, None)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
