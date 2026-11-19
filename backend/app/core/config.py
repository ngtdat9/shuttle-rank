"""Environment configuration.

Values come from the process environment and, when present, ``backend/.env``.
``AUTH_MODE=dev`` is rejected when ``APP_ENV=production`` so a local auth stub
cannot boot in production.
"""

from pathlib import Path
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: Literal["development", "test", "production"] = "development"
    DATABASE_URL: str = "sqlite:///./badminton.db"
    CORS_ORIGINS: str = "http://localhost:3000"
    SUPABASE_URL: str = ""
    SUPABASE_JWT_SECRET: str = ""
    SUPABASE_JWT_AUDIENCE: str = "authenticated"
    AUTH_MODE: Literal["supabase", "dev"] = "supabase"
    DEV_ADMIN_TOKEN: str = ""
    ADMIN_BOOTSTRAP_USER_ID: str = ""
    ADMIN_BOOTSTRAP_EMAIL: str = ""

    @model_validator(mode="after")
    def production_disallows_dev_auth(self) -> Self:
        if self.APP_ENV == "production" and self.AUTH_MODE == "dev":
            raise ValueError("AUTH_MODE=dev is not allowed when APP_ENV=production")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
