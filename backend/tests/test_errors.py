"""Exception envelope for AppError and request validation."""

import asyncio
import json

from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from app.core.errors import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    app_error_handler,
    validation_exception_handler,
)


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": []})


def test_app_error_subclasses() -> None:
    missing = NotFoundError("Player missing", details={"id": "x"})
    conflict = ConflictError("Duplicate player")
    rule = BusinessRuleError("Winner is not a participant")

    missing_response = asyncio.run(app_error_handler(_request(), missing))
    conflict_response = asyncio.run(app_error_handler(_request(), conflict))
    rule_response = asyncio.run(app_error_handler(_request(), rule))

    assert missing_response.status_code == 404
    assert missing_response.body
    assert json.loads(missing_response.body) == {
        "error": {"code": "not_found", "message": "Player missing", "details": {"id": "x"}}
    }
    assert conflict_response.status_code == 409
    assert json.loads(conflict_response.body)["error"]["code"] == "conflict"
    assert rule_response.status_code == 422
    assert json.loads(rule_response.body)["error"]["code"] == "business_rule_violation"


def test_validation_error_envelope() -> None:
    exc = RequestValidationError(
        [{"type": "missing", "loc": ("body", "name"), "msg": "Field required", "input": {}}]
    )
    response = asyncio.run(validation_exception_handler(_request(), exc))
    body = json.loads(response.body)
    assert response.status_code == 422
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Request validation failed"
    assert body["error"]["details"][0]["loc"] == ["body", "name"]
