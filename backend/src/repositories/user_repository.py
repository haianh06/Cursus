from sqlalchemy.orm import Session

from src.db.models import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_email(self, email: str) -> User | None:
        return self._db.query(User).filter_by(email=email).first()

    def get_by_id(self, user_id: str) -> User | None:
        return self._db.query(User).filter_by(id=user_id).first()

    def add(self, user: User) -> User:
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def update_password_hash(self, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        self._db.commit()
        self._db.refresh(user)
        return user

    def mark_email_verified(self, user: User) -> User:
        user.is_email_verified = True
        self._db.commit()
        self._db.refresh(user)
        return user

    def update_profile_fields(
        self,
        user: User,
        *,
        full_name: str,
        major: str | None,
        student_code: str | None,
    ) -> User:
        user.full_name = full_name
        user.major = major
        user.student_code = student_code
        self._db.commit()
        self._db.refresh(user)
        return user

    def update_preferences(self, user: User, patch: dict) -> User:
        merged = dict(user.preferences or {})
        merged.update({key: value for key, value in patch.items() if value is not None})
        user.preferences = merged
        self._db.commit()
        self._db.refresh(user)
        return user
