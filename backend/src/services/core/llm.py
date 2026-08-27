from langchain_google_genai import ChatGoogleGenerativeAI

from src.config import get_settings

_PLACEHOLDER_KEYS = frozenset({"", "test-key", "sk-your-key-here", "changeme"})


def get_llm() -> ChatGoogleGenerativeAI:
    """Create the shared chat model client (Google Gemini)."""
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=settings.model_name,
        google_api_key=settings.google_api_key,
        temperature=settings.llm_temperature,
    )


def has_configured_llm() -> bool:
    """True when a real (non-placeholder) Gemini API key is configured.

    Same placeholder set QaAnswerService checks locally — kept here too so
    other callers (e.g. plan_builder) don't have to duplicate the list.
    """
    settings = get_settings()
    key = (settings.google_api_key or "").strip()
    if key in _PLACEHOLDER_KEYS:
        return False
    if key.startswith("AQ.your") or key.startswith("your-"):
        return False
    return True
