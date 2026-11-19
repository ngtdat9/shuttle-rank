"""Demo seed: reproducible, refused in production, and consistent with a full replay."""

import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.db.session import make_engine
from app.models.achievement import Achievement, PlayerAchievement
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.models.match import Match
from app.models.player import Player
from app.services.rating_service import recalculate_all
from app.services.seed import SeedError, seed_demo

BACKEND_DIR = Path(__file__).resolve().parents[1]
_NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)


def _session(tmp_path: Path, name: str) -> tuple[object, Session]:
    engine = make_engine(f"sqlite:///{tmp_path / name}")
    Base.metadata.create_all(engine)
    database = Session(bind=engine)
    return engine, database


def _snapshot(db: Session) -> dict[str, object]:
    players = {player.id: player.display_name for player in db.scalars(select(Player)).all()}
    ratings = sorted(
        (player.display_name, player.current_rating, player.highest_rating)
        for player in db.scalars(select(Player)).all()
    )
    matches = sorted(
        (
            players[match.player_a_id],
            players[match.player_b_id],
            players[match.winner_id],
            match.status,
            tuple(tuple(game) for game in match.game_scores or []),
            match.match_date.isoformat(),
        )
        for match in db.scalars(select(Match)).all()
    )
    achievement_rows = list(db.scalars(select(Achievement)).all())
    achievement_names = {row.id: row.name for row in achievement_rows}
    achievements = sorted(
        (row.name, row.icon, row.criteria_type, row.criteria_value) for row in achievement_rows
    )
    awards = sorted(
        (players[row.player_id], achievement_names[row.achievement_id])
        for row in db.scalars(select(PlayerAchievement)).all()
    )
    return {"ratings": ratings, "matches": matches, "awards": awards, "achievements": achievements}


def _assert_badminton(snapshot: dict[str, object]) -> None:
    matches = snapshot["matches"]
    assert isinstance(matches, list)
    statuses = [match[3] for match in matches]
    assert statuses.count("disputed") == 1
    assert statuses.count("canceled") == 1
    assert statuses.count("completed") >= 20
    dates = []
    for player_a, _player_b, winner, status, scores, played_at in matches:
        played = datetime.fromisoformat(played_at)
        dates.append(played)
        assert played <= _NOW
        if status != "completed":
            continue
        assert isinstance(scores, tuple)
        assert len(scores) in (2, 3)
        wins = {"a": 0, "b": 0}
        for game in scores:
            left, right = game
            assert 0 <= left <= 30 and 0 <= right <= 30
            if left > right:
                assert left >= 21 and (left == 30 or left - right >= 2)
                wins["a"] += 1
            else:
                assert right >= 21 and (right == 30 or right - left >= 2)
                wins["b"] += 1
        winner_side = "a" if winner == player_a else "b"
        assert wins[winner_side] == 2
        assert wins["a"] + wins["b"] == len(scores)
    assert max(dates).isocalendar()[:2] == _NOW.isocalendar()[:2]


def test_seed_demo_is_reproducible_and_matches_recalculate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "APP_ENV", "development")
    engine_a, db_a = _session(tmp_path, "a.db")
    engine_b, db_b = _session(tmp_path, "b.db")
    try:
        first = seed_demo(db_a, now=_NOW)
        second = seed_demo(db_b, now=_NOW)
        snap_a = _snapshot(db_a)
        snap_b = _snapshot(db_b)
        assert snap_a == snap_b
        assert first.players == 8
        assert first.matches == second.matches
        assert first.completed >= 20
        assert first.disputed == 1
        assert first.canceled == 1
        assert first.achievements == 5
        assert first.awards >= 2
        assert first.render().splitlines()[0] == "Seeded demo club"
        names = [name for name, _rating in first.ratings]
        assert names[0] == max(first.ratings, key=lambda item: (item[1],))[0]
        assert "Linh Tran" in names
        ratings = snap_a["ratings"]
        assert isinstance(ratings, list)
        assert sum(rating for _name, rating, _highest in ratings) == 8 * 1500
        assert any(rating != 1500 for _name, rating, _highest in ratings)
        assert all(highest >= max(1500, rating) for _name, rating, highest in ratings)
        icons = {icon for _name, icon, _kind, _value in snap_a["achievements"]}
        assert icons == {"trophy", "swords", "flame", "crown", "target"}
        _assert_badminton(snap_a)
        assert (
            db_a.scalar(
                select(func.count()).select_from(AuditLog).where(AuditLog.action == "match.create")
            )
            == first.completed + first.disputed + first.canceled
        )

        before = {
            player.display_name: (player.current_rating, player.highest_rating)
            for player in db_a.scalars(select(Player)).all()
        }
        recalculate_all(db_a)
        db_a.expire_all()
        after = {
            player.display_name: (player.current_rating, player.highest_rating)
            for player in db_a.scalars(select(Player)).all()
        }
        assert before == after

        with pytest.raises(SeedError, match="--reset"):
            seed_demo(db_a, now=_NOW)
        assert db_a.scalar(select(func.count()).select_from(Player)) == 8

        admin = AdminUser(
            auth_user_id=str(uuid.uuid4()),
            email="admin@example.com",
            display_name="Admin",
            is_active=True,
        )
        db_a.add(admin)
        db_a.commit()
        reset = seed_demo(db_a, reset=True, now=_NOW)
        assert reset.players == 8
        assert db_a.scalar(select(func.count()).select_from(Player)) == 8
        assert db_a.scalar(select(func.count()).select_from(AdminUser)) == 1
        assert _snapshot(db_a)["ratings"] == snap_a["ratings"]

        monkeypatch.setattr(settings, "APP_ENV", "production")
        with pytest.raises(SeedError, match="production"):
            seed_demo(db_a, reset=True, now=_NOW)
        assert db_a.scalar(select(func.count()).select_from(Player)) == 8
        assert db_a.scalar(select(func.count()).select_from(AdminUser)) == 1
    finally:
        db_a.close()
        db_b.close()
        engine_a.dispose()
        engine_b.dispose()


def test_seed_demo_cli_prints_summary_and_refuses_twice(
    tmp_path: Path,
) -> None:
    url = f"sqlite:///{tmp_path / 'cli.db'}"
    engine = make_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": url,
            "APP_ENV": "development",
            "AUTH_MODE": "dev",
            "DEV_ADMIN_TOKEN": "test-token",
            "ADMIN_BOOTSTRAP_USER_ID": "",
            "ADMIN_BOOTSTRAP_EMAIL": "",
        }
    )

    def run(
        *args: str, app_env: str = "development", auth_mode: str = "dev"
    ) -> subprocess.CompletedProcess[str]:
        command_env = env.copy()
        command_env["APP_ENV"] = app_env
        command_env["AUTH_MODE"] = auth_mode
        return subprocess.run(
            [sys.executable, "-m", "app.cli", *args],
            cwd=BACKEND_DIR,
            env=command_env,
            capture_output=True,
            text=True,
            check=False,
        )

    created = run("seed-demo")
    assert created.returncode == 0, created.stderr
    assert "Seeded demo club" in created.stdout
    assert "Linh Tran" in created.stdout

    again = run("seed-demo")
    assert again.returncode == 1
    assert "reset" in again.stderr.lower()

    blocked = run("seed-demo", "--reset", app_env="production", auth_mode="supabase")
    assert blocked.returncode == 1
    assert "production" in blocked.stderr.lower()

    check = make_engine(url)
    with Session(bind=check) as session:
        assert session.scalar(select(func.count()).select_from(Player)) == 8
    check.dispose()
