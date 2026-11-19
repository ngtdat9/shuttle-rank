"""Achievement admin API: definitions, awards, revocation, audit."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.rate_limit import failed_auth_limiter
from app.models.audit_log import AuditLog

ApiClient = tuple[TestClient, sessionmaker[Session]]


@pytest.fixture(autouse=True)
def _reset_auth_limiter() -> Iterator[None]:
    failed_auth_limiter.reset()
    yield
    failed_auth_limiter.reset()


def _h() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.DEV_ADMIN_TOKEN}"}


def _player(client: TestClient, name: str = "Ada") -> str:
    response = client.post("/api/v1/admin/players", json={"display_name": name}, headers=_h())
    return str(response.json()["id"])


def _achievement(client: TestClient, name: str = "First Win", **extra: Any) -> dict[str, Any]:
    response = client.post(
        "/api/v1/admin/achievements",
        json={"name": name, "description": "Win a match", **extra},
        headers=_h(),
    )
    assert response.status_code == 201, response.json()
    return dict(response.json())


def test_create_defaults_duplicate_and_validation(api_client: ApiClient) -> None:
    client, _ = api_client
    created = _achievement(client, "  First Win ")
    assert created["name"] == "First Win"
    assert created["icon"] == "award" and created["criteria_type"] == "manual"
    assert created["criteria_value"] is None and created["is_active"] is True
    assert created["awarded_count"] == 0
    full = _achievement(client, "Streak", icon="flame", criteria_type="streak", criteria_value=3)
    assert (full["icon"], full["criteria_type"], full["criteria_value"]) == ("flame", "streak", 3)
    dup = client.post(
        "/api/v1/admin/achievements",
        json={"name": "first win", "description": "x"},
        headers=_h(),
    )
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "conflict"
    for bad in (
        {"name": "", "description": "x"},
        {"name": "n" * 81, "description": "x"},
        {"name": "n", "description": ""},
        {"name": "n", "description": "d" * 301},
        {"name": "n", "description": "x", "is_active": False},
    ):
        response = client.post("/api/v1/admin/achievements", json=bad, headers=_h())
        assert response.status_code == 422, bad


def test_patch_and_listing_includes_inactive(api_client: ApiClient) -> None:
    client, factory = api_client
    first = _achievement(client, "A")
    _achievement(client, "B")
    patched = client.patch(
        f"/api/v1/admin/achievements/{first['id']}",
        json={"is_active": False, "criteria_value": 5, "description": "New"},
        headers=_h(),
    )
    assert patched.status_code == 200
    assert patched.json()["is_active"] is False and patched.json()["criteria_value"] == 5
    clash = client.patch(
        f"/api/v1/admin/achievements/{first['id']}", json={"name": "b"}, headers=_h()
    )
    assert clash.status_code == 409
    same = client.patch(
        f"/api/v1/admin/achievements/{first['id']}", json={"name": "A"}, headers=_h()
    )
    assert same.status_code == 200
    assert (
        client.patch(f"/api/v1/admin/achievements/{first['id']}", json={}, headers=_h()).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/v1/admin/achievements/{first['id']}", json={"name": None}, headers=_h()
        ).status_code
        == 422
    )
    missing = client.patch(
        "/api/v1/admin/achievements/00000000-0000-0000-0000-000000000000",
        json={"name": "z"},
        headers=_h(),
    )
    assert missing.status_code == 404
    admin_list = client.get("/api/v1/admin/achievements", headers=_h()).json()["items"]
    assert [item["name"] for item in admin_list] == ["A", "B"]
    public = client.get("/api/v1/achievements").json()["items"]
    assert [item["name"] for item in public] == ["B"]
    with factory() as db:
        updates = list(db.scalars(select(AuditLog).where(AuditLog.action == "achievement.update")))
    assert len(updates) == 2
    assert (
        updates[0].before_data["is_active"] is True and updates[0].after_data["is_active"] is False
    )


def test_award_duplicate_inactive_list_and_revoke(api_client: ApiClient) -> None:
    client, factory = api_client
    ada = _player(client, "Ada")
    bob = _player(client, "Bob")
    win = _achievement(client, "First Win")
    retired = _achievement(client, "Retired")
    client.patch(
        f"/api/v1/admin/achievements/{retired['id']}", json={"is_active": False}, headers=_h()
    )

    awarded = client.post(
        f"/api/v1/admin/players/{ada}/achievements",
        json={"achievement_id": win["id"], "notes": "opening night"},
        headers=_h(),
    )
    assert awarded.status_code == 201, awarded.json()
    body = awarded.json()
    assert set(body) == {"id", "player", "achievement", "awarded_at"}
    assert body["player"]["id"] == ada and body["achievement"]["awarded_count"] == 1

    again = client.post(
        f"/api/v1/admin/players/{ada}/achievements",
        json={"achievement_id": win["id"]},
        headers=_h(),
    )
    assert again.status_code == 409
    inactive = client.post(
        f"/api/v1/admin/players/{bob}/achievements",
        json={"achievement_id": retired["id"]},
        headers=_h(),
    )
    assert inactive.status_code == 422
    no_player = client.post(
        "/api/v1/admin/players/00000000-0000-0000-0000-000000000000/achievements",
        json={"achievement_id": win["id"]},
        headers=_h(),
    )
    assert no_player.status_code == 404
    extra_field = client.post(
        f"/api/v1/admin/players/{bob}/achievements",
        json={"achievement_id": win["id"], "awarded_by": "me"},
        headers=_h(),
    )
    assert extra_field.status_code == 422
    # A different player may receive the same achievement.
    second = client.post(
        f"/api/v1/admin/players/{bob}/achievements",
        json={"achievement_id": win["id"]},
        headers=_h(),
    )
    assert second.status_code == 201

    page = client.get(
        "/api/v1/admin/player-achievements", params={"page_size": 1}, headers=_h()
    ).json()
    assert page["total"] == 2 and page["page_size"] == 1 and len(page["items"]) == 1
    assert page["items"][0]["awarded_by"] == "dev-admin"
    assert page["items"][0]["player"]["display_name"] == "Bob"  # newest first
    both = client.get("/api/v1/admin/player-achievements", headers=_h()).json()
    ada_award = next(item for item in both["items"] if item["player"]["id"] == ada)
    assert ada_award["notes"] == "opening night"
    assert (
        client.get(
            "/api/v1/admin/player-achievements", params={"page_size": 101}, headers=_h()
        ).status_code
        == 422
    )

    revoked = client.delete(f"/api/v1/admin/player-achievements/{ada_award['id']}", headers=_h())
    assert revoked.status_code == 200 and revoked.json() == {"id": ada_award["id"], "deleted": True}
    assert (
        client.delete(
            f"/api/v1/admin/player-achievements/{ada_award['id']}", headers=_h()
        ).status_code
        == 404
    )
    assert client.get(f"/api/v1/players/{ada}/achievements").json()["items"] == []
    # Revoked awards can be granted again.
    regrant = client.post(
        f"/api/v1/admin/players/{ada}/achievements",
        json={"achievement_id": win["id"]},
        headers=_h(),
    )
    assert regrant.status_code == 201
    with factory() as db:
        actions = [row.action for row in db.scalars(select(AuditLog).order_by(AuditLog.created_at))]
        revoke = db.scalar(select(AuditLog).where(AuditLog.action == "achievement.revoke"))
    assert actions.count("achievement.create") == 2
    assert actions.count("achievement.award") == 3
    assert actions.count("achievement.revoke") == 1
    assert revoke is not None and revoke.before_data["notes"] == "opening night"
