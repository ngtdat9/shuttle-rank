"""Admin authentication: Supabase JWT, dev token, and failed-attempt limits."""

import time
import uuid
from collections.abc import Generator
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import AdminPrincipal, get_actor_id
from app.cli import bootstrap_admin
from app.core.config import Settings, settings
from app.core.rate_limit import SlidingWindowRateLimiter, failed_auth_limiter
from app.core.security import reset_jwks_cache
from app.db.base import Base
from app.db.session import engine, make_engine
from app.main import app
from app.models.admin_user import AdminUser

TEST_SECRET = "test-supabase-jwt-secret-32bytes"
ADMIN_SUB = "11111111-1111-4111-8111-111111111111"
_EC_KEY = ec.generate_private_key(ec.SECP256R1())


@pytest.fixture(autouse=True)
def _reset_auth_state() -> Generator[None, None, None]:
    failed_auth_limiter.reset()
    reset_jwks_cache()
    yield
    failed_auth_limiter.reset()
    reset_jwks_cache()


@pytest.fixture
def admins() -> Generator[Session, None, None]:
    Base.metadata.create_all(engine)
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.rollback()
        db.close()
        cleanup = Session(bind=engine)
        try:
            cleanup.execute(delete(AdminUser))
            cleanup.commit()
        finally:
            cleanup.close()


@pytest.fixture
def supabase_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AUTH_MODE", "supabase")
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_SECRET)
    monkeypatch.setattr(settings, "SUPABASE_JWT_AUDIENCE", "authenticated")
    monkeypatch.setattr(settings, "SUPABASE_URL", "")


def supabase_token(
    *,
    sub: str = ADMIN_SUB,
    audience: str = "authenticated",
    expires_in: int = 600,
    secret: str = TEST_SECRET,
    algorithm: str = "HS256",
    key: object | None = None,
    extra: dict[str, object] | None = None,
    include_sub: bool = True,
) -> str:
    now = int(time.time())
    payload: dict[str, object] = {"aud": audience, "exp": now + expires_in}
    if include_sub:
        payload["sub"] = sub
    if extra:
        payload.update(extra)
    encoded = jwt.encode(payload, secret if key is None else key, algorithm=algorithm)
    if isinstance(encoded, bytes):
        return encoded.decode("ascii")
    return encoded


def add_admin(
    db: Session,
    *,
    auth_user_id: str = ADMIN_SUB,
    email: str = "admin@example.com",
    display_name: str | None = "Ada",
    is_active: bool = True,
) -> AdminUser:
    admin = AdminUser(
        auth_user_id=auth_user_id,
        email=email,
        display_name=display_name,
        is_active=is_active,
    )
    db.add(admin)
    db.commit()
    return admin


def assert_error(response, status: int, code: str, message: str) -> None:
    body = response.json()
    assert response.status_code == status
    assert body == {"error": {"code": code, "message": message, "details": None}}


def assert_unauthorized(response, message: str) -> None:
    assert_error(response, 401, "unauthorized", message)
    assert response.headers["www-authenticate"] == "Bearer"


def test_get_actor_id_uses_principal_id() -> None:
    supabase = AdminPrincipal(
        id=ADMIN_SUB, email="admin@example.com", display_name="Ada", auth_mode="supabase"
    )
    dev = AdminPrincipal(id="dev-admin", email=None, display_name=None, auth_mode="dev")
    assert get_actor_id(supabase) == ADMIN_SUB
    assert get_actor_id(dev) == "dev-admin"


def test_missing_header_is_unauthorized(client: TestClient) -> None:
    response = client.get("/api/v1/admin/me")
    assert_unauthorized(response, "Missing bearer token")


@pytest.mark.parametrize(
    "header",
    ["Bearer", "Bearer ", "Basic abc", "Token", "Bearer one two"],
)
def test_malformed_header_is_unauthorized(client: TestClient, header: str) -> None:
    response = client.get("/api/v1/admin/me", headers={"Authorization": header})
    assert_unauthorized(response, "Malformed authorization header")


def test_garbage_token_is_unauthorized(client: TestClient, supabase_mode: None) -> None:
    response = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer not-a-token"})
    assert_unauthorized(response, "Invalid or expired token")


def test_expired_token_is_unauthorized(client: TestClient, supabase_mode: None) -> None:
    token = supabase_token(expires_in=-120)
    response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
    assert_unauthorized(response, "Invalid or expired token")


def test_token_within_leeway_is_accepted(
    client: TestClient, admins: Session, supabase_mode: None
) -> None:
    add_admin(admins)
    token = supabase_token(expires_in=-15)
    response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["id"] == ADMIN_SUB


def test_wrong_audience_is_unauthorized(client: TestClient, supabase_mode: None) -> None:
    token = supabase_token(audience="public")
    response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
    assert_unauthorized(response, "Invalid or expired token")


def test_wrong_signature_is_unauthorized(client: TestClient, supabase_mode: None) -> None:
    token = supabase_token(secret="other-supabase-jwt-secret-32bytes")
    response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
    assert_unauthorized(response, "Invalid or expired token")


def test_token_without_sub_is_unauthorized(client: TestClient, supabase_mode: None) -> None:
    token = supabase_token(include_sub=False)
    response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
    assert_unauthorized(response, "Invalid or expired token")


def test_valid_token_without_admin_row_is_forbidden(
    client: TestClient, admins: Session, supabase_mode: None
) -> None:
    token = supabase_token()
    response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
    assert_error(response, 403, "forbidden", "Valid token but the user is not an active admin")
    assert "www-authenticate" not in response.headers


def test_inactive_admin_is_forbidden(
    client: TestClient, admins: Session, supabase_mode: None
) -> None:
    add_admin(admins, is_active=False)
    token = supabase_token()
    response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
    assert_error(response, 403, "forbidden", "Valid token but the user is not an active admin")


def test_role_claim_without_admin_row_is_forbidden(
    client: TestClient, admins: Session, supabase_mode: None
) -> None:
    token = supabase_token(extra={"role": "admin", "email": "evil@example.com"})
    response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
    assert_error(response, 403, "forbidden", "Valid token but the user is not an active admin")


def test_valid_admin_me(client: TestClient, admins: Session, supabase_mode: None) -> None:
    add_admin(admins)
    token = supabase_token(extra={"role": "admin", "email": "evil@example.com"})
    response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {
        "id": ADMIN_SUB,
        "email": "admin@example.com",
        "display_name": "Ada",
        "auth_mode": "supabase",
    }


def test_jwt_secret_is_preferred_over_jwks(
    client: TestClient,
    admins: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AUTH_MODE", "supabase")
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_SECRET)
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_JWT_AUDIENCE", "authenticated")

    def fail_client(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("JWKS client should not be built when SUPABASE_JWT_SECRET is set")

    monkeypatch.setattr("app.core.security.PyJWKClient", fail_client)
    reset_jwks_cache()
    add_admin(admins)
    token = supabase_token()
    response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["auth_mode"] == "supabase"


def test_jwks_es256_accepts_an_active_admin(
    client: TestClient,
    admins: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AUTH_MODE", "supabase")
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "")
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://example.supabase.co/")
    monkeypatch.setattr(settings, "SUPABASE_JWT_AUDIENCE", "authenticated")
    created: list[str] = []

    class FakePyJWKClient:
        def __init__(self, uri: str, *_args: object, **_kwargs: object) -> None:
            created.append(uri)

        def get_signing_key_from_jwt(self, _token: str) -> SimpleNamespace:
            return SimpleNamespace(key=_EC_KEY.public_key())

    monkeypatch.setattr("app.core.security.PyJWKClient", FakePyJWKClient)
    reset_jwks_cache()
    add_admin(admins, display_name=None)
    token = supabase_token(key=_EC_KEY, algorithm="ES256")
    headers = {"Authorization": f"Bearer {token}"}
    first = client.get("/api/v1/admin/me", headers=headers)
    second = client.get("/api/v1/admin/me", headers=headers)
    assert first.status_code == 200
    assert first.json() == {
        "id": ADMIN_SUB,
        "email": "admin@example.com",
        "display_name": None,
        "auth_mode": "supabase",
    }
    assert second.status_code == 200
    assert created == ["https://example.supabase.co/auth/v1/.well-known/jwks.json"]


def test_jwks_rejects_hs256_token(
    client: TestClient,
    admins: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AUTH_MODE", "supabase")
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "")
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://example.supabase.co")

    class FakePyJWKClient:
        def __init__(self, _uri: str, *_args: object, **_kwargs: object) -> None:
            return None

        def get_signing_key_from_jwt(self, _token: str) -> SimpleNamespace:
            return SimpleNamespace(key=_EC_KEY.public_key())

    monkeypatch.setattr("app.core.security.PyJWKClient", FakePyJWKClient)
    reset_jwks_cache()
    add_admin(admins)
    token = supabase_token()
    response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
    assert_unauthorized(response, "Invalid or expired token")


def test_supabase_mode_without_config_is_unauthorized(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "AUTH_MODE", "supabase")
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "")
    monkeypatch.setattr(settings, "SUPABASE_URL", "  ")
    response = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer anything"})
    assert_unauthorized(response, "Supabase auth is not configured")


def test_dev_mode_accepts_the_configured_token(client: TestClient) -> None:
    response = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert response.json() == {
        "id": "dev-admin",
        "email": None,
        "display_name": None,
        "auth_mode": "dev",
    }


def test_dev_mode_accepts_a_lowercase_scheme(client: TestClient) -> None:
    response = client.get("/api/v1/admin/me", headers={"Authorization": "bearer test-token"})
    assert response.status_code == 200
    assert response.json()["auth_mode"] == "dev"


def test_dev_mode_wrong_token_is_unauthorized(client: TestClient) -> None:
    response = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer wrong-token"})
    assert_unauthorized(response, "Invalid or expired token")


def test_dev_mode_empty_token_rejects_every_request(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "DEV_ADMIN_TOKEN", "")
    response = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer test-token"})
    assert_unauthorized(response, "Dev admin token is not configured")


def test_dev_mode_is_refused_in_production_by_the_dependency(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "AUTH_MODE", "dev")
    response = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer test-token"})
    assert_unauthorized(response, "Dev authentication is not allowed in production")


def test_dev_mode_is_refused_at_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_MODE", "dev")
    with pytest.raises(ValidationError, match="AUTH_MODE=dev is not allowed"):
        Settings(_env_file=None)


def test_rate_limit_blocks_the_21st_failed_attempt(client: TestClient) -> None:
    for attempt in range(20):
        response = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer wrong"})
        assert response.status_code == 401, attempt
        assert response.headers["www-authenticate"] == "Bearer"
    blocked = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer wrong"})
    assert_error(blocked, 429, "rate_limited", "Too many failed admin authentication attempts")
    assert "www-authenticate" not in blocked.headers

    still_blocked = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer test-token"})
    assert still_blocked.status_code == 429

    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    failed_auth_limiter.reset()
    recovered = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer test-token"})
    assert recovered.status_code == 200
    assert recovered.json()["auth_mode"] == "dev"


def test_forbidden_responses_do_not_count_toward_the_limit(
    client: TestClient, admins: Session, supabase_mode: None
) -> None:
    token = supabase_token()
    for _ in range(21):
        response = client.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403


def test_health_stays_anonymous(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_openapi_lists_admin_me(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/api/v1/admin/me"]


def test_sliding_window_clears_and_resets() -> None:
    limiter = SlidingWindowRateLimiter(max_events=20, window_seconds=300)
    for _ in range(20):
        limiter.record("203.0.113.4", now=1_000.0)
    assert limiter.is_limited("203.0.113.4", now=1_000.0)
    assert limiter.is_limited("203.0.113.4", now=1_299.0)
    assert not limiter.is_limited("203.0.113.4", now=1_300.0)
    assert not limiter.is_limited("203.0.113.5", now=1_000.0)
    limiter.record("203.0.113.4", now=1_300.0)
    assert not limiter.is_limited("203.0.113.4", now=1_300.0)
    limiter.reset()
    assert not limiter.is_limited("203.0.113.4", now=1_300.0)


def test_bootstrap_upserts_on_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    Base.metadata.create_all(engine)
    user_id = "44444444-4444-4444-8444-444444444444"
    db = Session(bind=engine)
    db.add(
        AdminUser(
            auth_user_id=user_id,
            email="old@example.com",
            display_name="Keep",
            is_active=False,
        )
    )
    db.commit()
    db.close()
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_USER_ID", user_id.upper())
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_EMAIL", "new@example.com")
    app.dependency_overrides.clear()
    try:
        with TestClient(app):
            pass
        with Session(bind=engine) as check:
            admin = check.scalar(select(AdminUser).where(AdminUser.auth_user_id == user_id))
            assert admin is not None
            assert admin.email == "new@example.com"
            assert admin.is_active is True
            assert admin.display_name == "Keep"
    finally:
        app.dependency_overrides.clear()
        with Session(bind=engine) as cleanup:
            cleanup.execute(delete(AdminUser))
            cleanup.commit()


def test_bootstrap_creates_a_missing_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    Base.metadata.create_all(engine)
    user_id = "55555555-5555-4555-8555-555555555555"
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_USER_ID", user_id)
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_EMAIL", "boot@example.com")
    bootstrap_admin()
    try:
        with Session(bind=engine) as check:
            admin = check.scalar(select(AdminUser).where(AdminUser.auth_user_id == user_id))
            assert admin is not None
            assert admin.email == "boot@example.com"
            assert admin.display_name is None
            assert admin.is_active is True
    finally:
        with Session(bind=engine) as cleanup:
            cleanup.execute(delete(AdminUser))
            cleanup.commit()


def test_bootstrap_missing_table_logs_a_warning(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    empty = make_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    factory = sessionmaker(bind=empty, autoflush=False, autocommit=False)
    monkeypatch.setattr("app.cli.SessionLocal", factory)
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_USER_ID", str(uuid.uuid4()))
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_EMAIL", "boot@example.com")
    try:
        with caplog.at_level("WARNING", logger="app.cli"):
            bootstrap_admin()
    finally:
        empty.dispose()
    assert "admin_users is not available yet" in caplog.text


def test_bootstrap_blank_settings_do_not_open_a_session(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_session() -> None:
        raise AssertionError("bootstrap should not touch the database")

    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_USER_ID", "")
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_EMAIL", "")
    monkeypatch.setattr("app.cli.SessionLocal", fail_session)
    bootstrap_admin()
