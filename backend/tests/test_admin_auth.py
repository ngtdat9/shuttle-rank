"""Every admin route rejects anonymous and wrong tokens, and accepts the dev token."""

import time
import uuid
from collections.abc import Generator

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.rate_limit import failed_auth_limiter

TEST_SECRET = "test-supabase-jwt-secret-32bytes"


@pytest.fixture(autouse=True)
def _reset_limiter() -> Generator[None, None, None]:
    failed_auth_limiter.reset()
    yield
    failed_auth_limiter.reset()


def _routes(player_id: str, match_id: str) -> list[tuple[str, str, dict[str, object]]]:
    other_id = str(uuid.uuid4())
    return [
        ("GET", "/api/v1/admin/me", {}),
        ("GET", "/api/v1/admin/stats", {}),
        ("GET", "/api/v1/admin/audit-logs", {}),
        ("GET", "/api/v1/admin/players", {}),
        ("POST", "/api/v1/admin/players", {"json": {"display_name": "Auth Probe"}}),
        ("PATCH", f"/api/v1/admin/players/{player_id}", {"json": {"display_name": "Renamed"}}),
        ("DELETE", f"/api/v1/admin/players/{player_id}", {}),
        ("GET", "/api/v1/admin/matches", {}),
        (
            "POST",
            "/api/v1/admin/matches",
            {
                "json": {
                    "player_a_id": player_id,
                    "player_b_id": other_id,
                    "winner_id": player_id,
                    "match_date": "2026-11-01T10:00:00Z",
                }
            },
        ),
        ("PATCH", f"/api/v1/admin/matches/{match_id}", {"json": {"notes": "later"}}),
        ("POST", f"/api/v1/admin/matches/{match_id}/correct", {"json": {"reason": "fix"}}),
        ("POST", f"/api/v1/admin/matches/{match_id}/cancel", {"json": {"reason": "rain"}}),
        ("DELETE", f"/api/v1/admin/matches/{match_id}?reason=duplicate", {}),
        ("POST", "/api/v1/admin/rankings/monthly/rebuild", {}),
    ]


def test_admin_routes_reject_missing_and_wrong_tokens(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _factory = api_client
    player_id = str(uuid.uuid4())
    match_id = str(uuid.uuid4())
    for method, path, kwargs in _routes(player_id, match_id):
        failed_auth_limiter.reset()
        missing = client.request(method, path, **kwargs)
        assert missing.status_code == 401, path
        assert missing.json()["error"]["code"] == "unauthorized"

        failed_auth_limiter.reset()
        wrong = client.request(
            method,
            path,
            headers={"Authorization": "Bearer not-the-dev-token"},
            **kwargs,
        )
        assert wrong.status_code == 401, path
        assert wrong.json()["error"]["code"] == "unauthorized"


def test_admin_routes_accept_the_dev_token(
    api_client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _factory = api_client
    headers = {"Authorization": f"Bearer {settings.DEV_ADMIN_TOKEN}"}

    for path in (
        "/api/v1/admin/me",
        "/api/v1/admin/stats",
        "/api/v1/admin/audit-logs",
        "/api/v1/admin/players",
        "/api/v1/admin/matches",
    ):
        response = client.get(path, headers=headers)
        assert response.status_code == 200, path

    amy = client.post("/api/v1/admin/players", json={"display_name": "Amy"}, headers=headers)
    bob = client.post("/api/v1/admin/players", json={"display_name": "Bob"}, headers=headers)
    assert amy.status_code == 201
    assert bob.status_code == 201
    amy_id = amy.json()["id"]
    bob_id = bob.json()["id"]

    renamed = client.patch(
        f"/api/v1/admin/players/{amy_id}",
        json={"display_name": "Amy Stone"},
        headers=headers,
    )
    assert renamed.status_code == 200

    created = client.post(
        "/api/v1/admin/matches",
        json={
            "player_a_id": amy_id,
            "player_b_id": bob_id,
            "winner_id": amy_id,
            "match_date": "2026-10-01T10:00:00Z",
        },
        headers=headers,
    )
    assert created.status_code == 201
    match_id = created.json()["id"]

    patched = client.patch(
        f"/api/v1/admin/matches/{match_id}",
        json={"notes": "club night"},
        headers=headers,
    )
    assert patched.status_code == 200
    corrected = client.post(
        f"/api/v1/admin/matches/{match_id}/correct",
        json={"winner_id": bob_id, "reason": "scorecard was reversed"},
        headers=headers,
    )
    assert corrected.status_code == 200
    canceled = client.post(
        f"/api/v1/admin/matches/{match_id}/cancel",
        json={"reason": "rain stopped play"},
        headers=headers,
    )
    assert canceled.status_code == 200
    deleted = client.delete(
        f"/api/v1/admin/matches/{match_id}",
        params={"reason": "entered twice"},
        headers=headers,
    )
    assert deleted.status_code == 200
    assert deleted.json() == {"id": match_id, "deleted": True}

    deactivated = client.delete(f"/api/v1/admin/players/{bob_id}", headers=headers)
    assert deactivated.status_code == 200
    rebuilt = client.post("/api/v1/admin/rankings/monthly/rebuild", headers=headers)
    assert rebuilt.status_code == 200
    assert "months_rebuilt" in rebuilt.json()


def test_non_admin_supabase_token_is_forbidden_on_a_write(
    api_client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _factory = api_client
    monkeypatch.setattr(settings, "AUTH_MODE", "supabase")
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_SECRET)
    monkeypatch.setattr(settings, "SUPABASE_JWT_AUDIENCE", "authenticated")
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "aud": "authenticated",
            "exp": int(time.time()) + 600,
        },
        TEST_SECRET,
        algorithm="HS256",
    )
    if isinstance(token, bytes):
        token = token.decode("ascii")
    response = client.post(
        "/api/v1/admin/players",
        json={"display_name": "Nope"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
