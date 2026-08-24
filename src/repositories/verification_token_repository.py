from datetime import datetime

from sqlalchemy.orm import Session

from src.db.models import VerificationToken


class VerificationTokenRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, token: VerificationToken) -> VerificationToken:
        self._db.add(token)
        self._db.commit()
        self._db.refresh(token)
        return token

    def get_by_token_hash(self, token_hash: str) -> VerificationToken | None:
        return (
            self._db.query(VerificationToken)
            .filter_by(token_hash=token_hash)
            .first()
        )

    def revoke_unused_for_user_and_purpose(
        self,
        *,
        user_id: str,
        purpose: str,
        used_at: datetime,
    ) -> None:
        (
            self._db.query(VerificationToken)
            .filter(
                VerificationToken.user_id == user_id,
                VerificationToken.purpose == purpose,
                VerificationToken.used_at.is_(None),
            )
            .update({"used_at": used_at}, synchronize_session=False)
        )

    def commit(self) -> None:
        self._db.commit()
