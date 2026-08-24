from src.config import Settings
from src.services.core.email_service import EmailService, NullEmailService
from src.services.core.smtp_email_service import SMTPEmailService


def build_email_service(settings: Settings) -> EmailService:
    if settings.email_provider == "smtp":
        return SMTPEmailService(settings)
    return NullEmailService()
