import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.config import Settings
from src.db.models import AuthSession, User
from src.repositories.session_repository import SessionRepository
from src.services.auth.device_service import DeviceService
from src.services.auth.refresh_token_service import RefreshTokenService


class SessionError(Exception):
    pass


class InvalidRefreshTokenError(SessionError):
    pass


class RefreshTokenExpiredError(SessionError):
    pass


class RefreshTokenReuseError(SessionError):
    pass


@dataclass(frozen=True)
class SessionTokenResult:
    session: AuthSession
    refresh_token: str


class SessionService:
    def __init__(
        self,
        sessions: SessionRepository,
        settings: Settings,
        refresh_tokens: RefreshTokenService | None = None,
        devices: DeviceService | None = None,
    ) -> None:
        self._sessions = sessions
        self._settings = settings
        self._refresh_tokens = refresh_tokens or RefreshTokenService()
        self._devices = devices or DeviceService()

    async def create_session(
        self,
        *,
        user: User,
        remember_me: bool,
        user_agent: str | None,
        ip_address: str | None,
    ) -> SessionTokenResult:
        return self._create_session(
            user=user,
            remember_me=remember_me,
            user_agent=user_agent,
            ip_address=ip_address,
            token_family_id=f"tf_{uuid.uuid4().hex}",
        )

    async def create_demo_session(
        self,
        *,
        user: User,
        user_agent: str | None,
        ip_address: str | None,
    ) -> SessionTokenResult:
        """Short, fixed-TTL session for /auth/demo-session — never
        remember-me, never refreshed to a long-lived window, regardless of
        settings changes elsewhere. Reuses the same cookie/refresh-token
        machinery as a normal login; only the lifetime differs."""
        now = _utc_now_naive()
        return self._create_session(
            user=user,
            remember_me=False,
            user_agent=user_agent,
            ip_address=ip_address,
            token_family_id=f"tf_{uuid.uuid4().hex}",
            absolute_expires_at=now + timedelta(minutes=self._settings.demo_session_token_minutes),
        )

    async def rotate_refresh_token(self, refresh_token: str) -> SessionTokenResult:
        token_hash = self._refresh_tokens.hash_token(refresh_token)
        session = self._sessions.get_by_refresh_token_hash(token_hash)
        if not session:
            raise InvalidRefreshTokenError("Refresh session not found")

        now = _utc_now_naive()
        if session.revoked_at:
            await self.revoke_token_family(
                session.token_family_id,
                reason="REFRESH_REUSE_DETECTED",
            )
            raise RefreshTokenReuseError("Refresh token reuse detected")

        if session.expires_at <= now:
            _revoke_session(session, now=now, reason="EXPIRED")
            self._sessions.commit()
            raise RefreshTokenExpiredError("Refresh session expired")

        absolute_expires_at = _absolute_expires_at(session, now)
        if absolute_expires_at <= now:
            await self.revoke_token_family(
                session.token_family_id,
                reason="ABSOLUTE_EXPIRED",
            )
            raise RefreshTokenExpiredError("Refresh session expired")

        _revoke_session(session, now=now, reason="ROTATED")
        rotated = self._create_session(
            user_id=session.user_id,
            remember_me=session.remember_me,
            device_label=session.device_label,
            user_agent_hash=session.user_agent_hash,
            ip_address=session.ip_address,
            token_family_id=session.token_family_id,
            absolute_expires_at=absolute_expires_at,
        )
        return rotated

    async def revoke_current_session(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return

        session = self._sessions.get_by_refresh_token_hash(
            self._refresh_tokens.hash_token(refresh_token)
        )
        if not session or session.revoked_at:
            return

        _revoke_session(session, now=_utc_now_naive(), reason="LOGOUT")
        self._sessions.commit()

    async def revoke_all_user_sessions(self, user_id: str) -> None:
        now = _utc_now_naive()
        for session in self._sessions.list_active_by_user_id(user_id, now=now):
            _revoke_session(session, now=now, reason="LOGOUT_ALL")
        self._sessions.commit()

    async def list_active_sessions(self, user_id: str) -> list[AuthSession]:
        now = _utc_now_naive()
        return self._sessions.list_active_by_user_id(user_id, now=now)

    async def revoke_session_for_user(self, session_id: str, user_id: str) -> None:
        session = self._sessions.get_by_id(session_id)
        if not session or session.user_id != user_id:
            raise SessionError("Session not found")

        if not session.revoked_at:
            _revoke_session(session, now=_utc_now_naive(), reason="REMOTE_LOGOUT")
            self._sessions.commit()

    async def revoke_token_family(self, token_family_id: str, reason: str) -> None:
        now = _utc_now_naive()
        for session in self._sessions.list_by_token_family_id(token_family_id):
            if not session.revoked_at:
                _revoke_session(session, now=now, reason=reason)
        self._sessions.commit()

    def _create_session(
        self,
        *,
        remember_me: bool,
        token_family_id: str,
        user: User | None = None,
        user_id: str | None = None,
        user_agent: str | None = None,
        device_label: str | None = None,
        user_agent_hash: str | None = None,
        ip_address: str | None = None,
        absolute_expires_at: datetime | None = None,
    ) -> SessionTokenResult:
        resolved_user_id = user.id if user else user_id
        if not resolved_user_id:
            raise SessionError("Session user is required")

        refresh_token = self._refresh_tokens.create_token()
        now = _utc_now_naive()
        resolved_absolute_expires_at = absolute_expires_at or (
            now + timedelta(days=self._absolute_session_days(remember_me))
        )
        expires_at = min(
            now + timedelta(days=self._refresh_token_days(remember_me)),
            resolved_absolute_expires_at,
        )
        session = AuthSession(
            id=f"sess_{uuid.uuid4().hex}",
            user_id=resolved_user_id,
            refresh_token_hash=self._refresh_tokens.hash_token(refresh_token),
            token_family_id=token_family_id,
            device_label=device_label or self._devices.label_from_user_agent(user_agent),
            user_agent_hash=user_agent_hash or self._devices.hash_user_agent(user_agent),
            ip_address=ip_address,
            remember_me=remember_me,
            expires_at=expires_at,
            absolute_expires_at=resolved_absolute_expires_at,
            created_at=now,
            last_used_at=now,
        )
        return SessionTokenResult(
            session=self._sessions.add(session),
            refresh_token=refresh_token,
        )

    def _refresh_token_days(self, remember_me: bool) -> int:
        if remember_me:
            return self._settings.remember_me_refresh_token_days
        return self._settings.refresh_token_days

    def _absolute_session_days(self, remember_me: bool) -> int:
        if remember_me:
            return self._settings.remember_me_session_absolute_days
        return self._settings.session_absolute_days


def _revoke_session(session: AuthSession, *, now: datetime, reason: str) -> None:
    session.revoked_at = now
    session.revoked_reason = reason


def _absolute_expires_at(session: AuthSession, now: datetime) -> datetime:
    if session.absolute_expires_at:
        return session.absolute_expires_at
    # Backfill behavior for sessions created before the bounded-lifetime column
    # existed. Treat the current refresh expiry as the absolute cap instead of
    # silently extending a legacy session family.
    return session.expires_at if session.expires_at else now


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
