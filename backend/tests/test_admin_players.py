"""Admin player create, update, deactivate, and reactivation."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.DEV_ADMIN_TOKEN}"}


def _create(client: TestClient, name: str, **extra: object) -> object:
    return client.post(
        "/api/v1/admin/players",
        json={"display_name": name, **extra},
        headers=_headers(),
    )


def test_player_crud_deactivation_and_reactivation(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _factory = api_client
    headers = _headers()
    created = _create(client, "  Amy  ")
    assert created.status_code == 201
    body = created.json()
    assert body["display_name"] == "Amy"
    assert body["current_rating"] == 1500
    assert body["highest_rating"] == 1500
    assert body["is_active"] is True
    assert body["rank"] == 1
    assert "stats" in body
    amy_id = body["id"]

    duplicate = _create(client, "amy")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"

    bob = _create(client, "Bob")
    assert bob.status_code == 201
    bob_id = bob.json()["id"]
    played = client.post(
        "/api/v1/admin/matches",
        json={
            "player_a_id": amy_id,
            "player_b_id": bob_id,
            "winner_id": amy_id,
            "match_date": "2026-10-01T10:00:00Z",
            "game_scores": [[21, 15], [21, 18]],
        },
        headers=headers,
    )
    assert played.status_code == 201
    rating_before = client.get(f"/api/v1/players/{amy_id}").json()["current_rating"]
    assert rating_before != 1500

    renamed = client.patch(
        f"/api/v1/admin/players/{amy_id}",
        json={"display_name": "Amy Stone", "avatar_url": "https://example.com/a.png"},
        headers=headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["display_name"] == "Amy Stone"
    assert renamed.json()["avatar_url"] == "https://example.com/a.png"
    assert renamed.json()["current_rating"] == rating_before

    deactivated = client.delete(f"/api/v1/admin/players/{amy_id}", headers=headers)
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert deactivated.json()["rank"] is None
    assert deactivated.json()["current_rating"] == rating_before

    history = client.get(f"/api/v1/players/{amy_id}/matches")
    assert history.status_code == 200
    assert history.json()["total"] == 1
    ratings = client.get(f"/api/v1/players/{amy_id}/rating-history")
    assert len(ratings.json()["points"]) == 1
    board = client.get("/api/v1/rankings").json()
    assert "Amy Stone" not in {row["player"]["display_name"] for row in board["items"]}
    included = client.get("/api/v1/rankings", params={"include_inactive": True}).json()
    assert "Amy Stone" in {row["player"]["display_name"] for row in included["items"]}

    directory = client.get("/api/v1/admin/players", headers=headers).json()
    listed = {item["display_name"]: item for item in directory["items"]}
    assert listed["Amy Stone"]["is_active"] is False
    assert listed["Bob"]["is_active"] is True

    reactivated = client.patch(
        f"/api/v1/admin/players/{amy_id}",
        json={"is_active": True},
        headers=headers,
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True
    assert reactivated.json()["rank"] is not None
    assert reactivated.json()["current_rating"] == rating_before
    board = client.get("/api/v1/rankings").json()
    assert "Amy Stone" in {row["player"]["display_name"] for row in board["items"]}

    logs = client.get("/api/v1/admin/audit-logs", headers=headers, params={"page_size": 100})
    assert logs.status_code == 200
    rows = logs.json()["items"]
    created_log = next(
        row
        for row in rows
        if row["action"] == "player.create" and row["after_data"]["display_name"] == "Amy"
    )
    assert created_log["actor_id"] == "dev-admin"
    assert created_log["before_data"] is None
    assert created_log["after_data"]["display_name"] == "Amy"
    updated = next(
        row
        for row in rows
        if row["action"] == "player.update"
        and row["entity_id"] == amy_id
        and row["before_data"]["display_name"] == "Amy"
    )
    assert updated["before_data"]["display_name"] == "Amy"
    assert updated["after_data"]["display_name"] == "Amy Stone"
    deactivated_log = next(row for row in rows if row["action"] == "player.deactivate")
    assert deactivated_log["before_data"]["is_active"] is True
    assert deactivated_log["after_data"]["is_active"] is False
    reactivated_log = next(
        row
        for row in rows
        if row["action"] == "player.update" and row["after_data"]["is_active"] is True
    )
    assert reactivated_log["before_data"]["is_active"] is False


def test_rating_fields_and_empty_update_are_rejected(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _factory = api_client
    headers = _headers()
    for field in ("current_rating", "highest_rating"):
        rejected = client.post(
            "/api/v1/admin/players",
            json={"display_name": "Zoe", field: 1800},
            headers=headers,
        )
        assert rejected.status_code == 422
        assert rejected.json()["error"]["code"] == "validation_error"
    assert client.get("/api/v1/admin/players", headers=headers).json()["items"] == []

    created = _create(client, "Zoe")
    assert created.status_code == 201
    player_id = created.json()["id"]
    empty = client.patch(f"/api/v1/admin/players/{player_id}", json={}, headers=headers)
    assert empty.status_code == 422
    assert empty.json()["error"]["code"] == "business_rule_violation"
    rated = client.patch(
        f"/api/v1/admin/players/{player_id}",
        json={"current_rating": 1800},
        headers=headers,
    )
    assert rated.status_code == 422
    assert rated.json()["error"]["code"] == "validation_error"
    assert client.get(f"/api/v1/players/{player_id}").json()["current_rating"] == 1500
