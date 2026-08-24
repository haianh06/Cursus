"""Optional web search fallback for companion chat, used only when local
course material has no answer (retrieval came back `no_source`).

Config already exists in `src/config.py` (`web_search_enabled`,
`web_search_provider`, `web_search_max_results`, `tavily_api_key`) — added
ahead of this build. Follows this branch's "fail gracefully, no crash
without a key" convention (see `embedding_service.has_embedding_backend`):
`has_web_search()` reports whether a usable backend exists, and `search()`
never raises — any provider/network/import failure just yields no results
so a chat reply degrades to "I don't have this in the course material"
instead of a 500.

Deliberately much smaller than develop's `web_search_service.py`: develop
hardcoded per-course search profiles for a fixed 4-course demo catalog
(SSA101/PRF192/CEA201/CSI106). This branch's courses are dynamic per
organization, so there is no fixed catalog to hang per-course keyword
profiles off of — the query is built generically from the subject code +
question instead.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WebResult:
    title: str
    snippet: str
    url: str


def has_web_search() -> bool:
    settings = get_settings()
    if not settings.web_search_enabled:
        return False
    if settings.web_search_provider == "tavily":
        return bool((settings.tavily_api_key or "").strip())
    # ddg needs no API key, but does need the optional dependency installed.
    try:
        import duckduckgo_search  # noqa: F401
    except ImportError:
        return False
    return True


def search(*, query: str, subject_code: str | None = None) -> list[WebResult]:
    """Best-effort web search. Returns [] on any failure — never raises."""
    if not has_web_search() or not (query or "").strip():
        return []
    settings = get_settings()
    full_query = f"{subject_code} {query}".strip() if subject_code else query
    try:
        if settings.web_search_provider == "tavily":
            return _search_tavily(full_query, settings.web_search_max_results, settings.tavily_api_key)
        return _search_ddg(full_query, settings.web_search_max_results)
    except Exception:  # noqa: BLE001 — a broken search provider must not break chat
        logger.exception("web_search_failed provider=%s", settings.web_search_provider)
        return []


def _search_ddg(query: str, max_results: int) -> list[WebResult]:
    from duckduckgo_search import DDGS

    with DDGS() as ddgs:
        hits = list(ddgs.text(query, max_results=max_results))
    return [
        WebResult(
            title=str(hit.get("title") or ""),
            snippet=str(hit.get("body") or ""),
            url=str(hit.get("href") or ""),
        )
        for hit in hits
    ]


def _search_tavily(query: str, max_results: int, api_key: str | None) -> list[WebResult]:
    if not (api_key or "").strip():
        return []
    from tavily import TavilyClient

    client = TavilyClient(api_key=api_key)
    response = client.search(query=query, max_results=max_results)
    results = response.get("results") if isinstance(response, dict) else None
    if not isinstance(results, list):
        return []
    return [
        WebResult(
            title=str(item.get("title") or ""),
            snippet=str(item.get("content") or ""),
            url=str(item.get("url") or ""),
        )
        for item in results
    ]
