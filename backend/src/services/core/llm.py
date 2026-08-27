from src.config import get_settings


def has_configured_llm() -> bool:
    """True when an OpenAI(-compatible) API key is configured — the actual
    LLM call happens in `src.services.core.ai_engine`, not here. Same gate
    role as before: callers use this to decide whether to attempt an
    LLM-backed path at all before falling back to a deterministic result."""
    settings = get_settings()
    return bool((settings.openai_api_key or "").strip())
