"""Health endpoint."""

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


def test_health_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_health_reports_database_error(client: TestClient) -> None:
    def broken_db():
        class BrokenSession:
            def execute(self, *_args: object, **_kwargs: object) -> None:
                raise RuntimeError("database unavailable")

            def rollback(self) -> None:
                return None

            def close(self) -> None:
                return None

        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "error"}


def test_openapi_lists_health(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "Badminton Club Ranking API"
    assert "/api/v1/health" in schema["paths"]


def test_unknown_route_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/missing")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Not Found", "details": None}
    }
