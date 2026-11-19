"""P6-01: persistence, migrations round trip, and seed-demo sanity on file SQLite databases."""

import logging
import os
import subprocess
import sys
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.rate_limit import failed_auth_limiter
from app.db.base import Base
from app.db.session import get_db, make_engine
from app.main import app
from app.models.audit_log import AuditLog
from app.models.match import Match
from app.models.player import Player
from tests.qa.api_helpers import API, auth, club_match, make_players, make_tournament

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _limiter() -> Generator[None, None, None]:
    """Reset auth state, and undo the logging changes Alembic's env.py makes.

    ``logging.config.fileConfig`` disables existing loggers, which would break
    caplog-based tests that run later in the same session.
    """
    failed_auth_limiter.reset()
    loggers = [
        (lg, lg.disabled, lg.level, list(lg.handlers))
        for lg in logging.Logger.manager.loggerDict.values()
        if isinstance(lg, logging.Logger)
    ]
    root = (logging.getLogger(), logging.getLogger().level, list(logging.getLogger().handlers))
    yield
    for lg, disabled, level, handlers in loggers:
        lg.disabled, lg.level, lg.handlers = disabled, level, handlers
    root[0].level, root[0].handlers = root[1], root[2]
    failed_auth_limiter.reset()


def _alembic(url: str, monkeypatch: pytest.MonkeyPatch) -> Config:
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def _tables(url: str) -> set[str]:
    engine = make_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def _serve(url: str) -> Generator[TestClient, None, None]:
    """A fresh engine and app lifespan bound to the file at ``url``."""
    engine = make_engine(url)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override() -> Generator[Session, None, None]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def _cli(url: str, *args: str, app_env: str = "development", auth_mode: str = "dev") -> Any:
    env = os.environ.copy()
    env.update(
        DATABASE_URL=url,
        APP_ENV=app_env,
        AUTH_MODE=auth_mode,
        DEV_ADMIN_TOKEN="test-token",
        ADMIN_BOOTSTRAP_USER_ID="",
        ADMIN_BOOTSTRAP_EMAIL="",
    )
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


# ------------------------------- migrations --------------------------------


def test_alembic_up_down_up_round_trip_on_a_fresh_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = f"sqlite:///{tmp_path / 'm.db'}"
    config = _alembic(url, monkeypatch)
    expected = set(Base.metadata.tables)

    command.upgrade(config, "head")
    assert expected <= _tables(url)
    command.downgrade(config, "base")
    assert not (expected & _tables(url))
    command.upgrade(config, "head")
    assert expected <= _tables(url)
    command.upgrade(config, "head")  # idempotent at head
    assert expected <= _tables(url)


def test_migrated_schema_has_no_drift_from_models(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    url = f"sqlite:///{tmp_path / 'drift.db'}"
    command.upgrade(_alembic(url, monkeypatch), "head")
    engine = make_engine(url)
    try:
        with engine.connect() as conn:
            diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    finally:
        engine.dispose()
    assert diff == [], diff


def test_migrated_database_enforces_foreign_keys_and_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy.exc import IntegrityError

    url = f"sqlite:///{tmp_path / 'fk.db'}"
    command.upgrade(_alembic(url, monkeypatch), "head")
    engine = make_engine(url)
    with Session(bind=engine) as db:
        db.add(Player(display_name="Solo"))
        db.commit()
        solo = db.scalars(select(Player)).one()
        db.add(
            Match(
                player_a_id=solo.id,
                player_b_id=solo.id,
                winner_id=solo.id,
                match_date=datetime(2026, 1, 1),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
    engine.dispose()


# ------------------------------- persistence -------------------------------


def test_api_writes_survive_an_app_restart_on_a_file_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_file = tmp_path / "persist.db"
    url = f"sqlite:///{db_file}"
    command.upgrade(_alembic(url, monkeypatch), "head")

    first = _serve(url)
    client = next(first)
    a, b, c, d = make_players(client, 4, prefix="Keep")
    club_match(client, a, b, a)
    club_match(client, c, d, d)
    tid = make_tournament(client, [a, b, c, d], name="Persisted Cup")
    gen = client.post(f"{API}/admin/tournaments/{tid}/generate-bracket", json={}, headers=auth())
    assert gen.status_code == 200
    rankings_before = client.get(f"{API}/rankings").json()
    matches_before = client.get(f"{API}/matches").json()
    bracket_before = client.get(f"{API}/tournaments/{tid}/bracket").json()
    audit_before = client.get(f"{API}/admin/audit-logs", headers=auth()).json()["total"]
    with pytest.raises(StopIteration):
        next(first)  # closes lifespan and disposes the engine
    assert db_file.is_file() and db_file.stat().st_size > 0

    second = _serve(url)
    again = next(second)
    assert again.get(f"{API}/rankings").json() == rankings_before
    assert again.get(f"{API}/matches").json() == matches_before
    assert again.get(f"{API}/tournaments/{tid}/bracket").json() == bracket_before
    assert again.get(f"{API}/tournaments/{tid}").json()["status"] == "in_progress"
    assert again.get(f"{API}/admin/audit-logs", headers=auth()).json()["total"] == audit_before
    # and the restarted app can keep writing
    e = make_players(again, 1, prefix="After")[0]
    assert again.get(f"{API}/players/{e}").status_code == 200
    with pytest.raises(StopIteration):
        next(second)


def test_failed_write_leaves_no_partial_state_after_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = f"sqlite:///{tmp_path / 'rollback.db'}"
    command.upgrade(_alembic(url, monkeypatch), "head")
    gen = _serve(url)
    client = next(gen)
    a, b = make_players(client, 2, prefix="Rb")
    before = client.get(f"{API}/rankings").json()
    bad = client.post(
        f"{API}/admin/matches",
        json={
            "player_a_id": a,
            "player_b_id": a,
            "winner_id": a,
            "match_date": "2026-10-01T10:00:00Z",
        },
        headers=auth(),
    )
    assert bad.status_code == 422
    assert client.get(f"{API}/rankings").json() == before
    assert client.get(f"{API}/matches").json()["total"] == 0
    with pytest.raises(StopIteration):
        next(gen)
    engine = make_engine(url)
    with Session(bind=engine) as db:
        assert db.scalar(select(func.count()).select_from(Match)) == 0
        assert not db.scalars(select(AuditLog).where(AuditLog.action == "match.create")).all()
    engine.dispose()


# ----------------------------------- seed ----------------------------------


@pytest.fixture
def seeded_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    url = f"sqlite:///{tmp_path / 'seed.db'}"
    command.upgrade(_alembic(url, monkeypatch), "head")
    result = _cli(url, "seed-demo", "--reset")
    assert result.returncode == 0, result.stderr
    assert "Seeded demo club" in result.stdout
    return url


def test_seed_reset_ratings_are_zero_sum(seeded_url: str) -> None:
    gen = _serve(seeded_url)
    client = next(gen)
    items = client.get(f"{API}/players").json()["items"]
    assert len(items) == 8
    assert sum(p["current_rating"] for p in items) == 1500 * len(items)
    assert all(p["highest_rating"] >= p["current_rating"] for p in items)
    rankings = client.get(f"{API}/rankings", params={"page_size": 100}).json()["items"]
    assert sum(r["rating"] for r in rankings) == 1500 * len(rankings)
    with pytest.raises(StopIteration):
        next(gen)


def test_seed_reset_is_repeatable_on_a_populated_database(seeded_url: str) -> None:
    refused = _cli(seeded_url, "seed-demo")
    assert refused.returncode == 1 and "reset" in refused.stderr.lower()
    again = _cli(seeded_url, "seed-demo", "--reset")
    assert again.returncode == 0, again.stderr
    engine = make_engine(seeded_url)
    with Session(bind=engine) as db:
        assert db.scalar(select(func.count()).select_from(Player)) == 8
        ratings = db.scalars(select(Player.current_rating)).all()
        assert sum(ratings) == 8 * 1500
    engine.dispose()


def test_seed_tournaments_are_consistent(seeded_url: str) -> None:
    gen = _serve(seeded_url)
    client = next(gen)
    tournaments = client.get(f"{API}/tournaments").json()["items"]
    by_status = {t["status"]: t for t in tournaments}
    assert set(by_status) == {"completed", "in_progress"}

    done = client.get(f"{API}/tournaments/{by_status['completed']['id']}").json()
    assert done["champion"] is not None
    positions = {p["player"]["id"]: p["final_position"] for p in done["participants"]}
    assert all(pos is not None for pos in positions.values())
    assert sorted(v for v in positions.values() if v == 1) == [1]
    assert positions[done["champion"]["id"]] == 1
    assert done["runner_up"] is not None and positions[done["runner_up"]["id"]] == 2
    bracket = client.get(f"{API}/tournaments/{done['id']}/bracket").json()
    slots = [m for r in bracket["rounds"] for m in r["matches"]]
    assert all(m["status"] in {"completed", "bye"} for m in slots)
    final = bracket["rounds"][-1]["matches"][0]
    assert final["winner_id"] == done["champion"]["id"]
    for m in slots:
        if m["status"] == "completed":
            assert m["match_id"] is not None
            assert client.get(f"{API}/matches/{m['match_id']}").json()["tournament"] is not None

    live = client.get(f"{API}/tournaments/{by_status['in_progress']['id']}").json()
    assert live["champion"] is None and live["bracket_generated"] is True
    live_slots = [
        m
        for r in client.get(f"{API}/tournaments/{live['id']}/bracket").json()["rounds"]
        for m in r["matches"]
    ]
    assert any(m["status"] == "ready" for m in live_slots)
    for m in live_slots:
        if m["status"] == "ready":
            assert m["player_a"] is not None and m["player_b"] is not None
            assert m["winner_id"] is None and m["match_id"] is None
    assert all(p["final_position"] is None for p in live["participants"])
    with pytest.raises(StopIteration):
        next(gen)


def test_seed_refuses_in_production_and_changes_nothing(seeded_url: str) -> None:
    engine = make_engine(seeded_url)
    with Session(bind=engine) as db:
        before = sorted(db.execute(select(Player.id, Player.current_rating)).all())
    for extra in ((), ("--reset",)):
        result = _cli(seeded_url, "seed-demo", *extra, app_env="production", auth_mode="supabase")
        assert result.returncode == 1
        assert "production" in result.stderr.lower()
    with Session(bind=engine) as db:
        assert sorted(db.execute(select(Player.id, Player.current_rating)).all()) == before
    engine.dispose()


def test_seed_refusal_in_production_with_dev_auth_cannot_even_boot(seeded_url: str) -> None:
    result = _cli(seeded_url, "seed-demo", "--reset", app_env="production", auth_mode="dev")
    assert result.returncode != 0


def test_seeded_public_endpoints_all_serve_data(seeded_url: str) -> None:
    gen = _serve(seeded_url)
    client = next(gen)
    for path in (
        "/dashboard",
        "/rankings",
        "/rankings/monthly",
        "/players",
        "/matches",
        "/tournaments",
        "/achievements",
    ):
        assert client.get(API + path).status_code == 200, path
    player = client.get(f"{API}/players").json()["items"][0]["id"]
    for sub in ("", "/matches", "/rating-history", "/monthly", "/achievements"):
        assert client.get(f"{API}/players/{player}{sub}").status_code == 200, sub
    with pytest.raises(StopIteration):
        next(gen)
