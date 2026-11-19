"""Settings validation."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_dev_auth_is_rejected_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_MODE", "dev")
    with pytest.raises(ValidationError, match="AUTH_MODE=dev is not allowed"):
        Settings(_env_file=None)


def test_production_supabase_auth_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_MODE", "supabase")
    settings = Settings(_env_file=None)
    assert settings.APP_ENV == "production"
    assert settings.AUTH_MODE == "supabase"


def test_cors_origins_split_on_commas() -> None:
    settings = Settings(CORS_ORIGINS="http://localhost:3000, http://127.0.0.1:3000")
    assert settings.cors_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]


def test_importing_settings_fails_at_startup_for_dev_auth_in_production() -> None:
    env = os.environ.copy()
    env["APP_ENV"] = "production"
    env["AUTH_MODE"] = "dev"
    env.pop("PYTEST_CURRENT_TEST", None)
    result = subprocess.run(
        [sys.executable, "-c", "from app.core.config import settings"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "AUTH_MODE=dev is not allowed when APP_ENV=production" in result.stderr + result.stdout


def test_normalize_database_url_maps_supabase_urls_to_psycopg() -> None:
    from app.db.session import normalize_database_url

    assert normalize_database_url("postgresql://u:p@h:5432/db") == (
        "postgresql+psycopg://u:p@h:5432/db"
    )
    assert normalize_database_url("postgres://u:p@h:6543/db?sslmode=require") == (
        "postgresql+psycopg://u:p@h:6543/db?sslmode=require"
    )
    assert normalize_database_url("postgresql+psycopg://u@h/db") == "postgresql+psycopg://u@h/db"
    assert normalize_database_url("sqlite:///./x.db") == "sqlite:///./x.db"


def test_postgres_engine_uses_pre_ping() -> None:
    from app.db.session import make_engine

    engine = make_engine("postgres://u:p@localhost:6543/db")
    assert engine.dialect.driver == "psycopg"
    assert engine.pool._pre_ping is True  # noqa: SLF001
    engine.dispose()
