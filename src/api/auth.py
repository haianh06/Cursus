import secrets

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.db.connection import get_db
from src.db.models import AuthSession, User
from src.repositories.audit_repository import AuditRepository
from src.repositories.mfa_repository import MfaRepository
from src.repositories.org_invite_repository import OrgInviteRepository
from src.repositories.organization_repository import OrganizationRepository
from src.repositories.session_repository import SessionRepository
from src.repositories.user_repository import UserRepository
from src.repositories.verification_token_repository import VerificationTokenRepository
from src.schemas.auth_schemas import (
    ChangeEmailRequest,
    ChangePasswordRequest,
    DemoSessionRequest,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    InviteDetailsResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    MessageResponse,
    MfaEnableRequest,
    MfaEnableResponse,
    MfaRecoveryCodesResponse,
    MfaStatusResponse,
    MfaTotpSetupResponse,
    MfaVerifyRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    ResendEmailVerificationRequest,
    ResetPasswordRequest,
    SessionResponse,
    UpdatePreferencesRequest,
    UpdateProfileRequest,
    UserResponse,
    VerifyEmailRequest,
)
from src.security.tokens import create_access_token
from src.services.auth.auth_service import AuthService
from src.services.auth.email_verification_service import (
    EmailVerificationError,
    EmailVerificationService,
)
from src.services.auth.mfa_service import MfaError, MfaLockedError, MfaRequiredError, MfaService
from src.services.auth.org_invite_service import InviteNotFoundError, OrgInviteService
from src.services.auth.password_reset_service import PasswordResetError, PasswordResetService
from src.services.auth.session_service import SessionError, SessionService
from src.services.auth_dto import LoginInput, RegisterInput
from src.services.auth_exceptions import (
    EmailNotVerifiedError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidInviteError,
    PasswordPolicyError,
    RegistrationError,
    UnauthorizedError,
)
from src.services.core.audit_service import AuditService
from src.services.core.email_provider import build_email_service
from src.services.core.notification_service import NotificationService
from src.services.mock.student_mock_data_service import StudentMockDataService

DEMO_ORG_SLUG = "cursus-demo"
DEMO_ROLE_EMAILS = {
    "student": "demo.student@cursusdemo.local",
    "instructor": "demo.instructor@cursusdemo.local",
    "admin": "demo.admin@cursusdemo.local",
}

router = APIRouter(prefix="/auth", tags=["auth"])


def get_session_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SessionService:
    return SessionService(SessionRepository(db), settings)


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    return AuditService(AuditRepository(db))


def get_mfa_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MfaService:
    return MfaService(MfaRepository(db), settings)


def get_notification_service(
    settings: Settings = Depends(get_settings),
) -> NotificationService:
    return NotificationService(settings, build_email_service(settings))


def get_org_invite_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    notification_service: NotificationService = Depends(get_notification_service),
) -> OrgInviteService:
    return OrgInviteService(
        OrgInviteRepository(db),
        OrganizationRepository(db),
        UserRepository(db),
        settings,
        notification_service,
    )


def get_auth_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    invite_service: OrgInviteService = Depends(get_org_invite_service),
) -> AuthService:
    session_service = SessionService(SessionRepository(db), settings)
    return AuthService(
        UserRepository(db),
        session_service,
        settings,
        invite_service,
        OrganizationRepository(db),
    )


def get_password_reset_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    notification_service: NotificationService = Depends(get_notification_service),
) -> PasswordResetService:
    session_service = SessionService(SessionRepository(db), settings)
    return PasswordResetService(
        UserRepository(db),
        VerificationTokenRepository(db),
        session_service,
        settings,
        notification_service,
    )


def get_email_verification_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    notification_service: NotificationService = Depends(get_notification_service),
) -> EmailVerificationService:
    return EmailVerificationService(
        UserRepository(db),
        VerificationTokenRepository(db),
        settings,
        notification_service,
    )


async def get_current_user_from_token(
    request: Request,
    authorization: str | None = Header(None),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> User:
    token = _extract_access_token(authorization, request, settings)
    try:
        return await auth_service.get_current_user(token)
    except (UnauthorizedError, InactiveUserError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authorization token",
        ) from exc


async def get_current_session_id_from_token(
    request: Request,
    authorization: str | None = Header(None),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> str:
    token = _extract_access_token(authorization, request, settings)
    try:
        return await auth_service.get_current_session_id(token)
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authorization token",
        ) from exc


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    audit_service: AuditService = Depends(get_audit_service),
    db: Session = Depends(get_db),
) -> RegisterResponse:
    try:
        user = await auth_service.register(
            RegisterInput(
                email=payload.email,
                password=payload.password,
                full_name=payload.full_name,
                invite_token=payload.invite_token,
            )
        )
    except PasswordPolicyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except InvalidInviteError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RegistrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    role_value = user.role if isinstance(user.role, str) else user.role.value
    if role_value == "STUDENT":
        StudentMockDataService(db).ensure_for_student(user.id)

    # Invited users are created pre-verified (the invite itself, sent to a
    # specific email by a trusted admin, already establishes ownership) —
    # there is no unverified state to issue a verification token for here.
    await audit_service.log_event(
        event_type="REGISTER_SUCCESS",
        decision="ALLOW",
        actor_user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return RegisterResponse(user=_serialize_user(user, db))


@router.get("/invites/{token}", response_model=InviteDetailsResponse)
async def get_invite_details(
    token: str,
    invite_service: OrgInviteService = Depends(get_org_invite_service),
) -> InviteDetailsResponse:
    """Public lookup used by the accept-invite screen to show who/what
    role/which organization the link is for, before the person sets a
    password. Never reveals anything for an expired/used/unknown token."""
    try:
        resolved = invite_service.get_valid_invite_by_token(token)
    except InviteNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invitation",
        ) from exc

    invite = resolved.invite
    return InviteDetailsResponse(
        email=invite.email,
        full_name=invite.full_name,
        role=invite.role,
        organization_name=resolved.organization_name,
        expires_at=invite.expires_at.isoformat(),
    )


@router.post("/demo-session", response_model=LoginResponse)
async def create_demo_session(
    payload: DemoSessionRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    session_service: SessionService = Depends(get_session_service),
    audit_service: AuditService = Depends(get_audit_service),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    """No credentials required — logs the visitor into one of the 3
    pre-seeded demo users inside the isolated 'Cursus Demo University'
    sandbox organization, with a short fixed-TTL session. Never creates,
    modifies, or reads anything belonging to a production organization."""
    demo_email = DEMO_ROLE_EMAILS[payload.role]
    user = UserRepository(db).get_by_email(demo_email)
    if not user or not user.organization or user.organization.slug != DEMO_ORG_SLUG:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Demo environment is not provisioned. Run provision_organization.py.",
        )

    session_result = await session_service.create_demo_session(
        user=user,
        user_agent=request.headers.get("user-agent"),
        ip_address=_request_ip(request),
    )
    access_token = create_access_token(
        subject=user.id,
        settings=settings,
        session_id=session_result.session.id,
    )
    await audit_service.log_event(
        event_type="DEMO_SESSION_STARTED",
        decision="ALLOW",
        actor_user_id=user.id,
        resource_type="session",
        resource_id=session_result.session.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={"role": payload.role},
    )
    csrf_token = _set_auth_cookies(
        response,
        access_token=access_token,
        refresh_token=session_result.refresh_token,
        settings=settings,
        remember_me=False,
    )
    return LoginResponse(
        token=access_token,
        user=_serialize_user(user, db),
        session=_serialize_session(session_result.session),
        csrf_token=csrf_token,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    mfa_service: MfaService = Depends(get_mfa_service),
    audit_service: AuditService = Depends(get_audit_service),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    login_input = LoginInput(
        email=payload.email,
        password=payload.password,
        remember_me=payload.remember_me,
    )
    try:
        user = await auth_service.authenticate_credentials(login_input)
    except (InvalidCredentialsError, InactiveUserError, EmailNotVerifiedError) as exc:
        await audit_service.log_event(
            event_type="LOGIN_FAILED",
            decision="DENY",
            ip_address=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
            metadata={"email_domain": payload.email.rsplit("@", 1)[-1].lower()},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc

    try:
        mfa_result = await mfa_service.verify_login_mfa(
            user=user,
            code=payload.mfa_code,
            recovery_code=payload.recovery_code,
            remember_device=payload.remember_device,
            user_agent=request.headers.get("user-agent"),
            trusted_device_token=_extract_mfa_trusted_device_token(request, settings),
        )
    except MfaRequiredError:
        await audit_service.log_event(
            event_type="MFA_CHALLENGE_REQUIRED",
            decision="DENY",
            actor_user_id=user.id,
            resource_type="user",
            resource_id=user.id,
            ip_address=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        return LoginResponse(mfa_required=True)
    except (MfaLockedError, MfaError) as exc:
        await audit_service.log_event(
            event_type="MFA_LOGIN_FAILED",
            decision="DENY",
            actor_user_id=user.id,
            resource_type="user",
            resource_id=user.id,
            ip_address=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA verification",
        ) from exc

    result = await auth_service.create_session_for_user(
        user=user,
        remember_me=payload.remember_me,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    await audit_service.log_event(
        event_type="LOGIN_SUCCESS",
        decision="ALLOW",
        actor_user_id=result.user.id,
        resource_type="session",
        resource_id=result.session.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    csrf_token = _set_auth_cookies(
        response,
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        settings=settings,
        remember_me=payload.remember_me,
    )
    if mfa_result.trusted_device_token:
        _set_mfa_trusted_device_cookie(
            response,
            token=mfa_result.trusted_device_token,
            settings=settings,
        )
    return LoginResponse(
        token=result.access_token,
        user=_serialize_user(result.user, db),
        session=_serialize_session(result.session),
        csrf_token=csrf_token,
    )


@router.post("/google-login", response_model=LoginResponse)
async def google_login(
    payload: GoogleLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    audit_service: AuditService = Depends(get_audit_service),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    user_repo = UserRepository(db)
    email = payload.email.strip().lower()
    user = user_repo.get_by_email(email)

    # Google sign-in authenticates an existing, already-invited account —
    # it never creates one. Silently provisioning a new account here would
    # be an open self-registration bypass (any Google account could reach
    # this endpoint), which is exactly what invite-only registration is
    # meant to close.
    if not user:
        await audit_service.log_event(
            event_type="LOGIN_FAILED",
            decision="DENY",
            ip_address=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
            metadata={"method": "google", "reason": "no_invited_account"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No account found for this email. Ask your organization admin for an invite.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )

    if not user.is_email_verified:
        user.is_email_verified = True
        db.commit()

    result = await auth_service.create_session_for_user(
        user=user,
        remember_me=True,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    await audit_service.log_event(
        event_type="LOGIN_SUCCESS",
        decision="ALLOW",
        actor_user_id=result.user.id,
        resource_type="session",
        resource_id=result.session.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={"method": "google"},
    )

    csrf_token = _set_auth_cookies(
        response,
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        settings=settings,
        remember_me=True,
    )

    return LoginResponse(
        token=result.access_token,
        user=_serialize_user(result.user, db),
        session=_serialize_session(result.session),
        csrf_token=csrf_token,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserResponse:
    payload = _serialize_user(current_user, db)
    # The csrf_token cookie already arrived with this request (the browser
    # attaches it same as any other cookie scoped to this API's domain) —
    # echoing it back here lets the frontend recover it into memory on page
    # reload without a fresh login, same reasoning as LoginResponse.csrf_token.
    payload.csrf_token = request.cookies.get(settings.csrf_cookie_name)
    return payload


@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
) -> UserResponse:
    updated = UserRepository(db).update_profile_fields(
        current_user,
        full_name=payload.full_name,
        major=payload.major,
        student_code=payload.student_code,
    )
    return _serialize_user(updated, db)


@router.put("/me/preferences", response_model=UserResponse)
async def update_my_preferences(
    payload: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
) -> UserResponse:
    patch = {
        "theme": payload.theme,
        "language": payload.language,
        "showMascot": payload.show_mascot,
    }
    updated = UserRepository(db).update_preferences(current_user, patch)
    return _serialize_user(updated, db)


@router.get("/mfa/status", response_model=MfaStatusResponse)
async def get_mfa_status(
    current_user: User = Depends(get_current_user_from_token),
    mfa_service: MfaService = Depends(get_mfa_service),
) -> MfaStatusResponse:
    status_result = await mfa_service.status(current_user.id)
    return MfaStatusResponse(**status_result)


@router.post("/mfa/totp/setup", response_model=MfaTotpSetupResponse)
async def setup_totp_mfa(
    request: Request,
    current_user: User = Depends(get_current_user_from_token),
    mfa_service: MfaService = Depends(get_mfa_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> MfaTotpSetupResponse:
    result = await mfa_service.start_totp_setup(current_user)
    await audit_service.log_event(
        event_type="MFA_TOTP_SETUP_STARTED",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="user",
        resource_id=current_user.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return MfaTotpSetupResponse(
        secret=result.secret,
        otpauth_uri=result.otpauth_uri,
        qr_code_uri=result.qr_code_uri,
    )


@router.post("/mfa/totp/enable", response_model=MfaEnableResponse)
async def enable_totp_mfa(
    payload: MfaEnableRequest,
    request: Request,
    current_user: User = Depends(get_current_user_from_token),
    mfa_service: MfaService = Depends(get_mfa_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> MfaEnableResponse:
    try:
        result = await mfa_service.enable_totp(current_user, payload.code)
    except MfaError as exc:
        await audit_service.log_event(
            event_type="MFA_TOTP_ENABLE_FAILED",
            decision="DENY",
            actor_user_id=current_user.id,
            resource_type="user",
            resource_id=current_user.id,
            ip_address=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await audit_service.log_event(
        event_type="MFA_TOTP_ENABLED",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="user",
        resource_id=current_user.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return MfaEnableResponse(status="ok", recovery_codes=result.recovery_codes)


@router.post("/mfa/recovery-codes/regenerate", response_model=MfaRecoveryCodesResponse)
async def regenerate_mfa_recovery_codes(
    payload: MfaEnableRequest,
    request: Request,
    current_user: User = Depends(get_current_user_from_token),
    mfa_service: MfaService = Depends(get_mfa_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> MfaRecoveryCodesResponse:
    try:
        recovery_codes = await mfa_service.regenerate_recovery_codes(
            current_user,
            payload.code,
        )
    except MfaError as exc:
        await audit_service.log_event(
            event_type="MFA_RECOVERY_CODES_REGENERATE_FAILED",
            decision="DENY",
            actor_user_id=current_user.id,
            resource_type="user",
            resource_id=current_user.id,
            ip_address=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await audit_service.log_event(
        event_type="MFA_RECOVERY_CODES_REGENERATED",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="user",
        resource_id=current_user.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return MfaRecoveryCodesResponse(recovery_codes=recovery_codes)


@router.post("/mfa/disable", response_model=MessageResponse)
async def disable_mfa(
    payload: MfaVerifyRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user_from_token),
    mfa_service: MfaService = Depends(get_mfa_service),
    audit_service: AuditService = Depends(get_audit_service),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    try:
        await mfa_service.disable_mfa(
            user=current_user,
            code=payload.code,
            recovery_code=payload.recovery_code,
        )
    except MfaError as exc:
        await audit_service.log_event(
            event_type="MFA_DISABLE_FAILED",
            decision="DENY",
            actor_user_id=current_user.id,
            resource_type="user",
            resource_id=current_user.id,
            ip_address=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    _clear_mfa_trusted_device_cookie(response, settings)
    await audit_service.log_event(
        event_type="MFA_DISABLED",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="user",
        resource_id=current_user.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return MessageResponse(status="ok", message="MFA has been disabled.")


@router.post("/password/forgot", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> MessageResponse:
    result = await password_reset_service.request_password_reset(payload.email)
    await audit_service.log_event(
        event_type="PASSWORD_RESET_REQUESTED",
        decision="ALLOW",
        actor_user_id=result.user_id,
        resource_type="user" if result.user_id else None,
        resource_id=result.user_id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={"issued": result.issued},
    )
    return MessageResponse(
        status="ok",
        message="If the account exists, password reset instructions have been sent.",
    )


@router.post("/password/reset", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> MessageResponse:
    try:
        user = await password_reset_service.reset_password(
            payload.token,
            payload.new_password,
        )
    except PasswordResetError as exc:
        await audit_service.log_event(
            event_type="PASSWORD_RESET_FAILED",
            decision="DENY",
            ip_address=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    await audit_service.log_event(
        event_type="PASSWORD_RESET_SUCCESS",
        decision="ALLOW",
        actor_user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={"sessions_revoked": True},
    )
    return MessageResponse(status="ok", message="Password has been reset.")


@router.post("/password/change", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user_from_token),
    session_id: str = Depends(get_current_session_id_from_token),
    auth_service: AuthService = Depends(get_auth_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> MessageResponse:
    try:
        await auth_service.change_password(
            current_user,
            current_password=payload.current_password,
            new_password=payload.new_password,
            current_session_id=session_id,
        )
    except InvalidCredentialsError as exc:
        await audit_service.log_event(
            event_type="PASSWORD_CHANGE_FAILED",
            decision="DENY",
            actor_user_id=current_user.id,
            resource_type="user",
            resource_id=current_user.id,
            ip_address=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PasswordPolicyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    await audit_service.log_event(
        event_type="PASSWORD_CHANGE_SUCCESS",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="user",
        resource_id=current_user.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={"other_sessions_revoked": True},
    )
    return MessageResponse(status="ok", message="Password has been changed.")


@router.post("/email/verify", response_model=MessageResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    email_verification_service: EmailVerificationService = Depends(
        get_email_verification_service
    ),
    audit_service: AuditService = Depends(get_audit_service),
) -> MessageResponse:
    try:
        user = await email_verification_service.verify_email(payload.token)
    except EmailVerificationError as exc:
        await audit_service.log_event(
            event_type="EMAIL_VERIFICATION_FAILED",
            decision="DENY",
            ip_address=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    await audit_service.log_event(
        event_type="EMAIL_VERIFICATION_SUCCESS",
        decision="ALLOW",
        actor_user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return MessageResponse(status="ok", message="Email has been verified.")


@router.post("/email/resend", response_model=MessageResponse)
async def resend_email_verification(
    payload: ResendEmailVerificationRequest,
    request: Request,
    email_verification_service: EmailVerificationService = Depends(
        get_email_verification_service
    ),
    audit_service: AuditService = Depends(get_audit_service),
) -> MessageResponse:
    result = await email_verification_service.resend_verification(payload.email)
    await audit_service.log_event(
        event_type="EMAIL_VERIFICATION_RESEND_REQUESTED",
        decision="ALLOW",
        actor_user_id=result.user_id,
        resource_type="user" if result.user_id else None,
        resource_id=result.user_id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={"issued": result.issued},
    )
    return MessageResponse(
        status="ok",
        message="If the account requires verification, instructions have been sent.",
    )


@router.post("/email/change", response_model=MessageResponse)
async def change_email(
    payload: ChangeEmailRequest,
    request: Request,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
    email_verification_service: EmailVerificationService = Depends(
        get_email_verification_service
    ),
    audit_service: AuditService = Depends(get_audit_service),
) -> MessageResponse:
    email = payload.email.strip().lower()

    # 1. Check if email is already registered by another user
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user and existing_user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    # 2. Update user's email address
    old_email = current_user.email
    current_user.email = email
    current_user.is_email_verified = True
    db.commit()

    # 3. Issue and send new verification token
    result = await email_verification_service.issue_verification_for_user(current_user)

    await audit_service.log_event(
        event_type="EMAIL_CHANGED",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="user",
        resource_id=current_user.id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata={"old_email": old_email, "new_email": email, "token_issued": result.issued},
    )

    return MessageResponse(
        status="ok",
        message="Verification email sent to new email address.",
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> RefreshResponse:
    refresh_token = _extract_refresh_token(request, settings)
    if not refresh_token:
        # An access-token cookie with no matching refresh-token cookie is
        # still enough to make CsrfProtectionMiddleware start requiring a
        # CSRF header (see the exception handler below) — clear whatever
        # auth cookies remain so the next request isn't stuck the same way.
        _clear_auth_cookies(response, settings)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    try:
        result = await auth_service.refresh_access_token(refresh_token)
    except (UnauthorizedError, InactiveUserError) as exc:
        # A dead/expired refresh token cookie can otherwise sit in the
        # browser indefinitely (its own Max-Age hasn't elapsed even though
        # the JWT inside has) -- CsrfProtectionMiddleware sees that cookie
        # and starts requiring a CSRF header on every mutating request, but
        # the frontend can never repopulate its in-memory CSRF token because
        # every refresh keeps failing this same way. That permanently locks
        # the browser out of login/demo-session/etc. behind a "CSRF
        # validation failed" 403 until cookies are cleared by hand. Clearing
        # here (same as the SessionError branch below) is the one place we
        # still hold a live `response` to fix that.
        _clear_auth_cookies(response, settings)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc
    except SessionError as exc:
        _clear_auth_cookies(response, settings)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh session",
        ) from exc

    csrf_token = _set_auth_cookies(
        response,
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        settings=settings,
        remember_me=result.session.remember_me,
    )
    return RefreshResponse(
        token=result.access_token,
        session=_serialize_session(result.session),
        csrf_token=csrf_token,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user_from_token),
    session_id: str = Depends(get_current_session_id_from_token),
    session_service: SessionService = Depends(get_session_service),
    audit_service: AuditService = Depends(get_audit_service),
    settings: Settings = Depends(get_settings),
) -> LogoutResponse:
    try:
        await session_service.revoke_session_for_user(session_id, current_user.id)
    except SessionError:
        pass
    await audit_service.log_event(
        event_type="LOGOUT",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="session",
        resource_id=session_id,
        ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    _clear_auth_cookies(response, settings)
    return LogoutResponse(status="ok")


@router.post("/logout-all", response_model=LogoutResponse)
async def logout_all(
    response: Response,
    current_user: User = Depends(get_current_user_from_token),
    session_service: SessionService = Depends(get_session_service),
    settings: Settings = Depends(get_settings),
) -> LogoutResponse:
    await session_service.revoke_all_user_sessions(current_user.id)
    _clear_auth_cookies(response, settings)
    return LogoutResponse(status="ok")


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user_from_token),
    session_id: str = Depends(get_current_session_id_from_token),
    session_service: SessionService = Depends(get_session_service),
) -> list[SessionResponse]:
    sessions = await session_service.list_active_sessions(current_user.id)
    return [
        _serialize_session(session, is_current=session.id == session_id)
        for session in sessions
    ]


@router.delete("/sessions/{session_id}", response_model=LogoutResponse)
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user_from_token),
    session_service: SessionService = Depends(get_session_service),
) -> LogoutResponse:
    try:
        await session_service.revoke_session_for_user(session_id, current_user.id)
    except SessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        ) from exc
    return LogoutResponse(status="ok")


def _extract_access_token(
    authorization: str | None,
    request: Request,
    settings: Settings,
) -> str:
    cookie_token = request.cookies.get(settings.access_token_cookie_name)
    if cookie_token:
        return cookie_token

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization token",
        )
    return authorization.split(" ", 1)[1]


def _serialize_user(user: User, db: Session | None = None) -> UserResponse:
    from src.services.onboarding_status import is_onboarded

    org = user.organization
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role if isinstance(user.role, str) else user.role.value,
        is_email_verified=user.is_email_verified,
        organization_id=org.id if org else None,
        organization_name=org.name if org else None,
        is_demo=bool(org and org.kind == "sandbox"),
        major=user.major,
        student_code=user.student_code,
        onboarded=is_onboarded(db, user) if db is not None else True,
        preferences=user.preferences or {},
    )


def _serialize_session(
    session: AuthSession,
    *,
    is_current: bool = False,
) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        device_label=session.device_label,
        ip_address=session.ip_address,
        remember_me=session.remember_me,
        expires_at=session.expires_at.isoformat(),
        absolute_expires_at=(
            session.absolute_expires_at.isoformat()
            if session.absolute_expires_at
            else None
        ),
        created_at=session.created_at.isoformat(),
        last_used_at=session.last_used_at.isoformat() if session.last_used_at else None,
        is_current=is_current,
    )


def _request_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    settings: Settings,
    remember_me: bool,
) -> str:
    """Sets the three auth cookies and returns the fresh CSRF token value.

    The CSRF cookie is JS-readable (httponly=False) by design, but that only
    lets the frontend recover it when frontend and backend share a
    registrable domain — a cross-domain deployment (Vercel + Render, etc.)
    never sees a cookie scoped to the API's own domain from `document.cookie`.
    Callers must also put this return value in the JSON response body so the
    frontend can hold it in memory and attach it as X-CSRF-Token itself.
    """
    response.set_cookie(
        key=settings.access_token_cookie_name,
        value=access_token,
        httponly=True,
        secure=_access_token_cookie_secure(settings),
        samesite=settings.access_token_cookie_samesite,
        domain=settings.access_token_cookie_domain,
        path=settings.access_token_cookie_path,
        max_age=settings.jwt_access_token_minutes * 60,
    )
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=_refresh_token_cookie_secure(settings),
        samesite=settings.refresh_token_cookie_samesite,
        domain=settings.refresh_token_cookie_domain,
        path=settings.refresh_token_cookie_path,
        max_age=_refresh_cookie_max_age(settings, remember_me),
    )
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        secure=_access_token_cookie_secure(settings),
        samesite=settings.access_token_cookie_samesite,
        domain=settings.access_token_cookie_domain,
        path=settings.access_token_cookie_path,
        max_age=_refresh_cookie_max_age(settings, remember_me),
    )
    return csrf_token


def _clear_auth_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.access_token_cookie_name,
        domain=settings.access_token_cookie_domain,
        path=settings.access_token_cookie_path,
    )
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        domain=settings.refresh_token_cookie_domain,
        path=settings.refresh_token_cookie_path,
    )
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        domain=settings.access_token_cookie_domain,
        path=settings.access_token_cookie_path,
    )


def _access_token_cookie_secure(settings: Settings) -> bool:
    if settings.access_token_cookie_secure is not None:
        return settings.access_token_cookie_secure
    return settings.app_env == "production"


def _refresh_token_cookie_secure(settings: Settings) -> bool:
    if settings.refresh_token_cookie_secure is not None:
        return settings.refresh_token_cookie_secure
    return settings.app_env == "production"


def _extract_refresh_token(request: Request, settings: Settings) -> str | None:
    return request.cookies.get(settings.refresh_token_cookie_name)


def _extract_mfa_trusted_device_token(
    request: Request,
    settings: Settings,
) -> str | None:
    return request.cookies.get(settings.mfa_trusted_device_cookie_name)


def _set_mfa_trusted_device_cookie(
    response: Response,
    *,
    token: str,
    settings: Settings,
) -> None:
    response.set_cookie(
        key=settings.mfa_trusted_device_cookie_name,
        value=token,
        httponly=True,
        secure=_mfa_trusted_device_cookie_secure(settings),
        samesite=settings.mfa_trusted_device_cookie_samesite,
        domain=settings.mfa_trusted_device_cookie_domain,
        path=settings.mfa_trusted_device_cookie_path,
        max_age=settings.mfa_trusted_device_days * 24 * 60 * 60,
    )


def _clear_mfa_trusted_device_cookie(
    response: Response,
    settings: Settings,
) -> None:
    response.delete_cookie(
        key=settings.mfa_trusted_device_cookie_name,
        domain=settings.mfa_trusted_device_cookie_domain,
        path=settings.mfa_trusted_device_cookie_path,
    )


def _mfa_trusted_device_cookie_secure(settings: Settings) -> bool:
    if settings.mfa_trusted_device_cookie_secure is not None:
        return settings.mfa_trusted_device_cookie_secure
    return settings.app_env == "production"


def _refresh_cookie_max_age(settings: Settings, remember_me: bool) -> int:
    days = (
        settings.remember_me_refresh_token_days
        if remember_me
        else settings.refresh_token_days
    )
    return days * 24 * 60 * 60
