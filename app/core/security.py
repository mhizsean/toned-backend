from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, status
from jwt import PyJWK, PyJWTError

from app.config import get_settings

_jwks_cache: dict[str, Any] | None = None
_jwks_fetched_at: float = 0.0
_JWKS_TTL_SECONDS = 3600


@dataclass
class TokenPayload:
    sub: str
    email: str | None = None


def _issuer(supabase_url: str) -> str:
    return f"{supabase_url.rstrip('/')}/auth/v1"


def _fetch_jwks(supabase_url: str) -> dict[str, Any]:
    global _jwks_cache, _jwks_fetched_at

    now = time.time()
    if _jwks_cache is not None and now - _jwks_fetched_at < _JWKS_TTL_SECONDS:
        return _jwks_cache

    url = f"{_issuer(supabase_url)}/.well-known/jwks.json"
    try:
        with httpx.Client(timeout=10.0, trust_env=False) as client:
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not fetch auth signing keys",
        ) from exc

    if not isinstance(payload, dict) or not payload.get("keys"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth signing keys unavailable",
        )

    _jwks_cache = payload
    _jwks_fetched_at = now
    return payload


def _decode_asymmetric(token: str, *, supabase_url: str, alg: str) -> dict[str, Any]:
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    jwks = _fetch_jwks(supabase_url)
    keys = jwks.get("keys") or []
    matching = next((key for key in keys if key.get("kid") == kid), None)
    if matching is None and len(keys) == 1:
        matching = keys[0]
    if matching is None:
        raise PyJWTError("No matching JWK for token")

    signing_key = PyJWK.from_dict(matching)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=[alg],
        audience="authenticated",
        issuer=_issuer(supabase_url),
    )


def _decode_hs256(token: str, *, jwt_secret: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        jwt_secret,
        algorithms=["HS256"],
        audience="authenticated",
    )


def decode_supabase_jwt(token: str) -> TokenPayload:
    """
    Verify a Supabase access token.

    Supports:
    - Legacy HS256 tokens (SUPABASE_JWT_SECRET)
    - New asymmetric ES256/RS256 tokens via JWKS
    """
    settings = get_settings()

    try:
        header = jwt.get_unverified_header(token)
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    alg = header.get("alg") or "HS256"

    try:
        if alg == "HS256":
            if not settings.supabase_jwt_secret:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Auth is not configured",
                )
            payload = _decode_hs256(token, jwt_secret=settings.supabase_jwt_secret)
        else:
            if not settings.supabase_url:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Auth is not configured",
                )
            payload = _decode_asymmetric(
                token,
                supabase_url=settings.supabase_url,
                alg=alg,
            )
    except HTTPException:
        raise
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    return TokenPayload(sub=sub, email=payload.get("email"))


def clear_jwks_cache() -> None:
    """Test helper."""
    global _jwks_cache, _jwks_fetched_at
    _jwks_cache = None
    _jwks_fetched_at = 0.0
