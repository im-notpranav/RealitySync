import os
from collections.abc import AsyncGenerator as AbcAsyncGenerator
from collections.abc import Generator

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
from testcontainers.postgres import PostgresContainer

from alembic import command
from app.core.config import settings
from app.db.session import get_session
from app.main import app


@pytest.fixture(scope="session")
def db_engine() -> Generator[AsyncEngine, None, None]:
    db_url = os.environ.get("DATABASE_URL_TEST")
    container = None
    if not db_url:
        container = PostgresContainer("postgres:15-alpine")
        container.start()
        sync_url = container.get_connection_url()
        # Convert sync url to async url for asyncpg
        db_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

    settings.DATABASE_URL = db_url

    engine = create_async_engine(db_url, pool_size=5)

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    yield engine

    if container:
        container.stop()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine: AsyncEngine) -> AbcAsyncGenerator[AsyncSession, None]:
    async with db_engine.connect() as conn:
        await conn.begin()
        await conn.begin_nested()

        async_session_factory = async_sessionmaker(
            bind=conn, expire_on_commit=False, class_=AsyncSession
        )

        async with async_session_factory() as session:
            yield session

        await conn.rollback()


# We do not autouse this, so tests can run without Docker if they don't need a real DB.
@pytest.fixture
def override_get_session(db_session: AsyncSession) -> Generator[None, None, None]:
    async def _get_session_override() -> AbcAsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _get_session_override
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client() -> AbcAsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
