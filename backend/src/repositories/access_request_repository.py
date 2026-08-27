from sqlalchemy.orm import Session

from src.db.models import AccessRequest


class AccessRequestRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, request: AccessRequest) -> AccessRequest:
        self._db.add(request)
        self._db.commit()
        self._db.refresh(request)
        return request

    def list_all(self) -> list[AccessRequest]:
        return self._db.query(AccessRequest).order_by(AccessRequest.created_at.desc()).all()
