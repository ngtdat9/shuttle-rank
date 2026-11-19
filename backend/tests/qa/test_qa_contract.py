"""P6-01: OpenAPI vs docs/API.md, request-schema hygiene, and the error envelope."""

import re
import uuid
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from tests.qa.api_helpers import (  # noqa: F401
    API,
    auth,
    club_match,
    make_players,
    make_tournament,
    reset_auth_limiter,
)

API_MD = Path(__file__).resolve().parents[3] / "docs" / "API.md"
FORBIDDEN_FIELDS = {"current_rating", "highest_rating", "rating", "elo", "rating_change"}
Client = tuple[TestClient, sessionmaker[Session]]


def _norm(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "{}", path)


def _documented() -> set[tuple[str, str]]:
    text = API_MD.read_text()
    found = set()
    for method, path in re.findall(r"`(GET|POST|PATCH|PUT|DELETE) (/[^`\s?]*)", text):
        found.add((method, _norm("/api/v1" + path)))
    return found


def _implemented() -> set[tuple[str, str]]:
    out = set()
    for path, item in app.openapi()["paths"].items():
        for method in item:
            if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                out.add((method.upper(), _norm(path)))
    return out


def test_documented_endpoints_were_parsed() -> None:
    assert len(_documented()) >= 35


def test_every_documented_endpoint_is_implemented() -> None:
    missing = sorted(_documented() - _implemented())
    assert not missing, f"documented in API.md but absent from OpenAPI: {missing}"


def test_no_undocumented_endpoint_is_implemented() -> None:
    extra = sorted(_implemented() - _documented())
    assert not extra, f"in OpenAPI but absent from API.md: {extra}"


def _walk_request_schemas() -> dict[str, dict[str, Any]]:
    doc = app.openapi()
    schemas = doc["components"]["schemas"]
    names: set[str] = set()
    for item in doc["paths"].values():
        for op in item.values():
            body = (op.get("requestBody") or {}).get("content", {})
            for media in body.values():
                ref = media.get("schema", {}).get("$ref")
                if ref:
                    names.add(ref.rsplit("/", 1)[-1])
    # include nested schemas referenced by request bodies
    todo = list(names)
    while todo:
        name = todo.pop()
        for ref in re.findall(
            r'"#/components/schemas/([^"]+)"', str(schemas[name]).replace("'", '"')
        ):
            if ref not in names:
                names.add(ref)
                todo.append(ref)
    return {n: schemas[n] for n in names}


def test_no_request_schema_has_a_rating_field() -> None:
    request_schemas = _walk_request_schemas()
    assert len(request_schemas) >= 10
    for name, schema in request_schemas.items():
        bad = FORBIDDEN_FIELDS & set(schema.get("properties", {}))
        assert not bad, f"{name} exposes {bad}"


def test_no_query_parameter_is_a_rating_field() -> None:
    for path, item in app.openapi()["paths"].items():
        for method, op in item.items():
            if method.upper() != "GET":
                continue
            for param in op.get("parameters", []):
                if path.startswith("/api/v1/admin") or param["in"] == "query":
                    assert param["name"] not in {"current_rating", "highest_rating", "elo"}


def test_write_request_schemas_forbid_unknown_fields() -> None:
    for name, schema in _walk_request_schemas().items():
        if "properties" in schema and name.endswith("Request"):
            assert schema.get("additionalProperties") is False, name


def test_rating_fields_are_rejected_on_every_write_route(api_client: Client) -> None:
    client, _ = api_client
    a, b = make_players(client, 2)
    tid = make_tournament(client, [a, b])
    m = club_match(client, a, b, a)
    for field in ("current_rating", "highest_rating", "rating", "elo", "rating_change"):
        extra = {field: 2000}
        cases = [
            ("POST", "/admin/players", {"display_name": "Zed", **extra}),
            ("PATCH", f"/admin/players/{a}", extra),
            (
                "POST",
                "/admin/matches",
                {
                    "player_a_id": a,
                    "player_b_id": b,
                    "winner_id": a,
                    "match_date": "2026-10-01T10:00:00Z",
                    **extra,
                },
            ),
            ("PATCH", f"/admin/matches/{m['id']}", extra),
            ("POST", f"/admin/matches/{m['id']}/correct", {"reason": "x", **extra}),
            ("POST", f"/admin/matches/{m['id']}/cancel", {"reason": "x", **extra}),
            ("POST", "/admin/tournaments", {"name": "T", **extra}),
            ("PATCH", f"/admin/tournaments/{tid}", extra),
            ("POST", f"/admin/tournaments/{tid}/generate-bracket", extra),
            ("POST", "/admin/achievements", {"name": "N", "description": "d", **extra}),
        ]
        for method, path, body in cases:
            r = client.request(method, API + path, json=body, headers=auth())
            assert r.status_code == 422, (field, method, path, r.status_code)
            assert r.json()["error"]["code"] == "validation_error"
    players = client.get(f"{API}/players/{a}").json()
    assert players["current_rating"] == 1516 and players["highest_rating"] == 1516


def test_no_route_exists_that_sets_ratings() -> None:
    for _method, path in _implemented():
        assert not re.search(r"rating(?!-history|s)|elo", path.replace("/rankings", "")), path


# ------------------------------ error envelope -----------------------------


def _assert_envelope(response: Any, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]


def test_404_envelopes(api_client: Client) -> None:
    client, _ = api_client
    missing = str(uuid.uuid4())
    for path in (
        f"/players/{missing}",
        f"/players/{missing}/matches",
        f"/players/{missing}/rating-history",
        f"/players/{missing}/monthly",
        f"/players/{missing}/achievements",
        f"/matches/{missing}",
        f"/tournaments/{missing}",
        f"/tournaments/{missing}/bracket",
        f"/head-to-head/{missing}/{uuid.uuid4()}",
    ):
        _assert_envelope(client.get(API + path), 404, "not_found")
    for method, path, body in (
        ("PATCH", f"/admin/players/{missing}", {"display_name": "Nobody"}),
        ("DELETE", f"/admin/players/{missing}", None),
        ("PATCH", f"/admin/matches/{missing}", {"notes": "n"}),
        ("POST", f"/admin/matches/{missing}/cancel", {"reason": "x"}),
        ("PATCH", f"/admin/tournaments/{missing}", {"name": "n"}),
        ("PATCH", f"/admin/achievements/{missing}", {"description": "n"}),
        ("DELETE", f"/admin/player-achievements/{missing}", None),
    ):
        kwargs = {} if body is None else {"json": body}
        r = client.request(method, API + path, headers=auth(), **kwargs)
        _assert_envelope(r, 404, "not_found")
    _assert_envelope(client.get(f"{API}/no-such-route"), 404, "not_found")


def test_409_envelopes(api_client: Client) -> None:
    client, _ = api_client
    a, b = make_players(client, 2, prefix="Dup")
    dup = client.post(f"{API}/admin/players", json={"display_name": "DUP1"}, headers=auth())
    _assert_envelope(dup, 409, "conflict")
    ach = {"name": "Twice", "description": "d"}
    assert client.post(f"{API}/admin/achievements", json=ach, headers=auth()).status_code == 201
    _assert_envelope(
        client.post(f"{API}/admin/achievements", json=ach, headers=auth()), 409, "conflict"
    )
    tid = make_tournament(client, [a])
    again = client.post(
        f"{API}/admin/tournaments/{tid}/participants",
        json={"participants": [{"player_id": a}]},
        headers=auth(),
    )
    _assert_envelope(again, 409, "conflict")
    one_player = client.post(
        f"{API}/admin/tournaments/{tid}/matches",
        json={
            "bracket_match_id": str(uuid.uuid4()),
            "winner_id": a,
            "match_date": "2026-10-01T10:00:00Z",
        },
        headers=auth(),
    )
    _assert_envelope(one_player, 409, "conflict")  # tournament not in progress


def test_422_validation_and_business_rule_envelopes(api_client: Client) -> None:
    client, _ = api_client
    a, b = make_players(client, 2, prefix="Val")
    empty = client.post(f"{API}/admin/players", json={"display_name": "  "}, headers=auth())
    _assert_envelope(empty, 422, "validation_error")
    assert isinstance(empty.json()["error"]["details"], list)
    assert empty.json()["error"]["details"]
    _assert_envelope(
        client.post(f"{API}/admin/players", json={}, headers=auth()), 422, "validation_error"
    )
    _assert_envelope(client.get(f"{API}/matches", params={"page": 0}), 422, "validation_error")
    _assert_envelope(
        client.get(f"{API}/matches", params={"page_size": 101}), 422, "validation_error"
    )
    _assert_envelope(client.get(f"{API}/players/not-a-uuid"), 422, "validation_error")
    base = {
        "player_a_id": a,
        "player_b_id": b,
        "winner_id": a,
        "match_date": "2026-10-01T10:00:00Z",
    }
    _assert_envelope(
        client.post(f"{API}/admin/matches", json={**base, "player_b_id": a}, headers=auth()),
        422,
        "business_rule_violation",
    )
    _assert_envelope(
        client.post(
            f"{API}/admin/matches", json={**base, "winner_id": str(uuid.uuid4())}, headers=auth()
        ),
        422,
        "business_rule_violation",
    )
    _assert_envelope(
        client.post(
            f"{API}/admin/matches", json={**base, "player_b_id": str(uuid.uuid4())}, headers=auth()
        ),
        422,
        "business_rule_violation",
    )


def test_401_403_envelopes_and_pagination_shape(api_client: Client) -> None:
    client, _ = api_client
    r = client.get(f"{API}/admin/me")
    _assert_envelope(r, 401, "unauthorized")
    assert r.headers["www-authenticate"] == "Bearer"
    make_players(client, 3, prefix="Pg")
    page = client.get(f"{API}/matches", params={"page": 2, "page_size": 1}).json()
    assert set(page) == {"items", "total", "page", "page_size"}
    assert page["page"] == 2 and page["page_size"] == 1
    default = client.get(f"{API}/matches").json()
    assert default["page"] == 1 and default["page_size"] == 20
    beyond = client.get(f"{API}/matches", params={"page": 99}).json()
    assert beyond["items"] == []
