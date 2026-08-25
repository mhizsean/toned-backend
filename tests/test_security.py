from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

from app.config import Settings, get_settings
from app.core.security import clear_jwks_cache, decode_supabase_jwt


def test_decode_hs256_access_token():
    get_settings.cache_clear()
    clear_jwks_cache()
    secret = "test-secret-for-pytest-hs256-0123456789ab"
    with patch(
        "app.core.security.get_settings",
        return_value=Settings(
            supabase_jwt_secret=secret,
            supabase_url="https://example.supabase.co",
        ),
    ):
        token = jwt.encode(
            {
                "sub": "user-hs",
                "email": "hs@toned.app",
                "aud": "authenticated",
            },
            secret,
            algorithm="HS256",
        )
        payload = decode_supabase_jwt(token)
        assert payload.sub == "user-hs"
        assert payload.email == "hs@toned.app"


def test_decode_es256_access_token_via_jwks():
    get_settings.cache_clear()
    clear_jwks_cache()

    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    public_numbers = public_key.public_numbers()

    def _int_to_b64url(value: int, length: int = 32) -> str:
        return (
            jwt.utils.base64url_encode(value.to_bytes(length, "big")).decode("ascii")
        )

    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": _int_to_b64url(public_numbers.x),
        "y": _int_to_b64url(public_numbers.y),
        "kid": "test-kid",
        "alg": "ES256",
        "use": "sig",
    }

    token = jwt.encode(
        {
            "sub": "user-es",
            "email": "es@toned.app",
            "aud": "authenticated",
            "iss": "https://example.supabase.co/auth/v1",
        },
        private_key,
        algorithm="ES256",
        headers={"kid": "test-kid"},
    )

    with (
        patch(
            "app.core.security.get_settings",
            return_value=Settings(
                supabase_jwt_secret="unused",
                supabase_url="https://example.supabase.co",
            ),
        ),
        patch(
            "app.core.security._fetch_jwks",
            return_value={"keys": [jwk]},
        ),
    ):
        payload = decode_supabase_jwt(token)
        assert payload.sub == "user-es"
        assert payload.email == "es@toned.app"
