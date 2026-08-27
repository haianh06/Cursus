"""Lexical retrieval over course document chunks (MVP without vector DB)."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from src.repositories.chunk_repository import ChunkRecord, ChunkRepository
from src.services.rag import embedding_service
from src.services.rag.query_normalization import expand_bilingual

# Cosine-similarity floor for a chunk to be included on embedding signal alone
# (i.e. it scored below the lexical min_score but semantically matches).
_EMBED_ONLY_MIN_SIMILARITY = 0.55
# How much an embedding match boosts a chunk that lexical scoring already found.
_EMBED_BOOST_WEIGHT = 2.0

_TOKEN_RE = re.compile(r"[a-z0-9àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ_]+", re.I)

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "is",
        "are",
        "was",
        "were",
        "be",
        "with",
        "this",
        "that",
        "what",
        "how",
        "why",
        "when",
        "where",
        "who",
        "which",
        "can",
        "you",
        "me",
        "my",
        "please",
        "help",
        "about",
        "và",
        "của",
        "các",
        "cho",
        "là",
        "có",
        "không",
        "trong",
        "với",
        "một",
        "những",
        "được",
        "này",
        "đó",
        "gì",
        "như",
        "thế",
        "nào",
        "tôi",
        "bạn",
        "em",
        "mình",
        "hãy",
        "giúp",
        "về",
    }
)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: ChunkRecord
    score: float


class RetrievalService:
    def __init__(
        self,
        repository: ChunkRepository,
        *,
        top_k: int = 5,
        min_score: float = 0.35,
    ) -> None:
        self._repository = repository
        self._top_k = top_k
        self._min_score = min_score

    def retrieve(
        self,
        *,
        subject_code: str,
        question: str,
        student_id: str | None = None,
    ) -> list[RetrievedChunk]:
        chunks = self._repository.list_chunks_for_course(
            subject_code=subject_code,
            student_id=student_id,
        )
        if not chunks:
            return []

        # Vietnamese question over an English syllabus: expand with the
        # bilingual alias map before tokenizing, otherwise lexical scoring
        # finds nothing (Data Contract §2.2).
        query_tokens = tokenize(expand_bilingual(question))
        if not query_tokens:
            return []

        lexical_by_chunk = {chunk.chunk_id: score_chunk(query_tokens, chunk) for chunk in chunks}
        similarity_by_chunk = self._embedding_similarities(subject_code=subject_code, question=question, chunks=chunks)

        scored: list[RetrievedChunk] = []
        for chunk in chunks:
            lexical_score = lexical_by_chunk.get(chunk.chunk_id, 0.0)
            similarity = similarity_by_chunk.get(chunk.chunk_id, 0.0)
            score = _combine_scores(lexical_score, similarity)
            if score >= self._min_score:
                scored.append(RetrievedChunk(chunk=chunk, score=score))

        scored.sort(key=lambda item: item.score, reverse=True)
        return _dedupe_retrieved(scored, limit=self._top_k)

    def _embedding_similarities(
        self,
        *,
        subject_code: str,
        question: str,
        chunks: list[ChunkRecord],
    ) -> dict[str, float]:
        """Cosine similarity per chunk_id, or {} when the embedding backend is off/unavailable."""
        if not embedding_service.has_embedding_backend():
            return {}
        query_vector = embedding_service.embed_query(question)
        if not query_vector:
            return {}
        items = [(chunk.chunk_id, f"{chunk.doc_title}\n{chunk.section or ''}\n{chunk.text}") for chunk in chunks]
        chunk_vectors = embedding_service.load_or_build_chunk_embeddings(
            course_code=subject_code, items=items
        )
        return {
            chunk_id: embedding_service.cosine_similarity(query_vector, vector)
            for chunk_id, vector in chunk_vectors.items()
        }


def _combine_scores(lexical_score: float, similarity: float) -> float:
    """Blend lexical + embedding signal. Never regresses lexical-only behavior
    when embedding is unavailable (similarity == 0.0 for every chunk in that case)."""
    if lexical_score > 0.0:
        return lexical_score + similarity * _EMBED_BOOST_WEIGHT
    if similarity >= _EMBED_ONLY_MIN_SIMILARITY:
        return similarity * _EMBED_BOOST_WEIGHT
    return 0.0


def tokenize(text: str) -> list[str]:
    tokens = [token.lower() for token in _TOKEN_RE.findall(text or "")]
    return [token for token in tokens if len(token) > 1 and token not in _STOPWORDS]


def _normalize_text(text: str) -> str:
    return " ".join((text or "").lower().split())


def _body_fingerprint(text: str) -> str:
    """Fingerprint ignoring the first line (often only the module title differs)."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if len(lines) <= 1:
        return _normalize_text(text)
    return _normalize_text("\n".join(lines[1:]))


def _dedupe_retrieved(
    scored: list[RetrievedChunk],
    *,
    limit: int,
) -> list[RetrievedChunk]:
    """Drop exact/near-duplicate chunks (common with synthetic seed data)."""
    unique: list[RetrievedChunk] = []
    seen_text: set[str] = set()
    seen_bodies: set[str] = set()
    for item in scored:
        fingerprint = _normalize_text(item.chunk.text)
        body = _body_fingerprint(item.chunk.text)
        if fingerprint in seen_text:
            continue
        if body and body in seen_bodies:
            continue
        seen_text.add(fingerprint)
        if body:
            seen_bodies.add(body)
        unique.append(item)
        if len(unique) >= limit:
            break
    return unique


def score_chunk(query_tokens: list[str], chunk: ChunkRecord) -> float:
    if not query_tokens:
        return 0.0

    haystack = f"{chunk.source_label}\n{chunk.doc_title}\n{chunk.section or ''}\n{chunk.text}".lower()
    hay_tokens = tokenize(haystack)
    if not hay_tokens:
        return 0.0

    # Term frequency with soft IDF-ish boost for rarer query terms in this chunk.
    tf: dict[str, int] = {}
    for token in hay_tokens:
        tf[token] = tf.get(token, 0) + 1

    score = 0.0
    exact_matches = 0
    for token in query_tokens:
        count = tf.get(token, 0)
        if count <= 0:
            # Soft prefix match only for longer technical tokens / course codes.
            if len(token) >= 5 and any(
                word.startswith(token) or token.startswith(word) and len(word) >= 4
                for word in tf
            ):
                score += 0.25
            continue
        exact_matches += 1
        score += 1.0 + math.log1p(count)
        if token in chunk.source_label.lower() or token in chunk.doc_title.lower():
            score += 0.5

    # Require at least one exact token hit so unrelated questions do not match.
    if exact_matches == 0:
        return 0.0

    coverage = exact_matches / len(query_tokens)
    return score * (0.5 + 0.5 * coverage)
