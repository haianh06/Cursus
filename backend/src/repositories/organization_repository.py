from sqlalchemy.orm import Session

from src.db.models import Organization, OrganizationMembership


class OrganizationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, org_id: str) -> Organization | None:
        return self._db.query(Organization).filter_by(id=org_id).first()

    def get_by_slug(self, slug: str) -> Organization | None:
        return self._db.query(Organization).filter_by(slug=slug).first()

    def add(self, org: Organization) -> Organization:
        self._db.add(org)
        self._db.commit()
        self._db.refresh(org)
        return org

    def add_membership(self, membership: OrganizationMembership) -> OrganizationMembership:
        self._db.add(membership)
        self._db.commit()
        self._db.refresh(membership)
        return membership

    def get_membership_for_user(self, user_id: str) -> OrganizationMembership | None:
        return self._db.query(OrganizationMembership).filter_by(user_id=user_id).first()
