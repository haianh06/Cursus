from src.config import get_settings


def has_configured_llm() -> bool:
    """True when ai-service is reachable in principle (an internal key is
    configured) — the actual LLM call now happens in ai-service
    (`src.services.core.ai_service_client`), not here. Same gate role as
    before: callers use this to decide whether to attempt an LLM-backed
    path at all before falling back to a deterministic result."""
    settings = get_settings()
    return bool((settings.ai_service_internal_key or "").strip())
