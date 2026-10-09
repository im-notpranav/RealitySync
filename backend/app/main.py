from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import (
    AppError,
    app_error_handler,
    fallback_error_handler,
    validation_error_handler,
)
from app.core.logging import RequestIdMiddleware, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Setup goes here (e.g. database connect, start inline worker if WORKER_MODE=inline)
    yield
    # Teardown goes here


def create_app() -> FastAPI:
    setup_logging(settings.LOG_LEVEL)

    # /docs hidden when APP_ENV=production
    docs_url = "/docs" if settings.APP_ENV != "production" else None
    redoc_url = "/redoc" if settings.APP_ENV != "production" else None
    openapi_url = "/openapi.json"

    app = FastAPI(
        title="RealitySync API",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )

    app.add_middleware(RequestIdMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppError, app_error_handler)  # type: ignore
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore
    app.add_exception_handler(Exception, fallback_error_handler)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
