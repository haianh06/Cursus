from typing import Literal

from pydantic import BaseModel, Field

DemoRole = Literal["student", "instructor", "admin"]


class RegisterRequest(BaseModel):
    """Invite-only registration — no `role` field. Role/organization are
    resolved server-side from `invite_token`, never accepted from the client."""

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=12, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    invite_token: str = Field(..., min_length=16, max_length=512)


class InviteDetailsResponse(BaseModel):
    email: str
    full_name: str
    role: str
    organization_name: str
    expires_at: str


class DemoSessionRequest(BaseModel):
    role: DemoRole


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=512)
    new_password: str = Field(..., min_length=12, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=12, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=512)


class ResendEmailVerificationRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)


class ChangeEmailRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)
    remember_me: bool = False
    mfa_code: str | None = Field(default=None, min_length=6, max_length=8)
    recovery_code: str | None = Field(default=None, min_length=8, max_length=64)
    remember_device: bool = False


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_email_verified: bool
    organization_id: str | None = None
    organization_name: str | None = None
    is_demo: bool = False
    major: str | None = None
    student_code: str | None = None
    onboarded: bool = True
    preferences: dict = Field(default_factory=dict)


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    major: str | None = Field(default=None, max_length=255)
    student_code: str | None = Field(default=None, max_length=64)


class UpdatePreferencesRequest(BaseModel):
    theme: str | None = None
    language: str | None = None
    show_mascot: bool | None = None


class SessionResponse(BaseModel):
    id: str
    device_label: str | None
    ip_address: str | None
    remember_me: bool
    expires_at: str
    absolute_expires_at: str | None
    created_at: str
    last_used_at: str | None
    is_current: bool = False


class LoginResponse(BaseModel):
    token: str | None = None
    token_type: str = "bearer"
    user: UserResponse | None = None
    session: SessionResponse | None = None
    mfa_required: bool = False


class MfaTotpSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    qr_code_uri: str


class MfaEnableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)


class MfaEnableResponse(BaseModel):
    status: str
    recovery_codes: list[str]


class MfaVerifyRequest(BaseModel):
    code: str | None = Field(default=None, min_length=6, max_length=8)
    recovery_code: str | None = Field(default=None, min_length=8, max_length=64)


class MfaRecoveryCodesResponse(BaseModel):
    recovery_codes: list[str]


class MfaStatusResponse(BaseModel):
    totp_enabled: bool


class RegisterResponse(BaseModel):
    user: UserResponse


class RefreshResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    session: SessionResponse


class LogoutResponse(BaseModel):
    status: str


class MessageResponse(BaseModel):
    status: str
    message: str


class GoogleLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    full_name: str = Field(..., min_length=1, max_length=255)
    google_id: str = Field(..., min_length=1, max_length=255)

