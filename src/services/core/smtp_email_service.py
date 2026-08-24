import asyncio
import smtplib
from email.message import EmailMessage as SmtpEmailMessage
from email.utils import formataddr

from src.config import Settings
from src.services.core.email_service import EmailMessage


class SmtpEmailConfigurationError(Exception):
    pass


class SMTPEmailService:
    def __init__(self, settings: Settings) -> None:
        if not settings.smtp_host:
            raise SmtpEmailConfigurationError("SMTP_HOST is required")
        if not settings.smtp_from_email:
            raise SmtpEmailConfigurationError("SMTP_FROM_EMAIL is required")

        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._username = settings.smtp_username
        self._password = settings.smtp_password
        self._from_email = settings.smtp_from_email
        self._from_name = settings.smtp_from_name
        self._use_tls = settings.smtp_use_tls

    async def send(self, message: EmailMessage) -> None:
        await asyncio.to_thread(self._send_sync, message)

    def _send_sync(self, message: EmailMessage) -> None:
        smtp_message = SmtpEmailMessage()
        smtp_message["From"] = formataddr((self._from_name, self._from_email))
        smtp_message["To"] = message.to_email
        smtp_message["Subject"] = message.subject
        smtp_message.set_content(message.body_text)
        if message.body_html:
            smtp_message.add_alternative(message.body_html, subtype="html")

        with smtplib.SMTP(self._host, self._port, timeout=15) as smtp:
            if self._use_tls:
                smtp.starttls()
            if self._username and self._password:
                smtp.login(self._username, self._password)
            smtp.send_message(smtp_message)
