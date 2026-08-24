import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    to_email: str
    subject: str
    body_text: str
    body_html: str | None = None


class EmailService(Protocol):
    async def send(self, message: EmailMessage) -> None:
        """Send an email message using the configured provider."""


class NullEmailService:
    """Default non-network email provider.

    Production deployments can replace this with SMTP, SendGrid, Resend,
    AWS SES, or another provider without changing identity services.
    """

    async def send(self, message: EmailMessage) -> None:
        logger.info(
            "Email delivery skipped by NullEmailService",
            extra={"to": message.to_email, "subject": message.subject},
        )
