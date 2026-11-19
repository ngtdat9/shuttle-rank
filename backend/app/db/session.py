"""Engine and request-scoped sessions."""

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def normalize_database_url(database_url: str) -> str:
    """Map Supabase-style ``postgres://`` and ``postgresql://`` URLs to the psycopg 3 driver."""
    url = database_url.strip()
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def make_engine(database_url: str) -> Engine:
    """Create an engine.

    SQLite connections disable same-thread checks and enforce foreign keys.
    PostgreSQL engines ping connections before use and recycle them, which
    survives Supabase pooler and Render idle disconnects.
    """
    database_url = normalize_database_url(database_url)
    connect_args: dict[str, Any] = {}
    kwargs: dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        kwargs.update(pool_pre_ping=True, pool_recycle=300, pool_size=5, max_overflow=5)
        if database_url.startswith("postgresql+psycopg"):
            # Supabase's transaction pooler (port 6543) does not support prepared statements.
            connect_args["prepare_threshold"] = None
    engine = create_engine(database_url, connect_args=connect_args, **kwargs)
    if database_url.startswith("sqlite"):
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


engine = make_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
