import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.config import Settings
from src.db.models import OrgInvite
from src.repositories.org_invite_repository import OrgInviteRepository
from src.repositories.organization_repository import OrganizationRepository
from src.repositories.user_repository import UserRepository
from src.security.tokens import create_opaque_token, hash_opaque_token
from src.services.core.notification_service import NotificationService


class OrgInviteError(Exception):
    pass


class InviteNotFoundError(OrgInviteError):
    pass


@dataclass(frozen=True)
class ResolvedInvite:
    invite: OrgInvite
    organization_name: str


class OrgInviteService:
    """Creates and resolves the invite tokens that gate registration —
    the only way any account (Student/Teacher/Admin) enters the system
    outside seed/provisioning scripts."""

    def __init__(
        self,
        invites: OrgInviteRepository,
        organizations: OrganizationRepository,
        users: UserRepository,
        settings: Settings,
        notifications: NotificationService | None = None,
    ) -> None:
        self._invites = invites
        self._organizations = organizations
        self._users = users
        self._settings = settings
        self._notifications = notifications or NotificationService(settings)

    async def create_invite(
        self,
        *,
        organization_id: str,
        email: str,
        full_name: str,
        role: str,
        invited_by_user_id: str,
    ) -> OrgInvite:
        email = email.strip().lower()
        if self._users.get_by_email(email):
            raise OrgInviteError("A user with this email already exists")

        org = self._organizations.get_by_id(organization_id)
        if not org:
            raise InviteNotFoundError("Organization not found")

        token = create_opaque_token()
        now = _utc_now_naive()
        invite = self._invites.add(
            OrgInvite(
                id=f"invite_{uuid.uuid4().hex}",
                organization_id=organization_id,
                email=email,
                full_name=full_name.strip(),
                role=role.strip().upper(),
                invited_by_user_id=invited_by_user_id,
                token_hash=hash_opaque_token(token),
                expires_at=now + timedelta(minutes=self._settings.org_invite_token_minutes),
                created_at=now,
            )
        )
        try:
            await self._notifications.send_org_invite(
                email,
                token,
                role=invite.role,
                full_name=invite.full_name,
                org_name=org.name,
            )
        except Exception as exc:
            self._invites.set_delivery_status(invite, status="failed", sent_at=None)
            raise OrgInviteError("Invitation delivery failed") from exc
        self._invites.set_delivery_status(invite, status="sent", sent_at=now)
        return invite

    def get_valid_invite_by_token(self, token: str) -> ResolvedInvite:
        invite = self._invites.get_by_token_hash(hash_opaque_token(token))
        if not invite:
            raise InviteNotFoundError("Invalid or expired invitation")
        self._assert_usable(invite)
        org = self._organizations.get_by_id(invite.organization_id)
        if not org:
            raise InviteNotFoundError("Invalid or expired invitation")
        return ResolvedInvite(invite=invite, organization_name=org.name)

    def consume(self, invite: OrgInvite, used_at: datetime) -> OrgInvite:
        return self._invites.mark_used(invite, used_at)

    def list_for_org(self, organization_id: str) -> list[OrgInvite]:
        return self._invites.list_for_org(organization_id)

    def revoke(self, invite_id: str, *, organization_id: str) -> OrgInvite:
        invite = self._invites.get_by_id(invite_id)
        if not invite or invite.organization_id != organization_id:
            raise InviteNotFoundError("Invitation not found")
        return self._invites.revoke(invite, _utc_now_naive())

    async def resend(self, invite_id: str, *, organization_id: str) -> OrgInvite:
        invite = self._invites.get_by_id(invite_id)
        if not invite or invite.organization_id != organization_id:
            raise InviteNotFoundError("Invitation not found")
        self._assert_usable(invite)

        org = self._organizations.get_by_id(organization_id)
        if not org:
            raise InviteNotFoundError("Invitation not found")

        token = create_opaque_token()
        now = _utc_now_naive()
        self._invites.rotate_token(
            invite,
            token_hash=hash_opaque_token(token),
            expires_at=now + timedelta(minutes=self._settings.org_invite_token_minutes),
        )
        try:
            await self._notifications.send_org_invite(
                invite.email,
                token,
                role=invite.role,
                full_name=invite.full_name,
                org_name=org.name,
            )
        except Exception as exc:
            self._invites.set_delivery_status(invite, status="failed", sent_at=None)
            raise OrgInviteError("Invitation delivery failed") from exc
        return self._invites.set_delivery_status(invite, status="sent", sent_at=now)

    def _assert_usable(self, invite: OrgInvite) -> None:
        now = _utc_now_naive()
        if invite.used_at is not None:
            raise InviteNotFoundError("Invalid or expired invitation")
        if invite.revoked_at is not None:
            raise InviteNotFoundError("Invalid or expired invitation")
        if invite.expires_at <= now:
            raise InviteNotFoundError("Invalid or expired invitation")


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
