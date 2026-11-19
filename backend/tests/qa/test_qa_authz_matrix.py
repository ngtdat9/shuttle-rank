"""P6-01: authorization matrix over every route, enumerated from the live FastAPI app."""

import re
import time
import uuid
from collections.abc import Generator
from types import SimpleNamespace
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, settings
from app.core.rate_limit import failed_auth_limiter
from app.core.security import reset_jwks_cache
from app.main import app
from app.models.admin_user import AdminUser

SECRET = "p6-01-supabase-jwt-secret-32bytes!"
ADMIN_SUB = "22222222-2222-4222-8222-222222222222"
OTHER_SUB = "33333333-3333-4333-8333-333333333333"
INACTIVE_SUB = "44444444-4444-4444-8444-444444444444"
_EC = ec.generate_private_key(ec.SECP256R1())
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

Client = tuple[TestClient, sessionmaker[Session]]


def _operations() -> list[tuple[str, str]]:
    """(METHOD, path) for every operation, read from the live OpenAPI document."""
    out = []
    for path, item in app.openapi()["paths"].items():
        for method in item:
            if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                out.append((method.upper(), path))
    return sorted(out)


def _admin_cases() -> list[tuple[str, str]]:
    return [(m, p) for m, p in _operations() if p.startswith("/api/v1/admin")]


def _public_get_paths() -> list[str]:
    return [p for m, p in _operations() if m == "GET" and not p.startswith("/api/v1/admin")]


def _fill(path: str) -> str:
    return re.sub(r"\{[^}]+\}", lambda _m: str(uuid.uuid4()), path)


def _request(client: TestClient, method: str, path: str, headers: dict[str, str] | None = None):
    failed_auth_limiter.reset()
    kwargs: dict[str, Any] = {}
    if method in {"POST", "PATCH", "PUT"}:
        kwargs["json"] = {}
    return client.request(method, _fill(path), headers=headers or {}, **kwargs)


def _token(
    *,
    sub: str | None = ADMIN_SUB,
    aud: str | None = "authenticated",
    expires_in: int = 600,
    key: Any = SECRET,
    algorithm: str = "HS256",
    extra: dict[str, Any] | None = None,
) -> str:
    payload: dict[str, Any] = {"exp": int(time.time()) + expires_in}
    if sub is not None:
        payload["sub"] = sub
    if aud is not None:
        payload["aud"] = aud
    payload.update(extra or {})
    encoded = jwt.encode(payload, key, algorithm=algorithm)
    return encoded.decode("ascii") if isinstance(encoded, bytes) else encoded


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _reset() -> Generator[None, None, None]:
    failed_auth_limiter.reset()
    reset_jwks_cache()
    yield
    failed_auth_limiter.reset()
    reset_jwks_cache()


@pytest.fixture
def supabase(api_client: Client, monkeypatch: pytest.MonkeyPatch) -> Client:
    client, factory = api_client
    monkeypatch.setattr(settings, "AUTH_MODE", "supabase")
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.setattr(settings, "SUPABASE_JWT_AUDIENCE", "authenticated")
    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    with factory() as db:
        db.add(AdminUser(auth_user_id=ADMIN_SUB, email="p6@example.com", is_active=True))
        db.add(AdminUser(auth_user_id=INACTIVE_SUB, email="gone@example.com", is_active=False))
        db.commit()
    return client, factory


ADMIN_CASES = _admin_cases()
IDS = [f"{m} {p}" for m, p in ADMIN_CASES]


def test_enumeration_is_not_empty_and_covers_all_write_verbs() -> None:
    assert len(ADMIN_CASES) >= 22
    assert {m for m, _p in ADMIN_CASES} >= {"GET", "POST", "PATCH", "DELETE"}


def test_no_public_route_has_a_write_method() -> None:
    for method, path in _operations():
        if not path.startswith("/api/v1/admin"):
            assert method == "GET", f"public write route {method} {path}"


# ------------------------------- dev mode ---------------------------------


@pytest.mark.parametrize(("method", "path"), ADMIN_CASES, ids=IDS)
def test_dev_mode_rejects_anonymous_malformed_and_wrong_tokens(
    api_client: Client, method: str, path: str
) -> None:
    client, _ = api_client
    bad_headers: list[dict[str, str] | None] = [
        None,
        {"Authorization": ""},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer "},
        {"Authorization": "Basic dGVzdDp0ZXN0"},
        {"Authorization": "Bearer a b"},
        {"Authorization": "test-token"},
        {"Authorization": "Bearer wrong-token"},
        {"Authorization": f"Bearer {settings.DEV_ADMIN_TOKEN}x"},
        {"Authorization": "Bearer " + _token()},
    ]
    for headers in bad_headers:
        response = _request(client, method, path, headers)
        assert response.status_code == 401, (headers, response.text)
        body = response.json()
        assert body["error"]["code"] == "unauthorized"
        assert set(body["error"]) == {"code", "message", "details"}


@pytest.mark.parametrize(("method", "path"), ADMIN_CASES, ids=IDS)
def test_dev_token_passes_the_auth_gate_on_every_admin_route(
    api_client: Client, method: str, path: str
) -> None:
    client, _ = api_client
    response = _request(
        client, method, path, {"Authorization": f"Bearer {settings.DEV_ADMIN_TOKEN}"}
    )
    assert response.status_code not in (401, 403, 429), response.text
    assert response.status_code < 500, response.text


# ----------------------------- supabase mode -------------------------------


@pytest.mark.parametrize(("method", "path"), ADMIN_CASES, ids=IDS)
def test_supabase_unauthenticated_variants_get_401(
    supabase: Client, method: str, path: str
) -> None:
    client, _ = supabase
    variants = {
        "none": None,
        "expired": _bearer(_token(expires_in=-3600)),
        "bad_signature": _bearer(_token(key="x" * 40)),
        "wrong_audience": _bearer(_token(aud="anon")),
        "missing_audience": _bearer(_token(aud=None)),
        "missing_sub": _bearer(_token(sub=None)),
        "garbage": _bearer("not.a.jwt"),
        "alg_none": _bearer(
            jwt.encode({"sub": ADMIN_SUB, "aud": "authenticated"}, None, algorithm="none")
        ),
        "dev_token": _bearer(settings.DEV_ADMIN_TOKEN),
    }
    for name, headers in variants.items():
        response = _request(client, method, path, headers)
        assert response.status_code == 401, (name, response.text)
        assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(("method", "path"), ADMIN_CASES, ids=IDS)
def test_supabase_valid_non_allowlisted_or_inactive_user_gets_403(
    supabase: Client, method: str, path: str
) -> None:
    client, _ = supabase
    for sub in (OTHER_SUB, INACTIVE_SUB):
        response = _request(client, method, path, _bearer(_token(sub=sub)))
        assert response.status_code == 403, (sub, response.text)
        assert response.json()["error"]["code"] == "forbidden"


def test_supabase_role_claims_do_not_grant_admin(supabase: Client) -> None:
    client, _ = supabase
    token = _token(
        sub=OTHER_SUB,
        extra={"role": "service_role", "app_metadata": {"role": "admin"}, "is_admin": True},
    )
    assert _request(client, "GET", "/api/v1/admin/me", _bearer(token)).status_code == 403


@pytest.mark.parametrize(("method", "path"), ADMIN_CASES, ids=IDS)
def test_supabase_allowlisted_admin_passes_the_gate(
    supabase: Client, method: str, path: str
) -> None:
    client, _ = supabase
    response = _request(client, method, path, _bearer(_token()))
    assert response.status_code not in (401, 403, 429), response.text
    assert response.status_code < 500, response.text


def test_supabase_admin_me_reports_identity(supabase: Client) -> None:
    client, _ = supabase
    body = client.get("/api/v1/admin/me", headers=_bearer(_token())).json()
    assert body["id"] == ADMIN_SUB
    assert body["auth_mode"] == "supabase"
    assert body["email"] == "p6@example.com"


def test_supabase_deactivated_admin_loses_access(supabase: Client) -> None:
    client, factory = supabase
    headers = _bearer(_token())
    assert client.get("/api/v1/admin/me", headers=headers).status_code == 200
    with factory() as db:
        row = db.query(AdminUser).filter_by(auth_user_id=ADMIN_SUB).one()
        row.is_active = False
        db.commit()
    assert client.get("/api/v1/admin/me", headers=headers).status_code == 403


def test_supabase_jwks_mode_wrong_key_expired_and_audience(
    supabase: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = supabase
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "")
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://p6.supabase.co")
    other = ec.generate_private_key(ec.SECP256R1())

    class FakeJWKS:
        def __init__(self, *_a: object, **_k: object) -> None: ...

        def get_signing_key_from_jwt(self, _t: str) -> SimpleNamespace:
            return SimpleNamespace(key=_EC.public_key())

    monkeypatch.setattr("app.core.security.PyJWKClient", FakeJWKS)
    reset_jwks_cache()
    url = "/api/v1/admin/stats"
    ok = _token(key=_EC, algorithm="ES256")
    assert _request(client, "GET", url, _bearer(ok)).status_code == 200
    for bad in (
        _token(key=other, algorithm="ES256"),
        _token(key=_EC, algorithm="ES256", expires_in=-3600),
        _token(key=_EC, algorithm="ES256", aud="wrong"),
        _token(),  # HS256 token must not be accepted when only JWKS is configured
    ):
        assert _request(client, "GET", url, _bearer(bad)).status_code == 401
    non_admin = _token(key=_EC, algorithm="ES256", sub=OTHER_SUB)
    assert _request(client, "GET", url, _bearer(non_admin)).status_code == 403


def test_supabase_mode_unconfigured_rejects_everything(
    supabase: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = supabase
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "")
    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    response = _request(client, "GET", "/api/v1/admin/me", _bearer(_token()))
    assert response.status_code == 401


def test_rate_limit_returns_429_after_repeated_failures(api_client: Client) -> None:
    client, _ = api_client
    failed_auth_limiter.reset()
    codes = [client.get("/api/v1/admin/me").status_code for _ in range(25)]
    assert codes[0] == 401
    assert 429 in codes
    body = client.get(
        "/api/v1/admin/me", headers={"Authorization": f"Bearer {settings.DEV_ADMIN_TOKEN}"}
    )
    assert body.status_code == 429
    assert body.json()["error"]["code"] == "rate_limited"


# ----------------------------- production ----------------------------------


def test_settings_refuse_dev_auth_in_production() -> None:
    with pytest.raises(ValueError, match="production"):
        Settings(APP_ENV="production", AUTH_MODE="dev", DEV_ADMIN_TOKEN="x")


def test_production_dev_token_is_rejected_even_if_settings_are_forced(
    api_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defence in depth: bypass the startup validator and the request gate still refuses."""
    client, _ = api_client
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "AUTH_MODE", "dev")
    for method, path in ADMIN_CASES:
        response = _request(
            client, method, path, {"Authorization": f"Bearer {settings.DEV_ADMIN_TOKEN}"}
        )
        assert response.status_code == 401, (method, path)


def test_production_supabase_mode_does_not_accept_dev_token(
    supabase: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = supabase
    monkeypatch.setattr(settings, "APP_ENV", "production")
    response = _request(client, "GET", "/api/v1/admin/me", _bearer(settings.DEV_ADMIN_TOKEN))
    assert response.status_code == 401
    assert _request(client, "GET", "/api/v1/admin/me", _bearer(_token())).status_code == 200


# ----------------------------- public reads --------------------------------


def test_public_get_routes_work_anonymously(api_client: Client) -> None:
    client, _ = api_client
    paths = _public_get_paths()
    assert len(paths) >= 15
    for path in paths:
        response = client.get(_fill(path))
        assert response.status_code != 401, path
        assert response.status_code != 403, path
        assert response.status_code < 500, path
        if response.status_code >= 400:
            assert set(response.json()["error"]) == {"code", "message", "details"}, path


def test_public_list_routes_return_200_when_empty(api_client: Client) -> None:
    client, _ = api_client
    for path in (
        "/api/v1/health",
        "/api/v1/dashboard",
        "/api/v1/rankings",
        "/api/v1/rankings/monthly",
        "/api/v1/players",
        "/api/v1/matches",
        "/api/v1/tournaments",
        "/api/v1/achievements",
    ):
        assert client.get(path).status_code == 200, path


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_public_paths_reject_write_methods(api_client: Client, method: str) -> None:
    client, _ = api_client
    for path in _public_get_paths():
        response = client.request(method, _fill(path), json={})
        assert response.status_code in (404, 405), (method, path, response.status_code)


def test_dev_token_on_public_route_is_harmless(api_client: Client) -> None:
    client, _ = api_client
    response = client.get("/api/v1/players", headers={"Authorization": "Bearer junk"})
    assert response.status_code == 200
