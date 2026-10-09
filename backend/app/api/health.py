from fastapi import APIRouter
from pydantic import BaseModel

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
async def ready_check() -> dict[str, str]:
    # DB check is not implemented yet (T-003)
    return {"status": "ok", "db": "unknown"}
