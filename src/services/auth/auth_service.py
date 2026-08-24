import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from src.config import Settings
from src.db.models import AuthSession, OrganizationMembership, User
from src.repositories.organization_repository import OrganizationRepository
from src.repositories.user_repository import UserRepository
from src.security.passwords import (
    hash_password,
    run_timing_safe_dummy_check,
    validate_password_policy,
    verify_password,
)
from src.security.token_exceptions import TokenError
from src.security.tokens import create_access_token, parse_access_token_claims
from src.services.auth.org_invite_service import InviteNotFoundError, OrgInviteService
from src.services.auth.session_service import SessionService
from src.services.auth_dto import LoginInput, RegisterInput
from src.services.auth_exceptions import (
    EmailNotVerifiedError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidInviteError,
    PasswordPolicyError,
    RegistrationError,
    UnauthorizedError,
)


@dataclass(frozen=True)
class AuthResult:
    user: User
    access_token: str
    refresh_token: str
    session: AuthSession


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        sessions: SessionService,
        settings: Settings,
        invites: OrgInviteService,
        organizations: OrganizationRepository,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._settings = settings
        self._invites = invites
        self._organizations = organizations

    async def register(self, payload: RegisterInput) -> User:
        """Invite-only registration. Email, role, and organization all come
        from the invite record — never from `payload` — so a client can
        never grant itself a role or join an organization it wasn't invited
        to. This is the single account-creation path for every role
        (Student/Teacher/Admin); there is no open self-signup."""
        try:
            validate_password_policy(payload.password)
        except ValueError as exc:
            raise PasswordPolicyError(str(exc)) from exc

        try:
            resolved = self._invites.get_valid_invite_by_token(payload.invite_token)
        except InviteNotFoundError as exc:
            raise InvalidInviteError(str(exc)) from exc

        invite = resolved.invite
        submitted_email = _normalize_email(payload.email)
        if submitted_email != invite.email:
            raise InvalidInviteError("Email does not match this invitation")

        if self._users.get_by_email(invite.email):
            raise RegistrationError("Email is already registered")

        now = _utc_now_naive()
        user = User(
            id=f"user_{uuid.uuid4().hex}",
            email=invite.email,
            password_hash=hash_password(payload.password),
            full_name=(payload.full_name or invite.full_name).strip(),
            role=invite.role,
            organization_id=invite.organization_id,
            is_email_verified=True,
            is_active=True,
            created_at=now,
        )
        user = self._users.add(user)
        self._organizations.add_membership(
            OrganizationMembership(
                id=f"orgmem_{uuid.uuid4().hex}",
                user_id=user.id,
                organization_id=invite.organization_id,
                role=invite.role,
                created_at=now,
            )
        )
        self._invites.consume(invite, now)
        return user

    async def login(
        self,
        payload: LoginInput,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> AuthResult:
        user = await self.authenticate_credentials(payload)
        return await self.create_session_for_user(
            user=user,
            remember_me=payload.remember_me,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    async def authenticate_credentials(self, payload: LoginInput) -> User:
        email = _normalize_email(payload.email)
        user = self._users.get_by_email(email)

        # Always run a password verification, even when no account matches,
        # so the response time does not reveal whether `email` is registered.
        if not user:
            run_timing_safe_dummy_check(payload.password)
            raise InvalidCredentialsError("Invalid email or password")

        if not verify_password(payload.password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")

        if not user.is_active:
            raise InactiveUserError("Account is deactivated")

        if not user.is_email_verified:
            raise EmailNotVerifiedError("Email address is not verified")

        return user

    async def create_session_for_user(
        self,
        *,
        user: User,
        remember_me: bool,
        user_agent: str | None,
        ip_address: str | None,
    ) -> AuthResult:
        session = await self._sessions.create_session(
            user=user,
            remember_me=remember_me,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        access_token = create_access_token(
            subject=user.id,
            settings=self._settings,
            session_id=session.session.id,
        )
        return AuthResult(
            user=user,
            access_token=access_token,
            refresh_token=session.refresh_token,
            session=session.session,
        )

    async def get_current_user(self, token: str) -> User:
        try:
            claims = parse_access_token_claims(token, self._settings)
        except TokenError as exc:
            raise UnauthorizedError("Invalid or expired token") from exc

        user = self._users.get_by_id(claims.subject)
        if not user:
            raise UnauthorizedError("User not found")

        if not user.is_active:
            raise InactiveUserError("Account is deactivated")

        return user

    async def refresh_access_token(self, refresh_token: str) -> AuthResult:
        session = await self._sessions.rotate_refresh_token(refresh_token)
        user = self._users.get_by_id(session.session.user_id)
        if not user:
            raise UnauthorizedError("User not found")

        if not user.is_active:
            raise InactiveUserError("Account is deactivated")

        access_token = create_access_token(
            subject=user.id,
            settings=self._settings,
            session_id=session.session.id,
        )
        return AuthResult(
            user=user,
            access_token=access_token,
            refresh_token=session.refresh_token,
            session=session.session,
        )

    async def get_current_session_id(self, token: str) -> str:
        try:
            claims = parse_access_token_claims(token, self._settings)
        except TokenError as exc:
            raise UnauthorizedError("Invalid or expired token") from exc

        if not claims.session_id:
            raise UnauthorizedError("Invalid token session")

        return claims.session_id

    async def change_password(
        self,
        user: User,
        *,
        current_password: str,
        new_password: str,
        current_session_id: str | None = None,
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")

        try:
            validate_password_policy(new_password)
        except ValueError as exc:
            raise PasswordPolicyError(str(exc)) from exc

        if current_password == new_password:
            raise PasswordPolicyError("New password must be different from the current password")

        self._users.update_password_hash(user, hash_password(new_password))

        sessions = await self._sessions.list_active_sessions(user.id)
        for session in sessions:
            if current_session_id and session.id == current_session_id:
                continue
            await self._sessions.revoke_session_for_user(session.id, user.id)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
