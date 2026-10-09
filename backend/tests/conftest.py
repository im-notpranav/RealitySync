from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
