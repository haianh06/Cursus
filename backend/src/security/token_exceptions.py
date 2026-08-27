"""Domain-specific exceptions raised by JWT creation, validation, and parsing.

Kept separate from `src.services.auth_exceptions` because these describe
failures of the token mechanism itself (signature, expiry, shape), not
authentication business rules (credentials, account status).
"""


class TokenError(Exception):
    """Base class for all access-token failures."""


class InvalidTokenError(TokenError):
    """Signature, header, issuer, or audience does not match expectations."""


class TokenExpiredError(TokenError):
    """Token signature is valid but the `exp` claim is in the past."""


class MalformedTokenError(TokenError):
    """Token is not well-formed JWT or is missing required claims."""
