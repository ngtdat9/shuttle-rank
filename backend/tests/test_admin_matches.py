"""Admin match writes, replay, and audit rows."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.services.elo import apply_result


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.DEV_ADMIN_TOKEN}"}


def _player(client: TestClient, name: str) -> str:
    response = client.post(
        "/api/v1/admin/players",
        json={"display_name": name},
        headers=_headers(),
    )
    assert response.status_code == 201
    return response.json()["id"]


def _match(
    client: TestClient,
    player_a: str,
    player_b: str,
    winner: str,
    when: str,
    **extra: object,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/admin/matches",
        json={
            "player_a_id": player_a,
            "player_b_id": player_b,
            "winner_id": winner,
            "match_date": when,
            **extra,
        },
        headers=_headers(),
    )
    assert response.status_code == 201, response.json()
    return response.json()


def test_create_patch_correct_cancel_and_delete_replay(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _factory = api_client
    headers = _headers()
    amy = _player(client, "Amy")
    bob = _player(client, "Bob")

    later = _match(client, amy, bob, amy, "2026-11-01T10:00:00Z", game_scores=[[21, 14], [21, 17]])
    assert later["status"] == "completed"
    assert {row["rating_change"] for row in later["rating_changes"]} == {16, -16}
    earlier = _match(client, amy, bob, bob, "2026-10-01T10:00:00Z")
    history = client.get(f"/api/v1/players/{amy}/rating-history").json()
    points = history["points"]
    assert [point["old_rating"] for point in points][0] == 1500
    assert points[0]["match_id"] == earlier["id"]
    assert points[1]["old_rating"] == points[0]["new_rating"]
    assert points[0]["result"] == "L"
    assert points[1]["result"] == "W"

    rating_before_patch = client.get(f"/api/v1/players/{amy}").json()["current_rating"]
    patched = client.patch(
        f"/api/v1/admin/matches/{later['id']}",
        json={"notes": "long rally", "game_scores": [[21, 19], [18, 21], [21, 16]]},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["notes"] == "long rally"
    assert patched.json()["game_scores"] == [[21, 19], [18, 21], [21, 16]]
    assert client.get(f"/api/v1/players/{amy}").json()["current_rating"] == rating_before_patch

    missing_reason = client.post(
        f"/api/v1/admin/matches/{earlier['id']}/correct",
        json={"winner_id": amy},
        headers=headers,
    )
    assert missing_reason.status_code == 422
    assert missing_reason.json()["error"]["code"] == "validation_error"

    corrected = client.post(
        f"/api/v1/admin/matches/{earlier['id']}/correct",
        json={"winner_id": amy, "reason": "wrong winner"},
        headers=headers,
    )
    assert corrected.status_code == 200
    assert corrected.json()["winner_id"] == amy
    replayed = client.get(f"/api/v1/players/{amy}/rating-history").json()["points"]
    # Both matches are now Amy wins, processed oldest first from 1500.
    first = apply_result(1500, 1500)
    second = apply_result(first.winner_new, first.loser_new)
    assert replayed[0]["rating_change"] == first.delta
    assert replayed[0]["new_rating"] == first.winner_new
    assert replayed[1]["old_rating"] == first.winner_new
    assert replayed[1]["new_rating"] == second.winner_new
    board = client.get("/api/v1/rankings").json()["items"]
    assert board[0]["player"]["id"] == amy
    assert board[0]["rating"] == second.winner_new

    canceled = client.post(
        f"/api/v1/admin/matches/{later['id']}/cancel",
        json={"reason": "retired hurt"},
        headers=headers,
    )
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"
    assert canceled.json()["rating_changes"] == []
    after_cancel = client.get(f"/api/v1/players/{amy}/rating-history").json()["points"]
    assert len(after_cancel) == 1
    assert after_cancel[0]["new_rating"] == first.winner_new
    assert client.get(f"/api/v1/players/{amy}").json()["current_rating"] == first.winner_new

    removed = client.delete(
        f"/api/v1/admin/matches/{earlier['id']}",
        params={"reason": "duplicate entry"},
        headers=headers,
    )
    assert removed.status_code == 200
    assert removed.json() == {"id": earlier["id"], "deleted": True}
    assert client.get(f"/api/v1/matches/{earlier['id']}").status_code == 404
    assert client.get(f"/api/v1/players/{amy}").json()["current_rating"] == 1500
    assert client.get(f"/api/v1/players/{amy}/rating-history").json()["points"] == []

    hidden = client.get("/api/v1/admin/matches", headers=headers).json()
    assert earlier["id"] not in {item["id"] for item in hidden["items"]}
    visible = client.get(
        "/api/v1/admin/matches",
        headers=headers,
        params={"include_deleted": True, "status": "all"},
    ).json()
    assert earlier["id"] in {item["id"] for item in visible["items"]}
    assert {item["status"] for item in hidden["items"]} == {"canceled"}

    logs = client.get(
        "/api/v1/admin/audit-logs",
        headers=headers,
        params={"entity_type": "match", "page_size": 100},
    ).json()["items"]
    by_action = {row["action"]: row for row in logs}
    assert by_action["match.create"]["before_data"] is None
    assert by_action["match.create"]["actor_id"] == "dev-admin"
    assert by_action["match.update"]["before_data"]["notes"] is None
    assert by_action["match.update"]["after_data"]["notes"] == "long rally"
    assert by_action["match.correct"]["before_data"]["winner_id"] == bob
    assert by_action["match.correct"]["after_data"]["winner_id"] == amy
    assert by_action["match.correct"]["after_data"]["reason"] == "wrong winner"
    assert by_action["match.cancel"]["after_data"]["status"] == "canceled"
    assert by_action["match.cancel"]["before_data"]["status"] == "completed"
    assert by_action["match.delete"]["after_data"]["deleted"] is True
    assert by_action["match.delete"]["before_data"]["deleted_at"] is None


def test_match_write_bodies_reject_rating_fields_and_tournament_id(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _factory = api_client
    headers = _headers()
    amy = _player(client, "Amy")
    bob = _player(client, "Bob")
    base = {
        "player_a_id": amy,
        "player_b_id": bob,
        "winner_id": amy,
        "match_date": "2026-10-02T10:00:00Z",
    }
    for field, value in (
        ("current_rating", 1700),
        ("highest_rating", 1700),
        ("rating_change", 16),
        ("tournament_id", amy),
    ):
        rejected = client.post(
            "/api/v1/admin/matches",
            json={**base, field: value},
            headers=headers,
        )
        assert rejected.status_code == 422, field
        assert rejected.json()["error"]["code"] == "validation_error"

    self_match = client.post(
        "/api/v1/admin/matches",
        json={**base, "player_b_id": amy, "winner_id": amy},
        headers=headers,
    )
    assert self_match.status_code == 422
    assert self_match.json()["error"]["code"] == "business_rule_violation"
    unknown = client.post(
        "/api/v1/admin/matches",
        json={**base, "player_b_id": "11111111-1111-4111-8111-111111111111"},
        headers=headers,
    )
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "business_rule_violation"
    assert client.get("/api/v1/admin/matches", headers=headers).json()["total"] == 0
