"""Retrieval trên dữ liệu syllabus đã ingest (FR-2.1, FR-4.1).

Hai backend cùng một chữ ký `retrieve()`:

- **embedding** — dùng OpenAI khi `OPENAI_API_KEY` đã cấu hình thật. Vector được
  cache xuống đĩa nên chỉ tốn tiền ở lần build index đầu tiên.
- **lexical** — TF-IDF thuần Python, dùng khi chưa có API key. Chất lượng thấp
  hơn nhưng chạy offline, đủ để demo và test luồng end-to-end.

Backend được chọn tự động lúc build index; phần gọi (planner/qa/api) không cần
biết đang dùng cái nào.
"""

from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

from src.config import Settings, get_settings

logger = logging.getLogger(__name__)

DATA_DIR = Path("docs/planning/v2/data")
CACHE_DIR = Path("data/rag_cache")
EMBEDDING_MODEL = "text-embedding-3-small"

# Dưới ngưỡng này coi như không tìm thấy nguồn — để tầng trên trả đúng câu
# "Không tìm thấy thông tin liên quan trong tài liệu môn học" thay vì bịa.
MIN_SCORE_EMBEDDING = 0.25
MIN_SCORE_LEXICAL = 0.05

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)

# Chunk dài hơn ngưỡng này được tách nhỏ trước khi embed.
MAX_CHUNK_CHARS = 500

# Nhãn trường trong syllabus FLM ("Description:", "Time Allocation:",
# "Conditions to pass:"...) — dùng làm điểm cắt tự nhiên.
_FIELD_LABEL_RE = re.compile(r"^[A-Z][A-Za-z ]{2,40}:", re.MULTILINE)

# Chú giải tiếng Việt cho các trường của syllabus FLM.
#
# Syllabus viết bằng tiếng Anh, sinh viên hỏi bằng tiếng Việt. Với đoạn văn xuôi
# thì embedding đa ngữ bắc cầu được, nhưng đoạn dạng bảng số ("- Project - Part 1:
# 10%") thì vector nằm rất xa câu hỏi tự nhiên — đo được: chunk thang điểm xếp
# hạng 46/75 cho câu "Project Part 1 chiếm bao nhiêu phần trăm điểm".
#
# Chú giải chỉ được nối vào text đem đi EMBED, không đụng tới text hiển thị cho
# sinh viên. Đây là giải pháp tạm cho Mốc 1; hướng đúng ở Mốc 2 là sinh câu mô tả
# cho từng chunk bằng LLM lúc ingest (contextual retrieval).
FIELD_GLOSSARY: tuple[tuple[str, str], ...] = (
    ("progress marks", "thang điểm, tỷ trọng các đầu điểm, phần trăm đánh giá, cách tính điểm, chấm điểm"),
    ("conditions to pass", "điều kiện qua môn, điểm sàn, điểm trung bình tối thiểu, tiêu chí đạt"),
    ("time allocation", "phân bổ thời gian học, số giờ, số buổi, số tiết"),
    ("studenttasks", "nhiệm vụ sinh viên, nội quy lớp, điểm danh, tỷ lệ tham dự"),
    ("description", "mô tả môn học, nội dung tổng quan, mục tiêu môn"),
)


class Chunk(TypedDict):
    """Một đoạn syllabus kèm nhãn trích nguồn hiển thị được trên UI."""

    chunk_id: str
    subject_code: str
    section: str
    text: str
    source_label: str
    score: float


@dataclass(frozen=True)
class _IndexedChunk:
    """Chunk gốc kèm biểu diễn vector đã tính sẵn."""

    chunk_id: str
    subject_code: str
    subject_name: str
    section: str
    text: str
    source_label: str
    vector: dict[str, float] | list[float]


@dataclass(frozen=True)
class _Index:
    chunks: tuple[_IndexedChunk, ...]
    backend: str

    @property
    def min_score(self) -> float:
        return MIN_SCORE_EMBEDDING if self.backend == "embedding" else MIN_SCORE_LEXICAL


def retrieve(query: str, subject_code: str, k: int = 5) -> list[Chunk]:
    """Trả tối đa `k` chunk liên quan nhất của một môn, giảm dần theo điểm.

    Trả list rỗng khi không có chunk nào vượt ngưỡng — đó là tín hiệu "không có
    nguồn", tầng gọi phải xử lý chứ không được suy diễn tiếp.
    """
    if not query.strip():
        return []

    index = _get_index()
    candidates = [c for c in index.chunks if c.subject_code == subject_code.upper()]
    if not candidates:
        logger.warning("rag_subject_not_ingested", extra={"subject_code": subject_code})
        return []

    query_vector = _embed_query(query, index.backend)
    scored = ((_similarity(query_vector, c.vector, index.backend), c) for c in candidates)
    hits = sorted(
        ((score, chunk) for score, chunk in scored if score >= index.min_score),
        key=lambda pair: pair[0],
        reverse=True,
    )
    return [_to_chunk(chunk, score) for score, chunk in hits[:k]]


def list_ingested_subjects() -> list[dict]:
    """Danh sách môn đã ingest kèm số chunk — dùng cho bảng Curriculum (F6)."""
    counter: Counter[str] = Counter()
    names: dict[str, str] = {}
    for chunk in _get_index().chunks:
        counter[chunk.subject_code] += 1
        names.setdefault(chunk.subject_code, chunk.subject_name)
    return [
        {"subject_code": code, "subject_name": names[code], "chunk_count": count}
        for code, count in sorted(counter.items())
    ]


def _to_chunk(indexed: _IndexedChunk, score: float) -> Chunk:
    return {
        "chunk_id": indexed.chunk_id,
        "subject_code": indexed.subject_code,
        "section": indexed.section,
        "text": indexed.text,
        "source_label": indexed.source_label,
        "score": round(score, 4),
    }


@lru_cache(maxsize=1)
def _get_index() -> _Index:
    """Build index một lần cho cả vòng đời process."""
    raw = _load_raw_chunks()
    if not raw:
        logger.error("rag_no_chunks_found", extra={"data_dir": str(DATA_DIR)})
        return _Index(chunks=(), backend="lexical")

    settings = get_settings()
    if _has_real_api_key(settings):
        try:
            return _Index(chunks=_build_embedding_index(raw, settings), backend="embedding")
        except Exception as exc:  # noqa: BLE001 - SDK/network/auth: fall back to lexical
            logger.warning("rag_embedding_failed_fallback_lexical", extra={"error": str(exc)})

    return _Index(chunks=_build_lexical_index(raw), backend="lexical")


def _load_raw_chunks() -> list[dict]:
    """Đọc mọi file `chunks_*.json` trong thư mục dữ liệu.

    Thêm môn mới chỉ cần thả file vào, không phải sửa code.
    """
    records: list[dict] = []
    for path in sorted(DATA_DIR.glob("chunks_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("rag_chunk_file_unreadable", extra={"path": str(path), "error": str(exc)})
            continue
        subject_name = payload.get("subject_name", "")
        for chunk in payload.get("chunks", []):
            records.extend(_split_record(chunk, subject_name))
    return records


def _split_record(chunk: dict, subject_name: str) -> list[dict]:
    """Tách chunk dài thành nhiều đơn vị truy xuất, giữ nguyên nhãn trích nguồn.

    Một số chunk (điển hình là phần Overview của syllabus) gộp nhiều chủ đề rời
    nhau trong cùng một khối: mô tả môn, phân bổ giờ, nội quy, thang điểm. Embed
    cả khối thì vector bị loãng và chủ đề nhỏ như "Project - Part 1: 10%" không
    bao giờ lọt top-k.

    `source_label` và `section` giữ nguyên ở mọi mảnh, nên trích dẫn hiển thị cho
    sinh viên không đổi — chỉ đơn vị truy xuất nhỏ lại.
    """
    parts = _split_text(chunk.get("text", ""))
    if len(parts) == 1:
        return [{**chunk, "subject_name": subject_name}]
    return [
        {**chunk, "subject_name": subject_name, "chunk_id": f"{chunk['chunk_id']}#{i}", "text": part}
        for i, part in enumerate(parts, start=1)
    ]


def _split_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Cắt tại nhãn trường, rồi gộp lại cho tới khi chạm `max_chars`."""
    if len(text) <= max_chars:
        return [text]

    boundaries = [m.start() for m in _FIELD_LABEL_RE.finditer(text)]
    if len(boundaries) < 2:
        return [text]

    offsets = [0, *boundaries, len(text)] if boundaries[0] != 0 else [*boundaries, len(text)]
    # zip lệch 1 phần tử là cố ý: ghép mỗi mốc với mốc kế tiếp.
    segments = [text[start:end].strip() for start, end in zip(offsets, offsets[1:], strict=False)]
    return _merge_segments([s for s in segments if s], max_chars)


def _merge_segments(segments: list[str], max_chars: int) -> list[str]:
    merged: list[str] = []
    buffer = ""
    for segment in segments:
        candidate = f"{buffer}\n{segment}" if buffer else segment
        if buffer and len(candidate) > max_chars:
            merged.append(buffer)
            buffer = segment
        else:
            buffer = candidate
    if buffer:
        merged.append(buffer)
    return merged


def _embed_text(record: dict) -> str:
    """Text đưa đi embed, có gắn thêm ngữ cảnh môn/mục.

    Nhiều chunk chỉ dài ~200 ký tự và phần lớn là tiêu đề session, embed thô thì
    vector rất nhiễu. Thêm tên môn + tên mục vào giúp phân biệt rõ hơn hẳn.
    """
    subject = record.get("subject_name", "")
    code = record.get("subject_code", "")
    section = record.get("section", "")
    text = record.get("text", "")
    header = f"[{subject} ({code})] — {section}"
    gloss = _gloss_for(text)
    return f"{header}\n{gloss}\n{text}" if gloss else f"{header}\n{text}"


def _gloss_for(text: str) -> str:
    """Chú giải tiếng Việt cho các trường syllabus xuất hiện trong đoạn text."""
    lowered = text.lower()
    matched = [gloss for label, gloss in FIELD_GLOSSARY if label in lowered]
    return " · ".join(matched)


def _build_lexical_index(raw: list[dict]) -> tuple[_IndexedChunk, ...]:
    """TF-IDF sparse vector, chuẩn hoá L2 để cosine chỉ còn phép nhân vô hướng."""
    documents = [_tokenize(_embed_text(record)) for record in raw]
    idf = _compute_idf(documents)
    return tuple(
        _IndexedChunk(
            chunk_id=record["chunk_id"],
            subject_code=record["subject_code"],
            subject_name=record.get("subject_name", ""),
            section=record.get("section", ""),
            text=record.get("text", ""),
            source_label=record.get("source_label", ""),
            vector=_tfidf_vector(tokens, idf),
        )
        for record, tokens in zip(raw, documents, strict=True)
    )


def _build_embedding_index(raw: list[dict], settings: Settings) -> tuple[_IndexedChunk, ...]:
    """Embedding index, đọc cache trên đĩa nếu còn khớp với dữ liệu hiện tại."""
    texts = [_embed_text(record) for record in raw]
    cache_path = CACHE_DIR / f"embeddings_{EMBEDDING_MODEL}.json"
    vectors = _load_cached_vectors(cache_path, expected=len(texts))
    if vectors is None:
        vectors = _request_embeddings(texts, settings)
        _save_cached_vectors(cache_path, vectors)

    return tuple(
        _IndexedChunk(
            chunk_id=record["chunk_id"],
            subject_code=record["subject_code"],
            subject_name=record.get("subject_name", ""),
            section=record.get("section", ""),
            text=record.get("text", ""),
            source_label=record.get("source_label", ""),
            vector=_l2_normalize(vector),
        )
        for record, vector in zip(raw, vectors, strict=True)
    )


def _request_embeddings(texts: list[str], settings: Settings) -> list[list[float]]:
    """Gọi OpenAI embeddings. Import cục bộ để bản lexical không cần package này."""
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    logger.info("rag_embeddings_created", extra={"count": len(texts)})
    return [item.embedding for item in response.data]


def _load_cached_vectors(path: Path, expected: int) -> list[list[float]] | None:
    if not path.exists():
        return None
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    vectors = cached.get("vectors")
    if not isinstance(vectors, list) or len(vectors) != expected:
        logger.info("rag_cache_stale_rebuilding")
        return None
    return vectors


def _save_cached_vectors(path: Path, vectors: list[list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"model": EMBEDDING_MODEL, "vectors": vectors}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _embed_query(query: str, backend: str) -> dict[str, float] | list[float]:
    if backend == "embedding":
        return _l2_normalize(_request_embeddings([_translate_query(query)], get_settings())[0])
    return _tfidf_vector(_tokenize(query), _get_index_idf())


@lru_cache(maxsize=256)
def _translate_query(query: str) -> str:
    """Dịch câu hỏi sang tiếng Anh trước khi embed.

    Syllabus là tiếng Anh, sinh viên hỏi tiếng Việt. Đo trên chunk thang điểm:
    hỏi tiếng Việt xếp hạng 33/75, cùng ý hỏi bằng tiếng Anh xếp hạng 1/75 —
    khoảng cách đủ lớn để quyết định chuẩn hoá ngôn ngữ truy vấn.

    Kết quả được cache theo câu hỏi nên hỏi lại không tốn thêm lần gọi nào.
    Dịch lỗi thì dùng nguyên câu gốc, không làm hỏng luồng.
    """
    from src.services.core.llm import get_llm

    try:
        response = get_llm().invoke(
            [
                ("system", "Translate the user's text to English. Output only the translation, nothing else."),
                ("human", query),
            ]
        )
        translated = str(response.content).strip()
        return translated or query
    except Exception as exc:  # noqa: BLE001 - dịch hỏng thì lùi về câu gốc
        logger.warning("rag_query_translation_failed", extra={"error": str(exc)})
        return query


def _similarity(
    query_vector: dict[str, float] | list[float],
    chunk_vector: dict[str, float] | list[float],
    backend: str,
) -> float:
    """Cosine similarity. Cả hai vector đã chuẩn hoá L2 nên chỉ cần tích vô hướng."""
    if backend == "embedding":
        return sum(a * b for a, b in zip(query_vector, chunk_vector, strict=True))  # type: ignore[arg-type]

    assert isinstance(query_vector, dict) and isinstance(chunk_vector, dict)
    if len(query_vector) > len(chunk_vector):
        query_vector, chunk_vector = chunk_vector, query_vector
    return sum(weight * chunk_vector.get(term, 0.0) for term, weight in query_vector.items())


@lru_cache(maxsize=1)
def _get_index_idf() -> dict[str, float]:
    """IDF của corpus hiện tại, dùng để vector hoá câu truy vấn."""
    return _compute_idf([_tokenize(_embed_text(record)) for record in _load_raw_chunks()])


def _compute_idf(documents: list[list[str]]) -> dict[str, float]:
    total = len(documents) or 1
    document_frequency: Counter[str] = Counter()
    for tokens in documents:
        document_frequency.update(set(tokens))
    return {term: math.log(total / (1 + freq)) + 1.0 for term, freq in document_frequency.items()}


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    if not tokens:
        return {}
    counts = Counter(tokens)
    weights = {term: (count / len(tokens)) * idf.get(term, 0.0) for term, count in counts.items()}
    norm = math.sqrt(sum(w * w for w in weights.values()))
    if norm == 0.0:
        return {}
    return {term: weight / norm for term, weight in weights.items() if weight}


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _has_real_api_key(settings: Settings) -> bool:
    key = (settings.openai_api_key or "").strip()
    if not key or key.startswith("sk-your") or key.startswith("your-"):
        return False
    if key in {"test-key", "changeme", "sk-test"}:
        return False
    return True
