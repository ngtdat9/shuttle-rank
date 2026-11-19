"""Alembic upgrade and downgrade against a fresh SQLite file."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import make_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_alembic_upgrade_head_and_downgrade_base(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_file = tmp_path / "fresh.db"
    url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", url)

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", url)

    command.upgrade(config, "head")

    engine = make_engine(url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        check_names = {item["name"] for item in inspector.get_check_constraints("matches")}
    finally:
        engine.dispose()

    assert set(Base.metadata.tables) <= tables
    assert "alembic_version" in tables
    assert "ck_matches_player_a_ne_player_b" in check_names
    assert "ck_matches_winner_is_participant" in check_names

    command.downgrade(config, "base")

    engine = make_engine(url)
    try:
        remaining = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert "players" not in remaining
    assert "matches" not in remaining
    assert not set(Base.metadata.tables) & remaining
