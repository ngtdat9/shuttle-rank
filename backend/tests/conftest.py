"""Pytest setup.

The environment is pinned to a temporary SQLite file before the app is imported
so tests never open the development database.
"""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

_TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="badminton-tests-"))
os.environ["APP_ENV"] = "test"
os.environ["AUTH_MODE"] = "dev"
os.environ["DEV_ADMIN_TOKEN"] = "test-token"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_DIR / 'test.db'}"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_JWT_SECRET"] = ""
os.environ["SUPABASE_JWT_AUDIENCE"] = "authenticated"
os.environ["ADMIN_BOOTSTRAP_USER_ID"] = ""
os.environ["ADMIN_BOOTSTRAP_EMAIL"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import make_engine
from app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def session(tmp_path: Path) -> Generator[Session, None, None]:
    engine = make_engine(f"sqlite:///{tmp_path / 'constraints.db'}")
    Base.metadata.create_all(engine)
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.rollback()
        db.close()
        engine.dispose()
