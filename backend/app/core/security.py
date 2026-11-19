"""Supabase access-token verification.

HS256 with ``SUPABASE_JWT_SECRET`` when that secret is set. Otherwise, when
``SUPABASE_URL`` is set, signatures are checked with the project JWKS
(ES256 or RS256). One ``PyJWKClient`` is reused per URL; that client caches
the key set. Token values are never logged.
"""

import threading
from typing import Any

import jwt
from jwt import PyJWKClient

from app.core.config import settings

_CLOCK_LEEWAY_SECONDS = 30
_jwks_clients: dict[str, PyJWKClient] = {}
_jwks_lock = threading.Lock()


class TokenError(Exception):
    """A bearer token was rejected. ``message`` is safe to show to clients."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class AuthNotConfiguredError(TokenError):
    """Supabase mode has neither a JWT secret nor a project URL."""

    def __init__(self) -> None:
        super().__init__("Supabase auth is not configured")


def reset_jwks_cache() -> None:
    """Drop cached JWKS clients. Tests call this after patching ``PyJWKClient``."""
    with _jwks_lock:
        _jwks_clients.clear()


def _jwks_client(supabase_url: str) -> PyJWKClient:
    jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    with _jwks_lock:
        client = _jwks_clients.get(jwks_url)
        if client is None:
            client = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=300)
            _jwks_clients[jwks_url] = client
        return client


def verify_supabase_token(token: str) -> dict[str, Any]:
    """Return verified Supabase JWT claims.

    Raises ``AuthNotConfiguredError`` when neither signing method is configured,
    and ``TokenError`` when the token is missing a claim, expired, or signed
    with the wrong key.
    """
    secret = settings.SUPABASE_JWT_SECRET.strip()
    supabase_url = settings.SUPABASE_URL.strip()
    if secret:
        key: Any = secret
        algorithms = ["HS256"]
    elif supabase_url:
        try:
            key = _jwks_client(supabase_url).get_signing_key_from_jwt(token).key
        except Exception as exc:
            raise TokenError("Invalid or expired token") from exc
        algorithms = ["ES256", "RS256"]
    else:
        raise AuthNotConfiguredError()

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience=settings.SUPABASE_JWT_AUDIENCE,
            leeway=_CLOCK_LEEWAY_SECONDS,
            options={"require": ["exp", "sub", "aud"]},
        )
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid or expired token") from exc

    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise TokenError("Invalid or expired token")
    return claims
