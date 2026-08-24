import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.config import Settings
from src.db.models import User, VerificationToken
from src.repositories.user_repository import UserRepository
from src.repositories.verification_token_repository import VerificationTokenRepository
from src.security.passwords import hash_password, validate_password_policy
from src.security.tokens import create_opaque_token, hash_opaque_token
from src.services.auth.session_service import SessionService
from src.services.core.notification_service import NotificationService

PASSWORD_RESET_PURPOSE = "PASSWORD_RESET"
_DUMMY_TOKEN = "password-reset-dummy-token"


class PasswordResetError(Exception):
    pass


@dataclass(frozen=True)
class PasswordResetRequestResult:
    user_id: str | None
    issued: bool


class PasswordResetService:
    def __init__(
        self,
        users: UserRepository,
        verification_tokens: VerificationTokenRepository,
        sessions: SessionService,
        settings: Settings,
        notifications: NotificationService | None = None,
    ) -> None:
        self._users = users
        self._verification_tokens = verification_tokens
        self._sessions = sessions
        self._settings = settings
        self._notifications = notifications or NotificationService(settings)

    async def request_password_reset(self, email: str) -> PasswordResetRequestResult:
        user = self._users.get_by_email(email.strip().lower())
        if not user or not user.is_active:
            self._run_dummy_token_lookup()
            return PasswordResetRequestResult(user_id=None, issued=False)

        token = create_opaque_token()
        now = _utc_now_naive()
        self._verification_tokens.revoke_unused_for_user_and_purpose(
            user_id=user.id,
            purpose=PASSWORD_RESET_PURPOSE,
            used_at=now,
        )
        self._verification_tokens.add(
            VerificationToken(
                id=f"vrt_{uuid.uuid4().hex}",
                user_id=user.id,
                token_hash=hash_opaque_token(token),
                purpose=PASSWORD_RESET_PURPOSE,
                expires_at=now
                + timedelta(minutes=self._settings.password_reset_token_minutes),
                created_at=now,
            )
        )
        await self._notifications.send_password_reset(user.email, token)
        return PasswordResetRequestResult(user_id=user.id, issued=True)

    async def reset_password(self, token: str, new_password: str) -> User:
        try:
            validate_password_policy(new_password)
        except ValueError as exc:
            raise PasswordResetError(str(exc)) from exc

        verification_token = self._verification_tokens.get_by_token_hash(
            hash_opaque_token(token)
        )
        if not verification_token:
            raise PasswordResetError("Invalid or expired password reset token")

        now = _utc_now_naive()
        if (
            verification_token.purpose != PASSWORD_RESET_PURPOSE
            or verification_token.used_at is not None
            or verification_token.expires_at <= now
        ):
            raise PasswordResetError("Invalid or expired password reset token")

        user = self._users.get_by_id(verification_token.user_id)
        if not user:
            raise PasswordResetError("Invalid or expired password reset token")
        if not user.is_active:
            raise PasswordResetError("Invalid or expired password reset token")

        verification_token.used_at = now
        self._verification_tokens.revoke_unused_for_user_and_purpose(
            user_id=user.id,
            purpose=PASSWORD_RESET_PURPOSE,
            used_at=now,
        )
        self._users.update_password_hash(user, hash_password(new_password))
        self._verification_tokens.commit()
        await self._sessions.revoke_all_user_sessions(user.id)
        return user

    def _run_dummy_token_lookup(self) -> None:
        self._verification_tokens.get_by_token_hash(hash_opaque_token(_DUMMY_TOKEN))


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
