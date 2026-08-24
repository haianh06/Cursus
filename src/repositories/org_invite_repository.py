from datetime import datetime

from sqlalchemy.orm import Session

from src.db.models import OrgInvite


class OrgInviteRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, invite: OrgInvite) -> OrgInvite:
        self._db.add(invite)
        self._db.commit()
        self._db.refresh(invite)
        return invite

    def get_by_id(self, invite_id: str) -> OrgInvite | None:
        return self._db.query(OrgInvite).filter_by(id=invite_id).first()

    def get_by_token_hash(self, token_hash: str) -> OrgInvite | None:
        return self._db.query(OrgInvite).filter_by(token_hash=token_hash).first()

    def list_for_org(self, organization_id: str) -> list[OrgInvite]:
        return (
            self._db.query(OrgInvite)
            .filter_by(organization_id=organization_id)
            .order_by(OrgInvite.created_at.desc())
            .all()
        )

    def mark_used(self, invite: OrgInvite, used_at: datetime) -> OrgInvite:
        invite.used_at = used_at
        self._db.commit()
        self._db.refresh(invite)
        return invite

    def revoke(self, invite: OrgInvite, revoked_at: datetime) -> OrgInvite:
        invite.revoked_at = revoked_at
        self._db.commit()
        self._db.refresh(invite)
        return invite
