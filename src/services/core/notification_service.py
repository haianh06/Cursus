from html import escape
from urllib.parse import urlencode

from src.config import Settings
from src.services.core.email_service import EmailMessage, EmailService, NullEmailService

_VERIFY_PATH = "/auth/verify-email"
_RESET_PATH = "/auth/reset-password"
_INVITE_PATH = "/accept-invite"


class NotificationService:
    """Notification facade used by identity workflows.

    Email verification depends on this abstraction instead of SMTP/provider
    code directly. Future providers only need to implement EmailService.
    """

    def __init__(
        self,
        settings: Settings,
        email_service: EmailService | None = None,
    ) -> None:
        self._settings = settings
        self._email_service = email_service or NullEmailService()

    async def send_email_verification(self, email: str, token: str) -> None:
        verification_url = _verification_url(self._settings, token)
        brand = self._settings.smtp_from_name or "Neural Forge"
        await self._email_service.send(
            EmailMessage(
                to_email=email,
                subject=f"Confirm your email for {brand}",
                body_text=_verification_text(brand, verification_url),
                body_html=_verification_html(brand, verification_url),
            )
        )

    async def send_password_reset(self, email: str, token: str) -> None:
        reset_url = _password_reset_url(self._settings, token)
        brand = self._settings.smtp_from_name or "Neural Forge"
        await self._email_service.send(
            EmailMessage(
                to_email=email,
                subject=f"Reset your {brand} password",
                body_text=_password_reset_text(brand, reset_url),
                body_html=_password_reset_html(brand, reset_url),
            )
        )

    async def send_org_invite(
        self, email: str, token: str, *, role: str, full_name: str, org_name: str
    ) -> None:
        invite_url = _invite_url(self._settings, token)
        brand = self._settings.smtp_from_name or "Neural Forge"
        await self._email_service.send(
            EmailMessage(
                to_email=email,
                subject=f"You're invited to {org_name} on {brand}",
                body_text=_invite_text(brand, org_name, role, full_name, invite_url),
                body_html=_invite_html(brand, org_name, role, full_name, invite_url),
            )
        )

    async def send_instructor_digest(
        self, email: str, instructor_name: str, digest: dict
    ) -> None:
        """C1 — GV tu bam gui ban tom tat tuan ve dung email cua minh (khong
        phai cron/scheduled — du an nay chua co ha tang lich hen rieng)."""
        brand = self._settings.smtp_from_name or "Cursus"
        safe_brand = escape(brand)
        safe_name = escape(instructor_name)
        summary = digest.get("summary", {})
        subject = f"{brand} — Tóm tắt tuần ({digest.get('sinceDate', '')} → nay)"
        await self._email_service.send(
            EmailMessage(
                to_email=email,
                subject=subject,
                body_text=_digest_text(brand, instructor_name, digest),
                body_html=_digest_html(safe_brand, safe_name, digest, summary),
            )
        )


def _verification_url(settings: Settings, token: str) -> str:
    base = settings.email_verification_url_base or _frontend_auth_url(settings, _VERIFY_PATH)
    return _url_with_token(base, token)


def _password_reset_url(settings: Settings, token: str) -> str:
    base = settings.password_reset_url_base or _frontend_auth_url(settings, _RESET_PATH)
    return _url_with_token(base, token)


def _invite_url(settings: Settings, token: str) -> str:
    base = settings.org_invite_url_base or _frontend_auth_url(settings, _INVITE_PATH)
    return _url_with_token(base, token)


def _frontend_auth_url(settings: Settings, path: str) -> str:
    origin = settings.cors_origins.split(",")[0].strip().rstrip("/")
    if not origin:
        origin = "http://localhost:3000"
    return f"{origin}{path}"


def _url_with_token(base_url: str, token: str) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url.rstrip('/')}{separator}{urlencode({'token': token})}"


def _verification_text(brand: str, verification_url: str) -> str:
    return (
        f"Welcome to {brand}.\n\n"
        "Thanks for creating an account. Please confirm your email address "
        "to activate your account and sign in.\n\n"
        f"Verify your email:\n{verification_url}\n\n"
        "This link expires soon for your security. If the button or link does "
        "not work, copy and paste the URL into your browser.\n\n"
        f"If you did not create a {brand} account, you can safely ignore this email.\n\n"
        f"— The {brand} Team"
    )


def _password_reset_text(brand: str, reset_url: str) -> str:
    return (
        f"We received a request to reset your {brand} password.\n\n"
        "If you made this request, use the link below to choose a new password:\n\n"
        f"{reset_url}\n\n"
        "This link expires soon and can be used only once. If you did not "
        "request a password reset, you can safely ignore this email. "
        "Your password will remain unchanged.\n\n"
        f"— The {brand} Team"
    )


def _invite_text(brand: str, org_name: str, role: str, full_name: str, invite_url: str) -> str:
    return (
        f"Hi {full_name},\n\n"
        f"{org_name} has invited you to join {brand} as {role.title()}.\n\n"
        f"Accept your invitation and set your password:\n{invite_url}\n\n"
        "This link expires soon and can only be used once. If you were not "
        f"expecting this invitation, you can safely ignore this email.\n\n"
        f"— The {brand} Team"
    )


def _invite_html(brand: str, org_name: str, role: str, full_name: str, invite_url: str) -> str:
    safe_brand = escape(brand)
    safe_org = escape(org_name)
    safe_role = escape(role.title())
    safe_url = escape(invite_url, quote=True)
    return _auth_email_html(
        brand=safe_brand,
        title=f"You're invited to {safe_org}",
        intro=f"{safe_org} has invited you to join {safe_brand} as {safe_role}.",
        cta_label="Accept invitation",
        cta_url=safe_url,
        footer="This link expires soon and can only be used once.",
    )


def _verification_html(brand: str, verification_url: str) -> str:
    safe_brand = escape(brand)
    safe_url = escape(verification_url, quote=True)
    return _auth_email_html(
        brand=safe_brand,
        title="Confirm your email",
        intro=(
            f"Thanks for creating a {safe_brand} account. "
            "Confirm your email address to activate your account and sign in."
        ),
        cta_label="Verify email address",
        cta_url=safe_url,
        footer=(
            "This link expires soon for your security. "
            f"If you did not create a {safe_brand} account, you can safely ignore this email."
        ),
    )


def _password_reset_html(brand: str, reset_url: str) -> str:
    safe_brand = escape(brand)
    safe_url = escape(reset_url, quote=True)
    return _auth_email_html(
        brand=safe_brand,
        title="Reset your password",
        intro=(
            f"We received a request to reset your {safe_brand} password. "
            "Use the button below to choose a new password."
        ),
        cta_label="Reset password",
        cta_url=safe_url,
        footer=(
            "This link expires soon and can be used only once. "
            "If you did not request a password reset, you can safely ignore this email."
        ),
    )


def _auth_email_html(
    *,
    brand: str,
    title: str,
    intro: str,
    cta_label: str,
    cta_url: str,
    footer: str,
) -> str:
    return f"""\
<!DOCTYPE html>
<html lang="en">
  <body style="margin:0;padding:0;background:#f4f6f8;font-family:Segoe UI,Arial,sans-serif;color:#1f2937;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f6f8;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border-radius:12px;padding:32px;">
            <tr>
              <td style="font-size:13px;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;color:#0f766e;">
                {brand}
              </td>
            </tr>
            <tr>
              <td style="padding-top:16px;font-size:24px;font-weight:700;line-height:1.3;color:#111827;">
                {title}
              </td>
            </tr>
            <tr>
              <td style="padding-top:12px;font-size:15px;line-height:1.6;color:#374151;">
                {intro}
              </td>
            </tr>
            <tr>
              <td style="padding-top:28px;" align="center">
                <a href="{cta_url}"
                   style="display:inline-block;background:#0f766e;color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;padding:12px 24px;border-radius:8px;">
                  {cta_label}
                </a>
              </td>
            </tr>
            <tr>
              <td style="padding-top:28px;font-size:13px;line-height:1.6;color:#6b7280;">
                Or copy and paste this link into your browser:<br>
                <a href="{cta_url}" style="color:#0f766e;word-break:break-all;">{cta_url}</a>
              </td>
            </tr>
            <tr>
              <td style="padding-top:24px;border-top:1px solid #e5e7eb;font-size:13px;line-height:1.6;color:#6b7280;">
                {footer}
              </td>
            </tr>
            <tr>
              <td style="padding-top:16px;font-size:12px;color:#9ca3af;">
                — The {brand} Team
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def _digest_text(brand: str, instructor_name: str, digest: dict) -> str:
    summary = digest.get("summary", {})
    lines = [
        f"Chào {instructor_name},",
        "",
        f"Tóm tắt từ {digest.get('sinceDate', '')} đến nay trên {brand}:",
        f"- {summary.get('newRiskCount', 0)} case rủi ro mới",
        f"- {summary.get('newGuardrailCount', 0)} case Guardrail mới cần xem xét",
        f"- {summary.get('kudosCount', 0)} sinh viên đang được ghi nhận tích cực (Kudos)",
        "",
        "Mở dashboard để xem chi tiết và xử lý.",
        "",
        f"— {brand}",
    ]
    return "\n".join(lines)


def _digest_html(brand: str, instructor_name: str, digest: dict, summary: dict) -> str:
    rows = "".join(
        f"""<tr>
              <td style="padding:10px 0;font-size:15px;color:#111827;border-bottom:1px solid #e5e7eb;">{escape(label)}</td>
              <td style="padding:10px 0;font-size:15px;font-weight:700;color:#0f766e;text-align:right;border-bottom:1px solid #e5e7eb;">{value}</td>
            </tr>"""
        for label, value in [
            ("Case rủi ro mới", summary.get("newRiskCount", 0)),
            ("Case Guardrail mới", summary.get("newGuardrailCount", 0)),
            ("SV được ghi nhận Kudos", summary.get("kudosCount", 0)),
        ]
    )
    return f"""\
<!DOCTYPE html>
<html lang="vi">
  <body style="margin:0;padding:0;background:#f4f6f8;font-family:Segoe UI,Arial,sans-serif;color:#1f2937;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f6f8;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border-radius:12px;padding:32px;">
            <tr>
              <td style="font-size:13px;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;color:#0f766e;">
                {brand}
              </td>
            </tr>
            <tr>
              <td style="padding-top:16px;font-size:24px;font-weight:700;line-height:1.3;color:#111827;">
                Tóm tắt tuần cho {instructor_name}
              </td>
            </tr>
            <tr>
              <td style="padding-top:8px;font-size:14px;color:#6b7280;">
                Từ {escape(str(digest.get('sinceDate', '')))} đến nay
              </td>
            </tr>
            <tr>
              <td style="padding-top:20px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  {rows}
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding-top:24px;border-top:1px solid #e5e7eb;font-size:13px;line-height:1.6;color:#6b7280;">
                Mở dashboard {brand} để xem chi tiết và xử lý từng case.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
