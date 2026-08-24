import jwt
import pytest

from src.config import Settings
from src.security.token_exceptions import (
    InvalidTokenError,
    MalformedTokenError,
    TokenExpiredError,
)
from src.security.tokens import create_access_token, parse_access_token_claims


@pytest.fixture
def settings() -> Settings:
    return Settings(
        jwt_secret_key="unit-test-secret-key-at-least-32-characters-long",
        jwt_algorithm="HS256",
        jwt_issuer="neural-forge-auth",
        jwt_audience="neural-forge-clients",
        jwt_access_token_minutes=15,
    )


def test_create_and_parse_access_token_roundtrip(settings):
    token = create_access_token(subject="user_1", settings=settings, session_id="sess_1")

    claims = parse_access_token_claims(token, settings)

    assert claims.subject == "user_1"
    assert claims.session_id == "sess_1"
    assert claims.issuer == settings.jwt_issuer
    assert claims.audience == settings.jwt_audience
    assert claims.expires_at > claims.issued_at
    assert claims.jti


def test_access_token_has_required_claims_only(settings):
    token = create_access_token(subject="user_1", settings=settings)
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )

    for claim in ("sub", "jti", "iat", "exp", "iss", "aud"):
        assert claim in payload

    # `role` must not be embedded: authorization always re-reads the role
    # from the database, so a cached role claim would be a stale-privilege
    # risk if a user's role changes after the token was issued.
    assert "role" not in payload


def test_decode_rejects_invalid_signature(settings):
    token = create_access_token(subject="user_1", settings=settings)
    tampered_settings = Settings(
        jwt_secret_key="a-completely-different-secret-key-32-chars-min",
        jwt_algorithm=settings.jwt_algorithm,
        jwt_issuer=settings.jwt_issuer,
        jwt_audience=settings.jwt_audience,
    )

    with pytest.raises(InvalidTokenError):
        parse_access_token_claims(token, tampered_settings)


def test_decode_rejects_expired_token(settings):
    expired_settings = Settings(
        jwt_secret_key=settings.jwt_secret_key,
        jwt_algorithm=settings.jwt_algorithm,
        jwt_issuer=settings.jwt_issuer,
        jwt_audience=settings.jwt_audience,
        jwt_access_token_minutes=1,
    )
    token = jwt.encode(
        {
            "sub": "user_1",
            "jti": "jti-1",
            "iat": 1,
            "exp": 2,
            "iss": expired_settings.jwt_issuer,
            "aud": expired_settings.jwt_audience,
        },
        expired_settings.jwt_secret_key,
        algorithm=expired_settings.jwt_algorithm,
    )

    with pytest.raises(TokenExpiredError):
        parse_access_token_claims(token, expired_settings)


def test_decode_rejects_malformed_token_string(settings):
    with pytest.raises(InvalidTokenError):
        parse_access_token_claims("not-a-jwt", settings)


def test_decode_rejects_wrong_audience(settings):
    other_audience_settings = Settings(
        jwt_secret_key=settings.jwt_secret_key,
        jwt_algorithm=settings.jwt_algorithm,
        jwt_issuer=settings.jwt_issuer,
        jwt_audience="some-other-audience",
    )
    token = create_access_token(subject="user_1", settings=other_audience_settings)

    with pytest.raises(InvalidTokenError):
        parse_access_token_claims(token, settings)


def test_decode_rejects_wrong_issuer(settings):
    other_issuer_settings = Settings(
        jwt_secret_key=settings.jwt_secret_key,
        jwt_algorithm=settings.jwt_algorithm,
        jwt_issuer="some-other-issuer",
        jwt_audience=settings.jwt_audience,
    )
    token = create_access_token(subject="user_1", settings=other_issuer_settings)

    with pytest.raises(InvalidTokenError):
        parse_access_token_claims(token, settings)


def test_decode_rejects_missing_required_claim(settings):
    token = jwt.encode(
        {
            "sub": "user_1",
            "iat": 1,
            "exp": 9999999999,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            # "jti" intentionally omitted
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises((InvalidTokenError, MalformedTokenError)):
        parse_access_token_claims(token, settings)
