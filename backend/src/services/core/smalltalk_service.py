"""Semantic bypass for small talk -- sits between chat_cache_service's Tier 1
exact-match ``_CANNED_ANSWERS`` and Tier 2 per-course semantic answer cache.

Tier 1 is free (no embedding call) but only matches strings it already knows
verbatim. This tier catches paraphrases of the same handful of intents
(greeting, thanks, "who are you", ...) by cosine similarity against a small
curated bank (smalltalk_bank.py), using the same embedding the caller already
computed for retrieval/Tier-2 lookup -- so a miss here costs nothing extra,
and a hit skips retrieval and the LLM call entirely, same as Tier 1.
"""

from __future__ import annotations

import hashlib
import json
import logging

from src import paths
from src.config import get_settings
from src.knowledge.smalltalk_bank import SMALLTALK_ENTRIES
from src.services.rag import embedding_service

logger = logging.getLogger(__name__)

_CACHE_PATH = paths.rag_cache_dir() / "smalltalk_embeddings.json"

# None = not loaded yet; [] = loaded but unavailable (no embedding backend).
_bank: list[tuple[list[float], str]] | None = None


def _bank_fingerprint() -> str:
    payload = json.dumps(
        [{"id": e.id, "variants": e.variants, "answer": e.answer} for e in SMALLTALK_ENTRIES],
        sort_keys=True,
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _read_cache() -> dict:
    if not _CACHE_PATH.is_file():
        return {}
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_cache(fingerprint: str, entries: list[tuple[list[float], str]]) -> None:
    try:
        payload = {"fingerprint": fingerprint, "entries": [{"v": v, "answer": a} for v, a in entries]}
        _CACHE_PATH.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        logger.exception("smalltalk_cache_write_failed")


def _load_bank() -> list[tuple[list[float], str]]:
    global _bank
    if _bank is not None:
        return _bank
    if not embedding_service.has_embedding_backend():
        _bank = []
        return _bank

    fingerprint = _bank_fingerprint()
    cached = _read_cache()
    if cached.get("fingerprint") == fingerprint and cached.get("entries"):
        _bank = [(item["v"], item["answer"]) for item in cached["entries"]]
        return _bank

    variants: list[str] = []
    answers: list[str] = []
    for entry in SMALLTALK_ENTRIES:
        for variant in entry.variants:
            variants.append(variant)
            answers.append(entry.answer)

    vectors = embedding_service.embed_texts(variants)
    if not vectors:
        _bank = []
        return _bank

    _bank = list(zip(vectors, answers, strict=True))
    _write_cache(fingerprint, _bank)
    return _bank


def match(query_vector: list[float] | None) -> str | None:
    """Return the canonical small-talk answer for ``query_vector``, or None
    when nothing in the bank clears ``settings.smalltalk_similarity_threshold``
    (or the embedding backend is unavailable)."""
    if not query_vector:
        return None
    bank = _load_bank()
    if not bank:
        return None

    settings = get_settings()
    best_answer: str | None = None
    best_similarity = 0.0
    for vector, answer in bank:
        similarity = embedding_service.cosine_similarity(query_vector, vector)
        if similarity > best_similarity:
            best_similarity, best_answer = similarity, answer
    if best_answer is not None and best_similarity >= settings.smalltalk_similarity_threshold:
        return best_answer
    return None
