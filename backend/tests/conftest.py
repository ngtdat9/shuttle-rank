"""Pytest setup.

The environment is pinned to a temporary SQLite file before the app is imported
so tests never open the development database.

Set ``TEST_DATABASE_URL`` (for example ``postgresql://user@host:5432/testdb``) to
run the ``session``, ``db`` and ``api_client`` fixtures against PostgreSQL. Each
test gets its own throwaway schema that is dropped afterwards. Tests that build
their own SQLite file (migrations, CLI subprocess, auth module tests) stay on
SQLite. SQLite is the default.
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

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db, make_engine
from app.main import app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "").strip()


@pytest.fixture
def fixture_engine(tmp_path: Path) -> Generator[Engine, None, None]:
    """Fresh schema-created engine: SQLite file by default, a PostgreSQL schema if configured."""
    if not TEST_DATABASE_URL:
        engine = make_engine(f"sqlite:///{tmp_path / 'fixture.db'}")
        Base.metadata.create_all(engine)
        yield engine
        engine.dispose()
        return
    schema = f"t_{uuid.uuid4().hex}"
    admin = make_engine(TEST_DATABASE_URL)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = make_engine(TEST_DATABASE_URL)

    # Pin every pooled connection to the throwaway schema.
    @event.listens_for(engine, "connect")
    def _set_search_path(dbapi_connection, _record):  # type: ignore[no-untyped-def]
        with dbapi_connection.cursor() as cursor:
            cursor.execute(f'SET search_path TO "{schema}"')
        dbapi_connection.commit()

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def session(fixture_engine: Engine) -> Generator[Session, None, None]:
    engine = fixture_engine
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def db(fixture_engine: Engine) -> Generator[Session, None, None]:
    """Isolated database. Service calls commit; the database is discarded afterward."""
    engine = fixture_engine
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    database = factory()
    try:
        yield database
    finally:
        database.rollback()
        database.close()


@pytest.fixture
def api_client(
    fixture_engine: Engine,
) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    """HTTP client and session factory sharing one temporary database."""
    engine = fixture_engine
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        database = factory()
        try:
            yield database
        except Exception:
            database.rollback()
            raise
        finally:
            database.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client, factory
    app.dependency_overrides.clear()
