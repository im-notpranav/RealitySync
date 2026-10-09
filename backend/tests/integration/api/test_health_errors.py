from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock

import pytest
from fastapi import APIRouter
from httpx import AsyncClient
from pydantic import BaseModel

from app.core.errors import NotFoundError, RateLimited
from app.db.session import get_session
from app.main import app

# Add test routes to verify error handlers
test_router = APIRouter()


class DummyPayload(BaseModel):
    name: str
    age: int


@test_router.get("/test-404")
async def route_404() -> dict[str, str]:
    raise NotFoundError("user", "123")


@test_router.post("/test-422")
async def route_422(payload: DummyPayload) -> dict[str, str]:
    return {"status": "ok"}


@test_router.get("/test-429")
async def route_429() -> dict[str, str]:
    raise RateLimited(retry_after=120)


app.include_router(test_router)


@pytest.fixture(autouse=True)
def mock_db_session() -> Generator[None, None, None]:
    # Mock the DB session for API tests so they don't need Docker
    async def _mock_get_session() -> AsyncGenerator[AsyncMock, None]:
        mock_session = AsyncMock()
        # SELECT 1 will succeed silently
        yield mock_session

    app.dependency_overrides[get_session] = _mock_get_session
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient) -> None:
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_check(async_client: AsyncClient) -> None:
    response = await async_client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["db"] == "ok"
    assert body["worker"] == "ok"
    assert body["gemini"] in ("configured", "missing")


@pytest.mark.asyncio
async def test_error_envelope_404(async_client: AsyncClient) -> None:
    response = await async_client.get("/test-404")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "request_id" in data["error"]


@pytest.mark.asyncio
async def test_error_envelope_422(async_client: AsyncClient) -> None:
    response = await async_client.post("/test-422", json={"name": "Alice"})  # missing age
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert any(d["field"] == "body->age" for d in data["error"]["details"])
    assert "request_id" in data["error"]


@pytest.mark.asyncio
async def test_error_envelope_429(async_client: AsyncClient) -> None:
    response = await async_client.get("/test-429")
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "120"
    data = response.json()
    assert data["error"]["code"] == "RATE_LIMITED"


@pytest.mark.asyncio
async def test_cors_headers(async_client: AsyncClient) -> None:
    headers = {"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"}
    response = await async_client.options("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    assert response.headers.get("Access-Control-Allow-Credentials") == "true"
