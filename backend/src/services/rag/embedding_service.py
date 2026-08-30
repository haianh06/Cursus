"""Embedding helpers for hybrid RAG retrieval (Gemini via LangChain).

Optional layer on top of `retrieval_service.py`'s lexical scoring. Disabled by
default — only activates when `settings.google_api_key` is a real key (not the
`"test-key"` placeholder), so existing lexical-only behavior is unchanged for
local dev/tests/demo-without-key. See docs/discovery/05_DEVELOP_FEATURE_SPEC.md
section 2 for the design this was adapted from.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from pathlib import Path

from src import paths
from src.config import get_settings

logger = logging.getLogger(__name__)

GEMINI_EMBED_MODEL = "models/gemini-embedding-001"
MAX_EMBED_CHARS = 2500
# Absolute, cwd-independent -- a bare relative Path("data/rag_cache") resolved
# differently depending on whether the process was launched from the repo
# root or from backend/, silently splitting the cache into two directories
# (data/rag_cache/ vs backend/data/rag_cache/) that never saw each other's
# entries. src.paths already solves exactly this (backend/data/ preferred,
# falls back to repo-root data/ or the Docker /app/data mount) but was never
# wired up anywhere -- use it here instead of hand-rolling another
# parents[N] path.
CACHE_DIR = paths.rag_cache_dir()

_PLACEHOLDER_KEYS = {"test-key", "changeme", "your-api-key", ""}


def has_embedding_backend() -> bool:
    settings = get_settings()
    key = (settings.google_api_key or "").strip()
    return key not in _PLACEHOLDER_KEYS and len(key) > 20


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Return unit vectors for `texts`, or None if embedding is unavailable/failed."""
    if not has_embedding_backend() or not texts:
        return None
    try:
        embedder = _gemini_embedder()
        raw = embedder.embed_documents(
            [(text or "")[:MAX_EMBED_CHARS] or " " for text in texts]
        )
        return [_l2_normalize([float(v) for v in vector]) for vector in raw]
    except Exception:
        logger.exception("embed_texts_failed")
        return None


def embed_query(text: str) -> list[float] | None:
    if not has_embedding_backend():
        return None
    try:
        embedder = _gemini_embedder()
        vector = embedder.embed_query((text or "")[:MAX_EMBED_CHARS] or " ")
        return _l2_normalize([float(v) for v in vector])
    except Exception:
        logger.exception("embed_query_failed")
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return max(0.0, min(1.0, dot))


def load_or_build_chunk_embeddings(
    *,
    course_code: str,
    items: list[tuple[str, str]],
) -> dict[str, list[float]]:
    """Cache embeddings for (chunk_id, text) pairs under data/rag_cache/."""
    code = course_code.strip().upper()
    cache_path = CACHE_DIR / f"db_embeddings_{code.lower()}.json"
    cached = _read_cache(cache_path)
    fingerprint = {chunk_id: _text_fingerprint(text) for chunk_id, text in items}

    missing: list[tuple[str, str]] = []
    for chunk_id, text in items:
        entry = cached.get(chunk_id)
        if not entry or entry.get("fp") != fingerprint[chunk_id] or not entry.get("v"):
            missing.append((chunk_id, text))

    if missing and has_embedding_backend():
        batch_size = 16
        for start in range(0, len(missing), batch_size):
            batch = missing[start : start + batch_size]
            vectors = embed_texts([text[:MAX_EMBED_CHARS] for _, text in batch])
            if not vectors:
                break
            for (chunk_id, _), vector in zip(batch, vectors, strict=True):
                cached[chunk_id] = {"fp": fingerprint[chunk_id], "v": vector}
        _write_cache(cache_path, cached)
        logger.info(
            "db_embeddings_updated course=%s new=%s total=%s",
            code,
            len(missing),
            len(cached),
        )

    return {
        chunk_id: entry["v"]
        for chunk_id, entry in cached.items()
        if isinstance(entry, dict) and entry.get("v")
    }


def _gemini_embedder():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    settings = get_settings()
    return GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBED_MODEL,
        google_api_key=settings.google_api_key,
        # No timeout here previously -- a slow/hanging Gemini call could
        # block retrieval indefinitely (see config.py's
        # embedding_request_timeout_seconds docstring for the incident).
        request_options={"timeout": settings.embedding_request_timeout_seconds},
    )


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def _text_fingerprint(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:16]


def _read_cache(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_cache(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
