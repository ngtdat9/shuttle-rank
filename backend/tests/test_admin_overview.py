"""Admin stats, audit-log filters, and monthly rebuild."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.player import Player
from tests.factories import award, make_achievement, make_tournament


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.DEV_ADMIN_TOKEN}"}


def test_admin_stats_count_players_matches_and_awards(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, factory = api_client
    headers = _headers()
    empty = client.get("/api/v1/admin/stats", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["players_total"] == 0
    assert empty.json()["matches_total"] == 0
    assert empty.json()["last_match_at"] is None

    amy = client.post("/api/v1/admin/players", json={"display_name": "Amy"}, headers=headers)
    bob = client.post("/api/v1/admin/players", json={"display_name": "Bob"}, headers=headers)
    assert amy.status_code == 201 and bob.status_code == 201
    amy_id = amy.json()["id"]
    bob_id = bob.json()["id"]

    def play(when: str, status: str = "completed") -> str:
        response = client.post(
            "/api/v1/admin/matches",
            json={
                "player_a_id": amy_id,
                "player_b_id": bob_id,
                "winner_id": amy_id,
                "match_date": when,
                "status": status,
            },
            headers=headers,
        )
        assert response.status_code == 201
        return response.json()["id"]

    play("2026-10-01T10:00:00Z")
    play("2026-10-02T10:00:00Z", "disputed")
    canceled_id = play("2026-10-03T15:00:00Z")
    canceled = client.post(
        f"/api/v1/admin/matches/{canceled_id}/cancel",
        json={"reason": "rain"},
        headers=headers,
    )
    assert canceled.status_code == 200
    client.delete(f"/api/v1/admin/players/{bob_id}", headers=headers)

    db = factory()
    try:
        player = db.get(Player, UUID(amy_id))
        assert player is not None
        make_tournament(db, "City Open", status="in_progress")
        make_tournament(db, "Draft Cup", status="draft")
        badge = make_achievement(db, "First Win", icon="trophy")
        award(db, player, badge)
    finally:
        db.close()

    stats = client.get("/api/v1/admin/stats", headers=headers).json()
    assert stats["players_total"] == 2
    assert stats["players_active"] == 1
    assert stats["matches_completed"] == 1
    assert stats["matches_disputed"] == 1
    assert stats["matches_canceled"] == 1
    assert stats["matches_total"] == 3
    assert stats["tournaments_total"] == 2
    assert stats["tournaments_in_progress"] == 1
    assert stats["achievements_awarded"] == 1
    assert stats["last_match_at"].startswith("2026-10-03")


def test_audit_log_filters_pagination_and_monthly_rebuild(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _factory = api_client
    headers = _headers()
    for name in ("Amy", "Bob", "Cara"):
        created = client.post(
            "/api/v1/admin/players",
            json={"display_name": name},
            headers=headers,
        )
        assert created.status_code == 201
    amy = client.get("/api/v1/admin/players", headers=headers).json()["items"]
    ids = {item["display_name"]: item["id"] for item in amy}
    played = client.post(
        "/api/v1/admin/matches",
        json={
            "player_a_id": ids["Amy"],
            "player_b_id": ids["Bob"],
            "winner_id": ids["Amy"],
            "match_date": "2026-10-04T10:00:00Z",
        },
        headers=headers,
    )
    assert played.status_code == 201

    creates = client.get(
        "/api/v1/admin/audit-logs",
        headers=headers,
        params={"entity_type": "player", "action": "player.create", "page_size": 1, "page": 1},
    )
    assert creates.status_code == 200
    first = creates.json()
    assert first["total"] == 3
    assert first["page"] == 1
    assert len(first["items"]) == 1
    assert first["items"][0]["action"] == "player.create"
    second = client.get(
        "/api/v1/admin/audit-logs",
        headers=headers,
        params={"entity_type": "player", "action": "player.create", "page_size": 1, "page": 2},
    ).json()
    assert second["total"] == 3
    assert second["items"][0]["id"] != first["items"][0]["id"]
    assert first["items"][0]["created_at"] >= second["items"][0]["created_at"]

    none = client.get(
        "/api/v1/admin/audit-logs",
        headers=headers,
        params={"entity_type": "match", "action": "player.create"},
    ).json()
    assert none["total"] == 0
    assert none["items"] == []

    match_logs = client.get(
        "/api/v1/admin/audit-logs",
        headers=headers,
        params={"entity_type": "match"},
    ).json()
    assert match_logs["total"] == 1
    assert match_logs["items"][0]["action"] == "match.create"

    rebuilt = client.post("/api/v1/admin/rankings/monthly/rebuild", headers=headers)
    assert rebuilt.status_code == 200
    assert rebuilt.json()["months_rebuilt"] >= 1
    rebuild_logs = client.get(
        "/api/v1/admin/audit-logs",
        headers=headers,
        params={"action": "rankings.monthly_rebuild"},
    ).json()
    assert rebuild_logs["total"] == 1
    assert rebuild_logs["items"][0]["entity_type"] == "rankings"
    assert (
        rebuild_logs["items"][0]["after_data"]["months_rebuilt"] == rebuilt.json()["months_rebuilt"]
    )
    assert rebuild_logs["items"][0]["before_data"] is None
    assert rebuild_logs["items"][0]["actor_id"] == "dev-admin"
