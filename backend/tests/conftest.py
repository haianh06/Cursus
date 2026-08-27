import os
from pathlib import Path
from unittest.mock import AsyncMock

# --- H7: isolate API tests on an ephemeral SQLite DB (not a shared leftover file) ---
_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEST_DB_PATH = _REPO_ROOT / "data" / "pytest.db"

os.environ["APP_ENV"] = "test"
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "unit-test-secret-key-at-least-32-characters-long",
)
# Force has_configured_llm() to False by default so LLM-backed paths take
# their deterministic fallback and tests never make a real network call,
# even when a real OPENAI_API_KEY is present in the developer's own .env
# (loaded by src.config's load_dotenv()). Individual tests that need the
# "LLM configured" path already monkeypatch has_configured_llm() directly
# rather than relying on this env var, so overriding it here is safe.
os.environ["OPENAI_API_KEY"] = ""
# Cookie jar in httpx TestClient would otherwise trip CSRF on refresh/login
# chains. CSRF behavior is covered by test_security_infrastructure.py.
os.environ["CSRF_PROTECTION_ENABLED"] = "false"

if "TEST_DATABASE_URL" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
else:
    _TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()
    os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH.as_posix()}"

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

from src.config import get_settings  # noqa: E402

get_settings.cache_clear()

from src.db.connection import SessionLocal, engine  # noqa: E402
from src.db.models import (  # noqa: E402
    AuditLog,
    AuthSession,
    Base,
    MfaRecoveryCode,
    MfaTotpCredential,
    MfaTrustedDevice,
    VerificationToken,
)
from src.main import app  # noqa: E402
from tests.support.api_demo_dataset import ensure_api_demo_dataset  # noqa: E402


def _prepare_schema() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_user_email_verification_column()
    _ensure_user_is_active_column()
    AuditLog.__table__.create(bind=engine, checkfirst=True)
    AuthSession.__table__.create(bind=engine, checkfirst=True)
    _ensure_session_absolute_expires_at_column()
    VerificationToken.__table__.create(bind=engine, checkfirst=True)
    MfaTotpCredential.__table__.create(bind=engine, checkfirst=True)
    MfaRecoveryCode.__table__.create(bind=engine, checkfirst=True)
    MfaTrustedDevice.__table__.create(bind=engine, checkfirst=True)


@pytest.fixture(scope="session", autouse=True)
def _session_demo_dataset() -> None:
    """Create schema + minimal demo users once per pytest process."""
    _prepare_schema()
    db = SessionLocal()
    try:
        ensure_api_demo_dataset(db)
    finally:
        db.close()


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing API endpoints."""
    # Keep schema present even if a test dropped tables.
    _prepare_schema()
    db = SessionLocal()
    try:
        ensure_api_demo_dataset(db)
    finally:
        db.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_llm():
    """Mock LLM to avoid calling OpenAI during tests."""
    mock = AsyncMock()
    mock.ainvoke.return_value = AsyncMock(content="Mocked LLM response")
    return mock


def _ensure_user_email_verification_column() -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "is_email_verified" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN is_email_verified BOOLEAN DEFAULT 1")
        )


def _ensure_user_is_active_column() -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "is_active" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")
        )


def _ensure_session_absolute_expires_at_column() -> None:
    inspector = inspect(engine)
    if "sessions" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("sessions")}
    if "absolute_expires_at" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE sessions ADD COLUMN absolute_expires_at DATETIME")
        )
