from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: Literal["development", "test", "production"] = "development"
    DATABASE_URL: str = "postgresql+asyncpg://realitysync:realitysync@db:5432/realitysync"
    DATABASE_URL_TEST: str = ""

    JWT_SECRET: str
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 7

    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""

    # Parsed as list if comma separated or JSON array string
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    WORKER_MODE: Literal["inline", "separate"] = "inline"
    EVENT_BUS: Literal["memory", "pg_notify"] = "memory"

    MATCH_AUTO: float = 0.85
    MATCH_REVIEW: float = 0.60

    DEFAULT_PHONE_REGION: str = "IN"

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_MAX_CONCURRENCY: int = 2
    GEMINI_DAILY_BUDGET: int = 500
    LLM_REDACT_PII: bool = True

    LOG_LEVEL: str = "INFO"

    @model_validator(mode="after")
    def validate_worker_mode(self) -> "Settings":
        if self.WORKER_MODE == "separate" and self.EVENT_BUS != "pg_notify":
            raise ValueError("WORKER_MODE=separate requires EVENT_BUS=pg_notify")
        return self


settings = Settings()  # type: ignore
