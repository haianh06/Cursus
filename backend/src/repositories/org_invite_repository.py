from datetime import datetime

from sqlalchemy.orm import Session

from src.db.models import CourseSection, OrgInvite


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

    def assign_section_instructor(self, section_id: str, instructor_id: str) -> bool:
        """Gán giảng viên cho lớp mà lời mời mang theo — chỉ khi lớp còn trống.

        Chạm `CourseSection` từ repository của lời mời vì chính lời mời là thứ
        mang quyết định gán này; tách ra một repository riêng chỉ để đặt một
        câu UPDATE thì đắt hơn là đáng.

        Trả về True nếu thật sự gán. Điều kiện `instructor_id IS NULL` nằm
        trong chính câu UPDATE: giữa lúc gửi lời mời và lúc người kia đăng ký,
        admin vẫn có thể gán lớp cho người khác ở màn Lớp học — bản gán sau
        cùng đó phải thắng, lời mời cũ không được cướp lại lớp.
        """
        updated = (
            self._db.query(CourseSection)
            .filter(
                CourseSection.id == section_id,
                CourseSection.instructor_id.is_(None),
            )
            .update({"instructor_id": instructor_id}, synchronize_session=False)
        )
        self._db.commit()
        return bool(updated)

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

    def rotate_token(
        self,
        invite: OrgInvite,
        *,
        token_hash: str,
        expires_at: datetime,
    ) -> OrgInvite:
        invite.token_hash = token_hash
        invite.expires_at = expires_at
        invite.resend_count = (invite.resend_count or 0) + 1
        invite.delivery_status = "pending"
        invite.last_sent_at = None
        self._db.commit()
        self._db.refresh(invite)
        return invite

    def set_delivery_status(
        self,
        invite: OrgInvite,
        *,
        status: str,
        sent_at: datetime | None,
    ) -> OrgInvite:
        invite.delivery_status = status
        invite.last_sent_at = sent_at
        self._db.commit()
        self._db.refresh(invite)
        return invite
