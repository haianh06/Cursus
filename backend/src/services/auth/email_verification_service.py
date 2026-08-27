import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.config import Settings
from src.db.models import User, VerificationToken
from src.repositories.user_repository import UserRepository
from src.repositories.verification_token_repository import VerificationTokenRepository
from src.security.tokens import create_opaque_token, hash_opaque_token
from src.services.core.notification_service import NotificationService

EMAIL_VERIFICATION_PURPOSE = "EMAIL_VERIFICATION"
_DUMMY_TOKEN = "email-verification-dummy-token"


class EmailVerificationError(Exception):
    pass


@dataclass(frozen=True)
class VerificationIssueResult:
    user_id: str | None
    issued: bool


class EmailVerificationService:
    def __init__(
        self,
        users: UserRepository,
        verification_tokens: VerificationTokenRepository,
        settings: Settings,
        notifications: NotificationService | None = None,
    ) -> None:
        self._users = users
        self._verification_tokens = verification_tokens
        self._settings = settings
        self._notifications = notifications or NotificationService(settings)

    async def issue_verification_for_user(self, user: User) -> VerificationIssueResult:
        if user.is_email_verified:
            return VerificationIssueResult(user_id=user.id, issued=False)
        await self._create_and_send_verification_token(user)
        return VerificationIssueResult(user_id=user.id, issued=True)

    async def resend_verification(self, email: str) -> VerificationIssueResult:
        user = self._users.get_by_email(email.strip().lower())
        if not user or user.is_email_verified:
            self._run_dummy_token_lookup()
            return VerificationIssueResult(user_id=None, issued=False)
        await self._create_and_send_verification_token(user)
        return VerificationIssueResult(user_id=user.id, issued=True)

    async def verify_email(self, token: str) -> User:
        verification_token = self._verification_tokens.get_by_token_hash(
            hash_opaque_token(token)
        )
        if not verification_token:
            raise EmailVerificationError("Invalid or expired email verification token")

        now = _utc_now_naive()
        if (
            verification_token.purpose != EMAIL_VERIFICATION_PURPOSE
            or verification_token.used_at is not None
            or verification_token.expires_at <= now
        ):
            raise EmailVerificationError("Invalid or expired email verification token")

        user = self._users.get_by_id(verification_token.user_id)
        if not user:
            raise EmailVerificationError("Invalid or expired email verification token")

        verification_token.used_at = now
        self._verification_tokens.revoke_unused_for_user_and_purpose(
            user_id=user.id,
            purpose=EMAIL_VERIFICATION_PURPOSE,
            used_at=now,
        )
        self._users.mark_email_verified(user)
        self._verification_tokens.commit()
        return user

    async def _create_and_send_verification_token(self, user: User) -> None:
        now = _utc_now_naive()
        token = create_opaque_token()
        self._verification_tokens.revoke_unused_for_user_and_purpose(
            user_id=user.id,
            purpose=EMAIL_VERIFICATION_PURPOSE,
            used_at=now,
        )
        self._verification_tokens.add(
            VerificationToken(
                id=f"vrt_{uuid.uuid4().hex}",
                user_id=user.id,
                token_hash=hash_opaque_token(token),
                purpose=EMAIL_VERIFICATION_PURPOSE,
                expires_at=now
                + timedelta(minutes=self._settings.email_verification_token_minutes),
                created_at=now,
            )
        )
        await self._notifications.send_email_verification(user.email, token)

    def _run_dummy_token_lookup(self) -> None:
        self._verification_tokens.get_by_token_hash(hash_opaque_token(_DUMMY_TOKEN))


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
