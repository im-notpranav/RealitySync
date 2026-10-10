from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import get_session
from app.main import app

# Port 1 is never a Postgres server, so connecting fails fast and deterministically.
UNREACHABLE_DB_URL = "postgresql+asyncpg://nobody:nothing@127.0.0.1:1/none"


@pytest.mark.db
@pytest.mark.asyncio
@pytest.mark.usefixtures("override_get_session")
async def test_ready_is_200_with_a_real_database(async_client: AsyncClient) -> None:
    response = await async_client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["db"] == "ok"


@pytest.fixture
def unreachable_db() -> Generator[None, None, None]:
    engine = create_async_engine(UNREACHABLE_DB_URL, connect_args={"timeout": 2})
    factory = async_sessionmaker(bind=engine, class_=AsyncSession)

    async def _session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = _session
    yield
    app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
@pytest.mark.usefixtures("unreachable_db")
async def test_ready_is_503_when_database_is_down(async_client: AsyncClient) -> None:
    response = await async_client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["db"] == "down"
