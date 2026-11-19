"""Independent QA of the achievement admin write API (docs/API.md, Admin -> Achievements)."""

import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from tests.qa.api_helpers import (  # noqa: F401  (autouse fixture)
    API,
    audit_actions,
    auth,
    make_players,
    reset_auth_limiter,
)

ApiClient = tuple[TestClient, sessionmaker[Session]]
ACHIEVEMENT_KEYS = {
    "id",
    "name",
    "description",
    "icon",
    "criteria_type",
    "criteria_value",
    "is_active",
    "awarded_count",
}


def _create(client: TestClient, name: str = "Streak", **extra: Any) -> dict[str, Any]:
    r = client.post(
        f"{API}/admin/achievements",
        json={"name": name, "description": "desc", **extra},
        headers=auth(),
    )
    assert r.status_code == 201, r.text
    return dict(r.json())


def _award(client: TestClient, player: str, ach: str, **extra: Any) -> Any:
    return client.post(
        f"{API}/admin/players/{player}/achievements",
        json={"achievement_id": ach, **extra},
        headers=auth(),
    )


def test_create_shape_validation_and_duplicate(api_client: ApiClient) -> None:
    client, _ = api_client
    a = _create(client, "Streak", icon="flame", criteria_type="win_streak", criteria_value=5)
    assert set(a) == ACHIEVEMENT_KEYS
    assert a["is_active"] is True and a["awarded_count"] == 0
    assert (a["icon"], a["criteria_type"], a["criteria_value"]) == ("flame", "win_streak", 5)
    plain = _create(client, "Plain")
    assert isinstance(plain["icon"], str) and isinstance(plain["criteria_type"], str)
    assert plain["criteria_value"] is None
    assert (
        client.post(
            f"{API}/admin/achievements", json={"name": "Streak", "description": "x"}, headers=auth()
        ).status_code
        == 409
    )
    for bad in (
        {"name": "", "description": "x"},
        {"name": "n" * 81, "description": "x"},
        {"name": "n", "description": ""},
        {"name": "n", "description": "d" * 301},
        {"name": "n"},
    ):
        r = client.post(f"{API}/admin/achievements", json=bad, headers=auth())
        assert r.status_code == 422, bad
        assert r.json()["error"]["code"] == "validation_error"


def test_patch_and_inactive_visibility(api_client: ApiClient) -> None:
    client, _ = api_client
    a = _create(client, "One")
    _create(client, "Two")
    r = client.patch(
        f"{API}/admin/achievements/{a['id']}",
        json={"description": "new", "is_active": False},
        headers=auth(),
    )
    assert r.status_code == 200
    assert r.json()["description"] == "new" and r.json()["is_active"] is False
    assert (
        client.patch(
            f"{API}/admin/achievements/{uuid.uuid4()}", json={"name": "z"}, headers=auth()
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"{API}/admin/achievements/{a['id']}", json={"name": "Two"}, headers=auth()
        ).status_code
        == 409
    )
    admin = client.get(f"{API}/admin/achievements", headers=auth()).json()["items"]
    assert {i["name"] for i in admin} == {"One", "Two"}
    assert [i["name"] for i in client.get(f"{API}/achievements").json()["items"]] == ["Two"]
    pub_all = client.get(f"{API}/achievements", params={"include_inactive": "true"}).json()["items"]
    assert {i["name"] for i in pub_all} == {"One", "Two"}


def test_award_rules_revoke_and_listing(api_client: ApiClient) -> None:
    client, _ = api_client
    ada, bob = make_players(client, 2)
    ach = _create(client, "Winner")
    retired = _create(client, "Retired")
    client.patch(
        f"{API}/admin/achievements/{retired['id']}", json={"is_active": False}, headers=auth()
    )

    r = _award(client, ada, ach["id"], notes="night one")
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body) == {"id", "player", "achievement", "awarded_at"}
    assert body["player"]["id"] == ada and body["achievement"]["id"] == ach["id"]
    assert body["achievement"]["awarded_count"] == 1

    assert _award(client, ada, ach["id"]).status_code == 409  # twice
    assert _award(client, bob, retired["id"]).status_code == 422  # inactive
    assert _award(client, bob, str(uuid.uuid4())).status_code == 404  # unknown achievement
    assert _award(client, str(uuid.uuid4()), ach["id"]).status_code == 404  # unknown player
    assert _award(client, bob, ach["id"]).status_code == 201  # same achievement, other player

    page = client.get(
        f"{API}/admin/player-achievements", params={"page_size": 1}, headers=auth()
    ).json()
    assert page["total"] == 2 and len(page["items"]) == 1 and page["page_size"] == 1
    allp = client.get(f"{API}/admin/player-achievements", headers=auth()).json()
    row = next(i for i in allp["items"] if i["player"]["id"] == ada)
    assert row["notes"] == "night one" and row["awarded_by"]
    assert row["id"] == body["id"]

    # public player page lists the award
    prof = client.get(f"{API}/players/{ada}/achievements").json()["items"]
    assert [x["achievement"]["id"] for x in prof] == [ach["id"]]

    # revoke
    d = client.delete(f"{API}/admin/player-achievements/{body['id']}", headers=auth())
    assert d.status_code == 200 and d.json() == {"id": body["id"], "deleted": True}
    assert (
        client.delete(f"{API}/admin/player-achievements/{body['id']}", headers=auth()).status_code
        == 404
    )
    assert client.get(f"{API}/admin/player-achievements", headers=auth()).json()["total"] == 1
    assert client.get(f"{API}/players/{ada}/achievements").json()["items"] == []
    # re-award after revoke is allowed again
    assert _award(client, ada, ach["id"]).status_code == 201
    counts = {
        i["id"]: i["awarded_count"]
        for i in client.get(f"{API}/admin/achievements", headers=auth()).json()["items"]
    }
    assert counts[ach["id"]] == 2


def test_audit_action_names(api_client: ApiClient) -> None:
    client, _ = api_client
    (ada,) = make_players(client, 1)
    a = _create(client, "Audit")
    client.patch(f"{API}/admin/achievements/{a['id']}", json={"description": "x"}, headers=auth())
    aw = _award(client, ada, a["id"]).json()
    client.delete(f"{API}/admin/player-achievements/{aw['id']}", headers=auth())
    for action in (
        "achievement.create",
        "achievement.update",
        "achievement.award",
        "achievement.revoke",
    ):
        entries = audit_actions(client, action)
        assert len(entries) == 1, action
        assert entries[0]["actor_id"]
    assert audit_actions(client, "achievement.update")[0]["before_data"]["description"] == "desc"
    assert audit_actions(client, "achievement.update")[0]["after_data"]["description"] == "x"
    # failed writes leave no audit entry
    _award(client, ada, str(uuid.uuid4()))
    assert len(audit_actions(client, "achievement.award")) == 1
