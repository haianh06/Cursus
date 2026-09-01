from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Cursus"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:3000"
    redis_url: str | None = None

    # LLM (Google Gemini) — values come from env / .env via pydantic-settings
    google_api_key: str = "test-key"
    # [Fixed 22/08] Was "gemini-2.5-flash" -- confirmed broken via a real API
    # call during the P0#5 small eval batch: 404 NOT_FOUND, "no longer
    # available to new users", recommending gemini-3.6-flash by name. Same
    # bug class as the GEMINI_EMBED_MODEL fix on 20/08 (embedding_service.py)
    # -- a hardcoded model name silently went stale; every LLM call in the
    # app was falling back to deterministic/extractive without a visible
    # crash until P0#8's trace fields made the failure legible. Verified via
    # `client.models.list()` with the real configured key that
    # "gemini-3.6-flash" is present and supports generateContent.
    model_name: str = "gemini-3.6-flash"
    # Comma-separated fallbacks tried after MODEL_NAME on 404/429/unavailable.
    # [Known gap, NOT fixed here — out of scope for the P0#5 eval task this
    # was found during] get_llm() (src/services/core/llm.py) never actually
    # reads this setting -- there is no fallback-retry logic anywhere in the
    # codebase, so this field has been silently inert. Both listed values
    # ("gemini-1.5-flash", "gemini-2.0-flash-lite") are ALSO not in the
    # current available-models list for this key, so even wiring this up
    # naively would not have helped tonight. Left as a known TODO rather
    # than expanding scope mid-eval.
    model_fallbacks: str = "gemini-1.5-flash,gemini-2.0-flash-lite"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    # Cursus Chat's interactive/structured generation (src.services.core.ai_engine,
    # folded in from the formerly-standalone ai-service so a single Render
    # deploy only needs one service). OPENAI_API_KEY may be issued by an
    # OpenAI-compatible gateway (e.g. a LiteLLM-style proxy) rather than
    # api.openai.com directly -- OPENAI_BASE_URL overrides the SDK's default
    # for that case. Browser clients never receive any of these values.
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_strong_model: str = "pro/gpt-5.6-terra"
    openai_light_model: str = "pro/gpt-5.6-luna"
    # 29/08 gap found via audit: neither `openai_client()`/`async_openai_client()`
    # nor any `.chat.completions.create()` call site set `timeout`/`max_tokens`
    # -- every call relied on the SDK's own default (600s client timeout, no
    # output cap at all beyond the model's own max). One slow/huge response
    # could tie up a sync worker thread for 10 minutes or burn an outsized
    # share of the $/day budget. 45s covers every real call site here (none
    # of them are long-running batch jobs); 2000 output tokens is generous
    # for a single JSON plan/quiz/reflection payload or one chat turn's
    # markdown reply (this app's answers are conversational, not essays) --
    # both are ordinary judgment calls, not something with real usage data to
    # tune against yet, so treat these as an approximate starting cap, not a
    # value with real load-testing behind it.
    llm_request_timeout_seconds: float = Field(default=45.0, gt=0)
    llm_max_output_tokens: int = Field(default=2000, ge=1)
    # Gemini embedding calls (backend/src/services/rag/embedding_service.py)
    # had NO timeout at all until 30/08 -- a slow/hanging call blocked
    # Cursus Chat's retrieval step for tens of seconds per enrolled course
    # (once per course, since each RetrievalService.retrieve() re-embedded
    # the same question). Kept short: embeddings are a single small call,
    # nothing like the LLM's own budget above.
    embedding_request_timeout_seconds: float = Field(default=8.0, gt=0)

    # Cursus Chat semantic answer cache (Redis-backed, in-memory fallback --
    # same pattern as rate_limiter.py). Scoped per exact enrolled-course-set
    # (see chat_cache_service.py) so a cache hit's citations can never
    # reference a course the asking student isn't enrolled in.
    chat_cache_enabled: bool = True
    chat_cache_similarity_threshold: float = Field(default=0.93, ge=0.0, le=1.0)
    chat_cache_max_entries_per_key: int = Field(default=200, ge=1)
    chat_cache_ttl_seconds: int = Field(default=14 * 24 * 3600, ge=60)

    # Small-talk semantic bypass (smalltalk_service.py): catches paraphrases
    # of greetings/thanks/"who are you" that chat_cache_service's exact-match
    # _CANNED_ANSWERS dict misses (e.g. "chao ban khoe khong"). Stricter than
    # chat_cache_similarity_threshold above -- a false positive here silently
    # replaces a real question with a small-talk reply instead of just
    # missing a cache hit, so it needs a higher bar.
    smalltalk_similarity_threshold: float = Field(default=0.86, ge=0.0, le=1.0)

    # Web search (used to augment retrieval when local context is insufficient)
    web_search_enabled: bool = True
    web_search_provider: Literal["ddg", "tavily"] = "ddg"
    web_search_max_results: int = Field(default=3, ge=1, le=8)
    tavily_api_key: str | None = None

    # Database — prefer Postgres in Docker / production; SQLite only for ad-hoc tests.
    # Password must come from env / .env (compose refuses to start without it).
    database_url: str = "postgresql://appuser:changeme-local-only@localhost:5432/appdb"
    # When true (and APP_ENV is development/test), entrypoint seeds if users empty.
    # Default false so shared/staging hosts never auto-load demo accounts.
    seed_on_start: bool = False

    # Authentication - JWT
    # No default: an unset or empty secret must fail fast instead of silently
    # signing tokens with a weak/None key.
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "cursus-auth"
    jwt_audience: str = "cursus-clients"
    jwt_access_token_minutes: int = Field(default=15, ge=1, le=1440)

    # Authentication - Access Token Cookie
    access_token_cookie_name: str = "access_token"
    # None = derive from app_env (secure only in production); set explicitly
    # to override per-deployment.
    access_token_cookie_secure: bool | None = None
    access_token_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    access_token_cookie_domain: str | None = None
    access_token_cookie_path: str = "/"

    # Session / Refresh Token
    refresh_token_days: int = Field(default=7, ge=1, le=90)
    remember_me_refresh_token_days: int = Field(default=30, ge=1, le=180)
    session_absolute_days: int = Field(default=30, ge=1, le=365)
    remember_me_session_absolute_days: int = Field(default=90, ge=1, le=365)
    refresh_token_cookie_name: str = "refresh_token"
    refresh_token_cookie_secure: bool | None = None
    refresh_token_cookie_samesite: Literal["lax", "strict", "none"] = "strict"
    refresh_token_cookie_domain: str | None = None
    refresh_token_cookie_path: str = "/api/v1/auth/refresh"
    password_reset_token_minutes: int = Field(default=30, ge=5, le=1440)
    password_reset_url_base: str | None = None
    email_verification_token_minutes: int = Field(default=1440, ge=5, le=10080)
    email_verification_url_base: str | None = None
    org_invite_token_minutes: int = Field(default=10080, ge=5, le=43200)  # default 7 days
    org_invite_url_base: str | None = None
    # Was 60 -- a demo walkthrough that pauses to explore a role (e.g. going
    # into Mock LMS/EduSync and back) routinely outlasted that, silently
    # killing the whole session's refresh token (not just the access token)
    # via SessionService's absolute_expires_at cap and forcing a re-login
    # with no warning. 240 min (4h) comfortably covers one sitting without
    # going unbounded.
    demo_session_token_minutes: int = Field(default=240, ge=5, le=480)
    email_provider: Literal["none", "smtp"] = "none"
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str = "Cursus"
    smtp_use_tls: bool = True

    # MFA
    mfa_issuer: str = "Cursus"
    mfa_secret_encryption_key: str | None = None
    mfa_totp_drift_steps: int = Field(default=1, ge=0, le=2)
    mfa_recovery_code_count: int = Field(default=10, ge=5, le=20)
    mfa_trusted_device_days: int = Field(default=30, ge=1, le=365)
    mfa_trusted_device_cookie_name: str = "mfa_trusted_device"
    mfa_trusted_device_cookie_secure: bool | None = None
    mfa_trusted_device_cookie_samesite: Literal["lax", "strict", "none"] = "strict"
    mfa_trusted_device_cookie_domain: str | None = None
    mfa_trusted_device_cookie_path: str = "/api/v1/auth"
    mfa_max_attempts: int = Field(default=5, ge=1, le=20)
    mfa_lockout_minutes: int = Field(default=10, ge=1, le=1440)

    # Security middleware
    rate_limit_enabled: bool = True
    rate_limit_requests: int = Field(default=1000, ge=1, le=100000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    csrf_protection_enabled: bool = True
    csrf_cookie_name: str = "csrf_token"
    csrf_header_name: str = "x-csrf-token"

    # Cursus Chat — operational safety nets. Defaults below are engineering
    # judgment calls (spam/cost circuit-breakers), NOT a substitute for an
    # actual product/compliance decision on data-retention or crisis-response
    # policy — an org should override these via env once that review happens.
    cursus_chat_rate_limit_per_minute: int = Field(default=10, ge=1, le=120)
    # System-wide ai-service call budget per rolling day, across chat +
    # Plan/Reflection/Practice/Quiz generation. Not a real dollar cap (this
    # code has no visibility into OpenAI billing) -- a circuit breaker so a
    # bug or abuse loop can't run up an unbounded bill unnoticed overnight.
    llm_daily_request_limit: int = Field(default=2000, ge=1)
    # Recipient for crisis-safety escalations and ops alerts (LLM budget
    # exceeded, etc). No default -- an unset value means these alerts are
    # logged only, never emailed, which a real deployment must not rely on.
    crisis_escalation_email: str | None = None
    ops_alert_email: str | None = None
    chat_action_proposal_retention_days: int = Field(default=30, ge=1, le=365)
    chat_briefing_impression_retention_days: int = Field(default=90, ge=1, le=730)

    # Vector Store
    chroma_persist_dir: str = "./data/chroma"

    # Mock LMS integration (mục 6.6) — a genuinely separate app/DB, reached only
    # over its own OAuth-protected REST API. `mock_lms_client_id`/`_secret` are
    # None by default so a missing credential fails fast (mock_lms_client.py
    # raises) instead of silently skipping sync.
    mock_lms_base_url: str = "http://127.0.0.1:9000"
    mock_lms_client_id: str | None = None
    mock_lms_client_secret: str | None = None

    # Mock LMS web-viewer SSO (mục 6.6 — thay Basic Auth riêng bằng danh tính
    # Cursus). Đây là 1 luồng OIDC-style code-exchange thu gọn, KHÔNG chia sẻ
    # session cookie/JWT signing secret giữa 2 origin (2 hệ thống vẫn tách
    # biệt thật, chỉ chuyển giao danh tính qua 1 mã dùng 1 lần, hạn dùng ngắn).
    # `mock_lms_sso_shared_secret` xác thực riêng lệnh gọi server-to-server
    # đổi mã lấy danh tính (không phải mật khẩu người dùng nào).
    mock_lms_sso_shared_secret: str | None = None
    mock_lms_sso_allowed_redirect_prefixes: str = "http://127.0.0.1:9000,http://localhost:9000"
    # Where the "not logged in" page (src/api/mock_lms_sso.py authorize())
    # sends the visitor to actually log in — the Cursus *frontend* dev
    # server, not this backend's own base_url.
    cursus_frontend_url: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
