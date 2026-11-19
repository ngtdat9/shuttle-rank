"""CLI admin allowlist commands against a temporary database."""

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.cli import main
from app.core.config import settings
from app.db.base import Base
from app.db.session import make_engine
from app.models.admin_user import AdminUser

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _prepare_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    url = f"sqlite:///{tmp_path / 'cli.db'}"
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    engine = make_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()


def test_cli_module_creates_lists_and_deactivates(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'module.db'}"
    engine = make_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()
    user_id = str(uuid.uuid4())
    env = os.environ.copy()
    env["DATABASE_URL"] = url
    env["ADMIN_BOOTSTRAP_USER_ID"] = ""
    env["ADMIN_BOOTSTRAP_EMAIL"] = ""

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "app.cli", *args],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    created = run(
        "create-admin",
        "--auth-user-id",
        user_id,
        "--email",
        "ada@example.com",
        "--display-name",
        "Ada",
    )
    assert created.returncode == 0, created.stderr
    assert user_id in created.stdout

    listed = run("list-admins")
    assert listed.returncode == 0, listed.stderr
    assert f"{user_id}\tada@example.com\tAda\tactive" in listed.stdout

    deactivated = run("deactivate-admin", "--auth-user-id", user_id)
    assert deactivated.returncode == 0, deactivated.stderr

    after = run("list-admins")
    assert after.returncode == 0, after.stderr
    assert f"{user_id}\tada@example.com\tAda\tinactive" in after.stdout

    check = make_engine(url)
    with Session(bind=check) as session:
        admin = session.scalars(select(AdminUser)).one()
        assert admin.is_active is False
        assert admin.auth_user_id == user_id
    check.dispose()


def test_cli_create_is_idempotent_and_validates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _prepare_db(tmp_path, monkeypatch)
    user_id = str(uuid.uuid4())
    other_id = str(uuid.uuid4())

    assert main(["list-admins"]) == 0
    assert capsys.readouterr().out.strip() == "No admins."

    assert (
        main(
            [
                "create-admin",
                "--auth-user-id",
                user_id.upper(),
                "--email",
                "ada@example.com",
                "--display-name",
                "Ada",
            ]
        )
        == 0
    )
    assert "Created admin" in capsys.readouterr().out

    assert (
        main(
            [
                "create-admin",
                "--auth-user-id",
                user_id,
                "--email",
                "ada.updated@example.com",
            ]
        )
        == 0
    )
    assert "Updated admin" in capsys.readouterr().out
    listed = main(["list-admins"])
    assert listed == 0
    output = capsys.readouterr().out
    assert f"{user_id}\tada.updated@example.com\tAda\tactive" in output

    assert (
        main(
            [
                "create-admin",
                "--auth-user-id",
                other_id,
                "--email",
                "ada.updated@example.com",
            ]
        )
        == 1
    )
    assert "already used" in capsys.readouterr().err

    assert main(["create-admin", "--auth-user-id", "not-a-uuid", "--email", "a@example.com"]) == 1
    assert "UUID" in capsys.readouterr().err

    assert (
        main(["create-admin", "--auth-user-id", str(uuid.uuid4()), "--email", "not-an-email"]) == 1
    )
    assert "email" in capsys.readouterr().err

    missing = str(uuid.uuid4())
    assert main(["deactivate-admin", "--auth-user-id", missing]) == 1
    assert missing in capsys.readouterr().err
