"""HTTP-only helpers for black-box QA tests of the admin write API."""

from collections.abc import Iterator
from itertools import count
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limit import failed_auth_limiter

API = "/api/v1"
_days = count(1)


@pytest.fixture(autouse=True)
def reset_auth_limiter() -> Iterator[None]:
    failed_auth_limiter.reset()
    yield
    failed_auth_limiter.reset()


def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.DEV_ADMIN_TOKEN}"}


def next_date() -> str:
    k = next(_days)  # strictly increasing, so insertion order equals chronological order
    return f"2026-10-{k // 20 + 1:02d}T{k % 20:02d}:30:00Z"


def make_players(client: TestClient, n: int, prefix: str = "Q") -> list[str]:
    ids = []
    for i in range(1, n + 1):
        r = client.post(
            f"{API}/admin/players", json={"display_name": f"{prefix}{i}"}, headers=auth()
        )
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    return ids


def ratings(client: TestClient) -> dict[str, int]:
    body = client.get(f"{API}/rankings", params={"page_size": 100}).json()
    return {e["player"]["id"]: e["rating"] for e in body["items"]}


def club_match(client: TestClient, a: str, b: str, winner: str) -> dict[str, Any]:
    r = client.post(
        f"{API}/admin/matches",
        json={"player_a_id": a, "player_b_id": b, "winner_id": winner, "match_date": next_date()},
        headers=auth(),
    )
    assert r.status_code == 201, r.text
    return dict(r.json())


def make_tournament(
    client: TestClient, players: list[str] | None = None, name: str = "Open"
) -> str:
    r = client.post(f"{API}/admin/tournaments", json={"name": name}, headers=auth())
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "draft"
    tid = str(r.json()["id"])
    if players:
        add = client.post(
            f"{API}/admin/tournaments/{tid}/participants",
            json={"participants": [{"player_id": p} for p in players]},
            headers=auth(),
        )
        assert add.status_code == 200, add.text
    return tid


def generate(client: TestClient, tid: str, **body: Any) -> Any:
    return client.post(f"{API}/admin/tournaments/{tid}/generate-bracket", json=body, headers=auth())


def bracket(client: TestClient, tid: str) -> dict[str, Any]:
    r = client.get(f"{API}/tournaments/{tid}/bracket")
    assert r.status_code == 200
    return dict(r.json())


def detail(client: TestClient, tid: str) -> dict[str, Any]:
    r = client.get(f"{API}/tournaments/{tid}")
    assert r.status_code == 200
    return dict(r.json())


def slots(br: dict[str, Any]) -> list[dict[str, Any]]:
    return [m for rnd in br["rounds"] for m in rnd["matches"]]


def slot(br: dict[str, Any], rnd: int, pos: int) -> dict[str, Any]:
    for r in br["rounds"]:
        if r["round"] == rnd:
            return next(m for m in r["matches"] if m["position"] == pos)
    raise AssertionError("no such round")


def record(client: TestClient, tid: str, bm: dict[str, Any], winner_id: str | None = None) -> Any:
    winner = winner_id or bm["player_a"]["id"]
    return client.post(
        f"{API}/admin/tournaments/{tid}/matches",
        json={"bracket_match_id": bm["id"], "winner_id": winner, "match_date": next_date()},
        headers=auth(),
    )


def play_out(client: TestClient, tid: str) -> None:
    """Record every ready match (player A wins) until nothing is ready."""
    while True:
        ready = [m for m in slots(bracket(client, tid)) if m["status"] == "ready"]
        if not ready:
            return
        r = record(client, tid, ready[0])
        assert r.status_code == 201, r.text


def audit_actions(client: TestClient, action: str) -> list[dict[str, Any]]:
    r = client.get(
        f"{API}/admin/audit-logs", params={"action": action, "page_size": 100}, headers=auth()
    )
    assert r.status_code == 200
    return list(r.json()["items"])
