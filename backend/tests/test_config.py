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
