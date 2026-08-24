"""Password hashing, policy, and verification.

No legacy/demo password bypass exists here. Every credential — including
seed/demo accounts — must be a real Argon2 hash produced by `hash_password`.
"""

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_password_hasher = PasswordHasher()

# A throwaway Argon2 hash of random data, generated once per process. It
# never corresponds to a real account and can never succeed a verification.
# It exists solely so `run_timing_safe_dummy_check` can burn roughly the same
# CPU time as a real verification, which keeps the login endpoint's response
# time independent of whether the supplied email exists (see
# AuthService.login).
_TIMING_SAFE_DUMMY_HASH = _password_hasher.hash(secrets.token_hex(32))


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def validate_password_policy(password: str) -> None:
    has_upper = any(char.isupper() for char in password)
    has_lower = any(char.islower() for char in password)
    has_digit = any(char.isdigit() for char in password)

    if not (has_upper and has_lower and has_digit):
        raise ValueError(
            "Password must include uppercase, lowercase, and numeric characters"
        )


def verify_password(password: str, password_hash: str) -> bool:
    # argon2-cffi verifies the digest with a constant-time comparison
    # internally, so no additional timing hardening is needed here.
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, ValueError):
        return False


def run_timing_safe_dummy_check(password: str) -> None:
    """Perform a throwaway Argon2 verification and discard the result.

    Call this when no user account was found, so that "no such account" and
    "wrong password for a real account" take a similar amount of time.
    """
    try:
        _password_hasher.verify(_TIMING_SAFE_DUMMY_HASH, password)
    except (VerifyMismatchError, ValueError):
        pass
