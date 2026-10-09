from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

router = APIRouter()


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    db: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", response_model=ReadyResponse)
async def ready_check(
    response: Response,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:  # noqa: BLE001
        db_status = "down"
        response.status_code = 503

    return {"status": "ok" if db_status == "ok" else "error", "db": db_status}
