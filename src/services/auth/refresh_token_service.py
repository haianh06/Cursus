import hashlib
import secrets


class RefreshTokenService:
    """Creates and hashes opaque refresh tokens.

    Refresh tokens are intentionally not JWTs. Only the raw token is returned
    to the client once; the database stores a SHA-256 digest for lookup and
    replay detection.
    """

    def create_token(self) -> str:
        return secrets.token_urlsafe(64)

    def hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
