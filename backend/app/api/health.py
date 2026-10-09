from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session

router = APIRouter()


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    """Shape per 04 §13. `status` is `ready` only when every dependency is usable."""

    status: Literal["ready", "not_ready"]
    db: Literal["ok", "down"]
    worker: Literal["ok", "lagging"]
    gemini: Literal["configured", "missing"]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", response_model=ReadyResponse)
async def ready_check(
    response: Response,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> ReadyResponse:
    try:
        await session.execute(text("SELECT 1"))
        db_status: Literal["ok", "down"] = "ok"
    except Exception:  # noqa: BLE001 - any connection failure means "not ready"
        db_status = "down"

    # TODO(T-044): report "lagging" when an ingest event or detection request is > 60 s old.
    worker_status: Literal["ok", "lagging"] = "ok"
    # A missing Gemini key is not a readiness failure: explanations fall back to templates.
    gemini_status: Literal["configured", "missing"] = (
        "configured" if settings.GEMINI_API_KEY else "missing"
    )

    ready = db_status == "ok" and worker_status == "ok"
    if not ready:
        response.status_code = 503
    return ReadyResponse(
        status="ready" if ready else "not_ready",
        db=db_status,
        worker=worker_status,
        gemini=gemini_status,
    )
