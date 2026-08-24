"""Domain exceptions for the Authentication service.

These describe authentication business-rule failures (as opposed to token
mechanics, which live in `src.security.token_exceptions`). Routers translate
these into HTTP responses; the service layer never raises `HTTPException`
directly, keeping it independent of FastAPI and the API schema layer.
"""


class AuthDomainError(Exception):
    """Base class for all authentication domain errors."""


class InvalidCredentialsError(AuthDomainError):
    """Email/password combination does not match any account."""


class InactiveUserError(AuthDomainError):
    """Account exists and credentials are valid, but is deactivated."""


class EmailNotVerifiedError(AuthDomainError):
    """Account exists and credentials are valid, but email is unverified."""


class UnauthorizedError(AuthDomainError):
    """Bearer token is missing, invalid, expired, or refers to no user."""


class RegistrationError(AuthDomainError):
    """A new account could not be created."""


class PasswordPolicyError(RegistrationError):
    """Candidate password does not satisfy the password policy."""


class InvalidInviteError(RegistrationError):
    """Invite token is missing, invalid, expired, revoked, already used, or
    does not match the submitted email — registration is invite-only, there
    is no publicly assignable role or open self-signup path."""
