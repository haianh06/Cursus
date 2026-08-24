import base64
import hashlib
import hmac
import secrets
import struct
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from cryptography.fernet import Fernet

from src.config import Settings
from src.db.models import MfaRecoveryCode, MfaTotpCredential, MfaTrustedDevice, User
from src.repositories.mfa_repository import MfaRepository


class MfaError(Exception):
    pass


class MfaRequiredError(MfaError):
    pass


class MfaLockedError(MfaError):
    pass


@dataclass(frozen=True)
class TotpSetupResult:
    secret: str
    otpauth_uri: str
    qr_code_uri: str


@dataclass(frozen=True)
class MfaEnableResult:
    recovery_codes: list[str]


@dataclass(frozen=True)
class MfaLoginResult:
    trusted_device_token: str | None = None


class MfaService:
    def __init__(self, mfa: MfaRepository, settings: Settings) -> None:
        self._mfa = mfa
        self._settings = settings
        self._fernet = Fernet(_fernet_key(settings))

    async def status(self, user_id: str) -> dict[str, bool]:
        credential = self._mfa.get_totp_by_user_id(user_id)
        return {"totp_enabled": bool(credential and credential.enabled)}

    async def start_totp_setup(self, user: User) -> TotpSetupResult:
        secret = _generate_totp_secret()
        encrypted = self._fernet.encrypt(secret.encode()).decode()
        now = _utc_now_naive()
        credential = self._mfa.get_totp_by_user_id(user.id)
        if credential:
            credential.secret_encrypted = encrypted
            credential.enabled = False
            credential.last_used_counter = None
            credential.failed_attempt_count = 0
            credential.locked_until = None
            credential.disabled_at = None
            credential.created_at = now
            credential.confirmed_at = None
            self._mfa.commit()
        else:
            self._mfa.add_totp(
                MfaTotpCredential(
                    id=f"mfa_totp_{uuid.uuid4().hex}",
                    user_id=user.id,
                    secret_encrypted=encrypted,
                    enabled=False,
                    created_at=now,
                )
            )
        otpauth_uri = _otpauth_uri(
            issuer=self._settings.mfa_issuer,
            account=user.email,
            secret=secret,
        )
        return TotpSetupResult(
            secret=secret,
            otpauth_uri=otpauth_uri,
            qr_code_uri=otpauth_uri,
        )

    async def enable_totp(self, user: User, code: str) -> MfaEnableResult:
        credential = self._mfa.get_totp_by_user_id(user.id)
        if not credential or credential.enabled:
            raise MfaError("MFA setup is not pending")
        secret = self._decrypt_secret(credential)
        counter = _matching_totp_counter(
            secret,
            code,
            drift_steps=self._settings.mfa_totp_drift_steps,
        )
        if counter is None:
            raise MfaError("Invalid MFA code")

        now = _utc_now_naive()
        credential.enabled = True
        credential.confirmed_at = now
        credential.last_used_counter = counter
        credential.failed_attempt_count = 0
        credential.locked_until = None
        recovery_codes = _generate_recovery_codes(self._settings.mfa_recovery_code_count)
        self._mfa.revoke_unused_recovery_codes(user.id, now)
        self._mfa.add_recovery_codes(
            [
                MfaRecoveryCode(
                    id=f"mfa_rc_{uuid.uuid4().hex}",
                    user_id=user.id,
                    code_hash=_hash_value(code_value),
                    created_at=now,
                )
                for code_value in recovery_codes
            ]
        )
        self._mfa.commit()
        return MfaEnableResult(recovery_codes=recovery_codes)

    async def verify_login_mfa(
        self,
        *,
        user: User,
        code: str | None,
        recovery_code: str | None,
        remember_device: bool,
        user_agent: str | None,
        trusted_device_token: str | None,
    ) -> MfaLoginResult:
        credential = self._enabled_credential(user.id)
        if not credential:
            return MfaLoginResult()

        if trusted_device_token and self.is_trusted_device(user.id, trusted_device_token):
            return MfaLoginResult()

        if recovery_code:
            await self._consume_recovery_code(user.id, recovery_code, credential)
        elif code:
            self._verify_totp_code(credential, code)
        else:
            raise MfaRequiredError("MFA verification required")

        if remember_device:
            return MfaLoginResult(
                trusted_device_token=self._trust_device(user.id, user_agent)
            )
        return MfaLoginResult()

    def is_mfa_enabled(self, user_id: str) -> bool:
        return self._enabled_credential(user_id) is not None

    def is_trusted_device(self, user_id: str, token: str) -> bool:
        device = self._mfa.get_trusted_device_by_hash(_hash_value(token))
        now = _utc_now_naive()
        if (
            not device
            or device.user_id != user_id
            or device.revoked_at is not None
            or device.expires_at <= now
        ):
            return False
        device.last_used_at = now
        self._mfa.commit()
        return True

    async def regenerate_recovery_codes(self, user: User, code: str) -> list[str]:
        credential = self._require_enabled_credential(user.id)
        self._verify_totp_code(credential, code)
        now = _utc_now_naive()
        recovery_codes = _generate_recovery_codes(self._settings.mfa_recovery_code_count)
        self._mfa.revoke_unused_recovery_codes(user.id, now)
        self._mfa.add_recovery_codes(
            [
                MfaRecoveryCode(
                    id=f"mfa_rc_{uuid.uuid4().hex}",
                    user_id=user.id,
                    code_hash=_hash_value(code_value),
                    created_at=now,
                )
                for code_value in recovery_codes
            ]
        )
        self._mfa.commit()
        return recovery_codes

    async def disable_mfa(
        self,
        *,
        user: User,
        code: str | None,
        recovery_code: str | None,
    ) -> None:
        credential = self._require_enabled_credential(user.id)
        if recovery_code:
            await self._consume_recovery_code(user.id, recovery_code, credential)
        elif code:
            self._verify_totp_code(credential, code)
        else:
            raise MfaError("MFA code or recovery code is required")

        now = _utc_now_naive()
        credential.enabled = False
        credential.disabled_at = now
        self._mfa.revoke_unused_recovery_codes(user.id, now)
        self._mfa.revoke_trusted_devices(user.id, now)
        self._mfa.commit()

    def current_totp(self, user_id: str) -> str:
        credential = self._require_enabled_credential(user_id)
        return generate_totp(self._decrypt_secret(credential), int(time.time()) // 30)

    def _verify_totp_code(self, credential: MfaTotpCredential, code: str) -> None:
        self._assert_not_locked(credential)
        secret = self._decrypt_secret(credential)
        counter = _matching_totp_counter(
            secret,
            code,
            drift_steps=self._settings.mfa_totp_drift_steps,
        )
        if counter is None or (
            credential.last_used_counter is not None
            and counter <= credential.last_used_counter
        ):
            self._record_failure(credential)
            raise MfaError("Invalid MFA code")
        credential.last_used_counter = counter
        self._record_success(credential)

    async def _consume_recovery_code(
        self,
        user_id: str,
        recovery_code: str,
        credential: MfaTotpCredential,
    ) -> None:
        self._assert_not_locked(credential)
        code = self._mfa.get_unused_recovery_code_by_hash(_hash_value(recovery_code))
        if not code or code.user_id != user_id:
            self._record_failure(credential)
            raise MfaError("Invalid recovery code")
        code.used_at = _utc_now_naive()
        self._record_success(credential)

    def _trust_device(self, user_id: str, user_agent: str | None) -> str:
        token = secrets.token_urlsafe(48)
        now = _utc_now_naive()
        self._mfa.add_trusted_device(
            MfaTrustedDevice(
                id=f"mfa_td_{uuid.uuid4().hex}",
                user_id=user_id,
                device_token_hash=_hash_value(token),
                device_label=user_agent[:120] if user_agent else None,
                expires_at=now + timedelta(days=self._settings.mfa_trusted_device_days),
                created_at=now,
                last_used_at=now,
            )
        )
        return token

    def _enabled_credential(self, user_id: str) -> MfaTotpCredential | None:
        credential = self._mfa.get_totp_by_user_id(user_id)
        if not credential or not credential.enabled:
            return None
        return credential

    def _require_enabled_credential(self, user_id: str) -> MfaTotpCredential:
        credential = self._enabled_credential(user_id)
        if not credential:
            raise MfaError("MFA is not enabled")
        return credential

    def _decrypt_secret(self, credential: MfaTotpCredential) -> str:
        return self._fernet.decrypt(credential.secret_encrypted.encode()).decode()

    def _assert_not_locked(self, credential: MfaTotpCredential) -> None:
        now = _utc_now_naive()
        if credential.locked_until and credential.locked_until > now:
            raise MfaLockedError("MFA is temporarily locked")

    def _record_failure(self, credential: MfaTotpCredential) -> None:
        credential.failed_attempt_count += 1
        if credential.failed_attempt_count >= self._settings.mfa_max_attempts:
            credential.locked_until = _utc_now_naive() + timedelta(
                minutes=self._settings.mfa_lockout_minutes
            )
        self._mfa.commit()

    def _record_success(self, credential: MfaTotpCredential) -> None:
        credential.failed_attempt_count = 0
        credential.locked_until = None
        self._mfa.commit()


def generate_totp(secret: str, counter: int, digits: int = 6) -> str:
    key = base64.b32decode(_pad_base32(secret), casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code_int % (10**digits)).zfill(digits)


def _matching_totp_counter(
    secret: str,
    code: str,
    *,
    drift_steps: int,
) -> int | None:
    if not code.isdigit():
        return None
    current_counter = int(time.time()) // 30
    for offset in range(-drift_steps, drift_steps + 1):
        counter = current_counter + offset
        if hmac.compare_digest(generate_totp(secret, counter), code):
            return counter
    return None


def _generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _generate_recovery_codes(count: int) -> list[str]:
    return [secrets.token_urlsafe(10) for _ in range(count)]


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _fernet_key(settings: Settings) -> bytes:
    raw_key = settings.mfa_secret_encryption_key or settings.jwt_secret_key
    digest = hashlib.sha256(raw_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _otpauth_uri(*, issuer: str, account: str, secret: str) -> str:
    issuer_q = quote(issuer)
    account_q = quote(account)
    return (
        f"otpauth://totp/{issuer_q}:{account_q}"
        f"?secret={secret}&issuer={issuer_q}&algorithm=SHA1&digits=6&period=30"
    )


def _pad_base32(value: str) -> str:
    return value + "=" * ((8 - len(value) % 8) % 8)


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
