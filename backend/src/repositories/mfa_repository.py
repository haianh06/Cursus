from datetime import datetime

from sqlalchemy.orm import Session

from src.db.models import MfaRecoveryCode, MfaTotpCredential, MfaTrustedDevice


class MfaRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_totp_by_user_id(self, user_id: str) -> MfaTotpCredential | None:
        return self._db.query(MfaTotpCredential).filter_by(user_id=user_id).first()

    def add_totp(self, credential: MfaTotpCredential) -> MfaTotpCredential:
        self._db.add(credential)
        self._db.commit()
        self._db.refresh(credential)
        return credential

    def add_recovery_codes(self, codes: list[MfaRecoveryCode]) -> None:
        self._db.add_all(codes)
        self._db.commit()

    def revoke_unused_recovery_codes(self, user_id: str, used_at: datetime) -> None:
        (
            self._db.query(MfaRecoveryCode)
            .filter(
                MfaRecoveryCode.user_id == user_id,
                MfaRecoveryCode.used_at.is_(None),
            )
            .update({"used_at": used_at}, synchronize_session=False)
        )

    def get_unused_recovery_code_by_hash(
        self,
        code_hash: str,
    ) -> MfaRecoveryCode | None:
        return (
            self._db.query(MfaRecoveryCode)
            .filter_by(code_hash=code_hash, used_at=None)
            .first()
        )

    def add_trusted_device(self, device: MfaTrustedDevice) -> MfaTrustedDevice:
        self._db.add(device)
        self._db.commit()
        self._db.refresh(device)
        return device

    def get_trusted_device_by_hash(
        self,
        device_token_hash: str,
    ) -> MfaTrustedDevice | None:
        return (
            self._db.query(MfaTrustedDevice)
            .filter_by(device_token_hash=device_token_hash)
            .first()
        )

    def revoke_trusted_devices(self, user_id: str, revoked_at: datetime) -> None:
        (
            self._db.query(MfaTrustedDevice)
            .filter(
                MfaTrustedDevice.user_id == user_id,
                MfaTrustedDevice.revoked_at.is_(None),
            )
            .update({"revoked_at": revoked_at}, synchronize_session=False)
        )

    def commit(self) -> None:
        self._db.commit()
