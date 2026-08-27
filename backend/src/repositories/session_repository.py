from datetime import datetime

from sqlalchemy.orm import Session

from src.db.models import AuthSession


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, session: AuthSession) -> AuthSession:
        self._db.add(session)
        self._db.commit()
        self._db.refresh(session)
        return session

    def get_by_refresh_token_hash(self, token_hash: str) -> AuthSession | None:
        return (
            self._db.query(AuthSession)
            .filter_by(refresh_token_hash=token_hash)
            .first()
        )

    def list_by_token_family_id(self, token_family_id: str) -> list[AuthSession]:
        return (
            self._db.query(AuthSession)
            .filter_by(token_family_id=token_family_id)
            .order_by(AuthSession.created_at.desc())
            .all()
        )

    def list_active_by_user_id(
        self,
        user_id: str,
        *,
        now: datetime | None = None,
    ) -> list[AuthSession]:
        query = self._db.query(AuthSession).filter_by(user_id=user_id, revoked_at=None)
        if now is not None:
            query = query.filter(AuthSession.expires_at > now)
        return (
            query.order_by(AuthSession.created_at.desc()).all()
        )

    def get_by_id(self, session_id: str) -> AuthSession | None:
        return self._db.query(AuthSession).filter_by(id=session_id).first()

    def commit(self) -> None:
        self._db.commit()
