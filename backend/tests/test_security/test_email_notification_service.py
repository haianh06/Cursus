import pytest

from src.config import Settings
from src.services.core.email_provider import build_email_service
from src.services.core.email_service import EmailMessage
from src.services.core.notification_service import NotificationService
from src.services.core.smtp_email_service import SMTPEmailService


class FakeEmailService:
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


@pytest.mark.asyncio
async def test_notification_service_sends_email_verification_link():
    email_service = FakeEmailService()
    settings = Settings(
        jwt_secret_key="unit-test-secret-key-at-least-32-characters-long",
        email_verification_url_base="https://app.example.test/verify-email",
    )
    notifications = NotificationService(settings, email_service)

    await notifications.send_email_verification(
        "user@example.test",
        "raw-verification-token",
    )

    assert len(email_service.sent) == 1
    message = email_service.sent[0]
    expected = "https://app.example.test/verify-email?token=raw-verification-token"
    assert message.to_email == "user@example.test"
    assert "Confirm your email" in message.subject
    assert expected in message.body_text
    assert message.body_html is not None
    assert expected in message.body_html
    assert 'href="https://app.example.test/verify-email?token=raw-verification-token"' in message.body_html


@pytest.mark.asyncio
async def test_notification_service_falls_back_to_cors_frontend_url():
    email_service = FakeEmailService()
    settings = Settings(
        jwt_secret_key="unit-test-secret-key-at-least-32-characters-long",
        cors_origins="http://localhost:3000,http://127.0.0.1:3000",
        email_verification_url_base=None,
        password_reset_url_base=None,
    )
    notifications = NotificationService(settings, email_service)

    await notifications.send_email_verification(
        "user@example.test",
        "fallback-token",
    )

    expected = "http://localhost:3000/auth/verify-email?token=fallback-token"
    assert expected in email_service.sent[0].body_text
    assert expected in (email_service.sent[0].body_html or "")


@pytest.mark.asyncio
async def test_notification_service_sends_password_reset_link():
    email_service = FakeEmailService()
    settings = Settings(
        jwt_secret_key="unit-test-secret-key-at-least-32-characters-long",
        password_reset_url_base="https://app.example.test/reset-password",
    )
    notifications = NotificationService(settings, email_service)

    await notifications.send_password_reset(
        "user@example.test",
        "raw-reset-token",
    )

    assert len(email_service.sent) == 1
    message = email_service.sent[0]
    expected = "https://app.example.test/reset-password?token=raw-reset-token"
    assert message.to_email == "user@example.test"
    assert "Reset" in message.subject
    assert expected in message.body_text
    assert message.body_html is not None
    assert expected in message.body_html


def test_email_provider_builds_smtp_service_from_settings():
    settings = Settings(
        jwt_secret_key="unit-test-secret-key-at-least-32-characters-long",
        email_provider="smtp",
        smtp_host="smtp.example.test",
        smtp_from_email="no-reply@example.test",
    )

    assert isinstance(build_email_service(settings), SMTPEmailService)


@pytest.mark.asyncio
async def test_smtp_email_service_sends_message(monkeypatch):
    sent_messages = []

    class FakeSmtp:
        def __init__(self, host, port, timeout):
            self.host = host
            self.port = port
            self.timeout = timeout
            self.started_tls = False
            self.logged_in = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def starttls(self):
            self.started_tls = True

        def login(self, username, password):
            self.logged_in = (username, password)

        def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setattr("src.services.core.smtp_email_service.smtplib.SMTP", FakeSmtp)
    settings = Settings(
        jwt_secret_key="unit-test-secret-key-at-least-32-characters-long",
        smtp_host="smtp.example.test",
        smtp_port=587,
        smtp_username="user",
        smtp_password="password",
        smtp_from_email="no-reply@example.test",
        smtp_from_name="Neural Forge",
        smtp_use_tls=True,
    )
    service = SMTPEmailService(settings)

    await service.send(
        EmailMessage(
            to_email="user@example.test",
            subject="Verify",
            body_text="Hello",
            body_html="<p>Hello</p>",
        )
    )

    assert len(sent_messages) == 1
    assert sent_messages[0]["To"] == "user@example.test"
    assert sent_messages[0]["Subject"] == "Verify"
    assert sent_messages[0].get_body(preferencelist=("html",)).get_content().strip() == "<p>Hello</p>"
