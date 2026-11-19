"""Dependencies for admin authorization.

``require_admin`` is the only gate for ``/admin/*``. It never trusts a role
claim. Audit logs should store ``get_actor_id(principal)``: the Supabase
``admin_users.auth_user_id`` (the JWT ``sub``), or ``dev-admin`` in dev mode.
"""

import hmac
from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import failed_auth_limiter
from app.core.security import AuthNotConfiguredError, TokenError, verify_supabase_token
from app.db.session import get_db
from app.models.admin_user import AdminUser


@dataclass(frozen=True, slots=True)
class AdminPrincipal:
    """Authenticated admin, or the isolated dev actor."""

    id: str
    email: str | None
    display_name: str | None
    auth_mode: Literal["supabase", "dev"]


def get_actor_id(principal: AdminPrincipal) -> str:
    """Actor id written on audit logs. This is ``principal.id``."""
    return principal.id


class _AuthFailure(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class _NotAdmin(Exception):
    """The token is valid and the caller is not an active admin."""


def _client_ip(request: Request) -> str:
    """Socket peer reported by the server, used only as a limiter key."""
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


def _bearer_token(request: Request) -> str:
    header = request.headers.get("authorization")
    if header is None or not header.strip():
        raise _AuthFailure("Missing bearer token")
    scheme, separator, token = header.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip() or " " in token.strip():
        raise _AuthFailure("Malformed authorization header")
    return token.strip()


def _principal_from_dev_token(token: str) -> AdminPrincipal:
    expected = settings.DEV_ADMIN_TOKEN
    if not expected:
        raise _AuthFailure("Dev admin token is not configured")
    presented = token.encode("utf-8")
    if not hmac.compare_digest(presented, expected.encode("utf-8")):
        raise _AuthFailure("Invalid or expired token")
    return AdminPrincipal(id="dev-admin", email=None, display_name=None, auth_mode="dev")


def _principal_from_supabase(token: str, db: Session) -> AdminPrincipal:
    try:
        claims = verify_supabase_token(token)
    except AuthNotConfiguredError as exc:
        raise _AuthFailure(exc.message) from exc
    except TokenError as exc:
        raise _AuthFailure("Invalid or expired token") from exc

    sub = claims["sub"]
    if not isinstance(sub, str) or not sub:
        raise _AuthFailure("Invalid or expired token")
    admin = db.scalar(select(AdminUser).where(AdminUser.auth_user_id == sub))
    if admin is None or not admin.is_active:
        raise _NotAdmin()
    return AdminPrincipal(
        id=admin.auth_user_id,
        email=admin.email,
        display_name=admin.display_name,
        auth_mode="supabase",
    )


def _authenticate(request: Request, db: Session) -> AdminPrincipal:
    if settings.APP_ENV == "production" and settings.AUTH_MODE == "dev":
        raise _AuthFailure("Dev authentication is not allowed in production")
    token = _bearer_token(request)
    if settings.AUTH_MODE == "dev":
        return _principal_from_dev_token(token)
    return _principal_from_supabase(token, db)


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> AdminPrincipal:
    """Require a bearer token that belongs to an active admin.

    Failed authentications are counted per client IP (20 per 5 minutes).
    While that window is full, later admin requests from the same IP receive
    429, including a request that would otherwise succeed. Dev mode is rejected
    again here when ``APP_ENV`` is production, in addition to the startup check.
    """
    cached = getattr(request.state, "admin_principal", None)
    if isinstance(cached, AdminPrincipal):
        return cached

    client_ip = _client_ip(request)
    if failed_auth_limiter.is_limited(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many failed admin authentication attempts",
        )

    try:
        principal = _authenticate(request, db)
    except _NotAdmin:
        raise HTTPException(
            status_code=403,
            detail="Valid token but the user is not an active admin",
        ) from None
    except _AuthFailure as exc:
        failed_auth_limiter.record(client_ip)
        raise _unauthorized(exc.message) from None

    request.state.admin_principal = principal
    return principal
