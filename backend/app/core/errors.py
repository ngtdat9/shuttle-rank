"""Application errors and the shared JSON error envelope.

Every handled failure returns ``{"error": {"code", "message", "details"}}``.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException

_HTTP_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "unprocessable_entity",
}


def error_payload(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


class AppError(Exception):
    """Base error for expected API failures."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found", details: Any | None = None) -> None:
        super().__init__(404, "not_found", message, details)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict", details: Any | None = None) -> None:
        super().__init__(409, "conflict", message, details)


class BusinessRuleError(AppError):
    def __init__(
        self,
        message: str = "Business rule violation",
        details: Any | None = None,
    ) -> None:
        super().__init__(422, "business_rule_violation", message, details)


def _jsonable_details(details: Any) -> Any:
    """Drop objects Pydantic put on validation errors that are not JSON-safe."""
    if isinstance(details, PydanticValidationError):
        return _jsonable_details(details.errors())
    if isinstance(details, (list, tuple)):
        return [_jsonable_details(item) for item in details]
    if isinstance(details, dict):
        cleaned: dict[str, Any] = {}
        for key, value in details.items():
            if key == "ctx" and isinstance(value, dict):
                cleaned[key] = {ctx_key: str(ctx_value) for ctx_key, ctx_value in value.items()}
            elif isinstance(value, (str, int, float, bool)) or value is None:
                cleaned[key] = value
            elif isinstance(value, (list, tuple, dict)):
                cleaned[key] = _jsonable_details(value)
            else:
                cleaned[key] = str(value)
        return cleaned
    if isinstance(details, (str, int, float, bool)) or details is None:
        return details
    return str(details)


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc.code, exc.message, exc.details),
    )


async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, str):
        message = exc.detail
        details = None
    else:
        message = "Request failed"
        details = _jsonable_details(exc.detail)
    code = _HTTP_CODES.get(exc.status_code, "http_error")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(code, message, details),
    )


async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_payload(
            "validation_error",
            "Request validation failed",
            _jsonable_details(exc.errors()),
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
