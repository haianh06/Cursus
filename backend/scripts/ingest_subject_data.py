"""One-time ingest of the real lecture/textbook PDFs under data/subject_data
into Course/Document/DocumentChunk (DB) and docs/planning/v2/data/chunks_
{CODE}.json (the file rag.py loads directly at runtime), so course content
for all 26 subjects is grounded in real material instead of synthetic
placeholders.

Text quality varies by content type: plain prose/code slides extract
cleanly; math-notation-heavy slides (e.g. MAS291) extract with visible
noise since PDF text streams don't preserve formula/subscript structure —
this is an inherent PDF-extraction limitation, not something this script
tries to fully fix. A lightweight cleanup pass (drop near-empty/repeated
lines) reduces the worst of it.

Idempotent per PDF: re-running updates existing Document/DocumentChunk rows
in place rather than duplicating them (matches scripts/seed_curriculum.py's
upsert convention).

Usage:
    python scripts/ingest_subject_data.py [--courses CEA201,SSA101] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import uuid
from collections import deque
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pymupdf  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ingest-subject-data")

SUBJECT_DATA_DIR = ROOT / "data" / "subject_data"
CHUNKS_DIR = ROOT / "docs" / "planning" / "v2" / "data"
CURRICULUM_FILE = CHUNKS_DIR / "courses_BIT_SE_K20D_K21A.json"

CHUNK_SIZE = 1100
MIN_EXTRACTED_CHARS = 50
SOURCE_TAG = "subject_data_pdf"

# 4 subject_data codes with no match in the official 48-subject curriculum.
FALLBACK_NAMES = {
    "AIL304M": "Applied Machine Learning",
    "DBM301": "Database Management",
    "DPL303M": "Deep Learning",
    "PRO102": "Programming Fundamentals with Java (early code for PRO192)",
}

_SLOT_RE = re.compile(r"slot[_\s]*0*(\d+)", re.IGNORECASE)
_CH_RE = re.compile(r"\bch(?:apter)?[_\s]*0*(\d+)", re.IGNORECASE)
_LEADING_NUM_RE = re.compile(r"^\s*(\d+)")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    return _SLUG_RE.sub("_", value.lower()).strip("_")[:60]


def load_official_names() -> dict[str, str]:
    if not CURRICULUM_FILE.is_file():
        return {}
    payload = json.loads(CURRICULUM_FILE.read_text(encoding="utf-8"))
    names: dict[str, str] = {}
    for subject in payload.get("subjects", []):
        code = str(subject.get("Subject Code") or "").strip().upper()
        name = str(subject.get("Subject Name") or "").strip()
        if code and name:
            names[code] = name
    return names


def course_name_for(code: str, official_names: dict[str, str]) -> str:
    return official_names.get(code.upper()) or FALLBACK_NAMES.get(code.upper()) or code


def _slot_number_for(filename: str, fallback_index: int) -> int:
    for pattern in (_SLOT_RE, _CH_RE, _LEADING_NUM_RE):
        match = pattern.search(filename)
        if match:
            return max(1, min(99, int(match.group(1))))
    return fallback_index


def clean_text(raw: str) -> str:
    """Drop near-empty/duplicate lines (page-number fragments, repeated
    logos/headers) without trying to reconstruct visual reading order."""
    # Some PDFs' text streams decode to embedded NUL bytes (malformed font
    # encodings) — Postgres rejects those outright in a text column.
    raw = raw.replace("\x00", "")
    kept: list[str] = []
    recent: deque[str] = deque(maxlen=6)
    for line in raw.splitlines():
        stripped = line.strip()
        if len(stripped) <= 2 or stripped in recent:
            continue
        recent.append(stripped)
        kept.append(stripped)
    return " ".join(kept)


def chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    text = text.strip()
    return [piece for i in range(0, len(text), size) if (piece := text[i : i + size].strip())]


def extract_course_pdfs(code: str, course_dir: Path) -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
    """Return (chunk_records, skipped) across every PDF in one course folder."""
    entries: list[dict[str, Any]] = []
    skipped: list[tuple[str, str]] = []
    for index, pdf_path in enumerate(sorted(course_dir.glob("*.pdf")), start=1):
        title = pdf_path.stem
        try:
            doc = pymupdf.open(pdf_path)
            raw = "\n".join(page.get_text() for page in doc)
            doc.close()
        except Exception as exc:  # noqa: BLE001 — one bad PDF must not kill the batch
            skipped.append((pdf_path.name, f"open/extract failed: {exc}"))
            continue
        cleaned = clean_text(raw)
        if len(cleaned) < MIN_EXTRACTED_CHARS:
            skipped.append((pdf_path.name, f"only {len(cleaned)} usable chars extracted"))
            continue
        slot = _slot_number_for(pdf_path.name, index)
        source_label = f"subject_data · Slot {slot:02d} · {code} · {title}"
        rel_path = str(pdf_path.relative_to(ROOT)).replace("\\", "/")
        for chunk in chunk_text(cleaned):
            entries.append(
                {
                    "chunk_id": f"sd_{code.lower()}_{uuid.uuid4().hex[:10]}",
                    "subject_code": code,
                    "section": title,
                    "text": chunk,
                    "source_label": source_label,
                    "document_title": title,
                    "document_file_path": rel_path,
                    "document_id": f"doc_subjdata_{_slugify(code)}_{_slugify(title)}",
                }
            )
    return entries, skipped


def write_chunks_json(code: str, name: str, entries: list[dict[str, Any]]) -> Path:
    path = CHUNKS_DIR / f"chunks_{code}.json"
    payload = {
        "subject_code": code,
        "subject_name": name,
        "chunks": [
            {
                "chunk_id": e["chunk_id"],
                "subject_code": e["subject_code"],
                "section": e["section"],
                "text": e["text"],
                "source_label": e["source_label"],
            }
            for e in entries
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_db(code: str, name: str, entries: list[dict[str, Any]]) -> tuple[int, int]:
    from src.db import models
    from src.db.connection import SessionLocal

    db = SessionLocal()
    documents_written = 0
    chunks_written = 0
    try:
        course = db.query(models.Course).filter_by(code=code).first()
        if course is None:
            course = models.Course(id=code, code=code, name=name, description=name)
            db.add(course)
            db.flush()
        else:
            course.name = name
            if not course.description:
                course.description = name

        by_document: dict[str, list[dict[str, Any]]] = {}
        for entry in entries:
            by_document.setdefault(entry["document_id"], []).append(entry)

        for document_id, doc_entries in by_document.items():
            title = doc_entries[0]["document_title"]
            file_path = doc_entries[0]["document_file_path"]
            document = db.query(models.Document).filter_by(id=document_id).first()
            if document is None:
                document = models.Document(
                    id=document_id,
                    course_id=course.id,
                    title=title,
                    file_path=file_path,
                    doc_type="LECTURE",
                    version="1.0",
                    metadata_info={"source": SOURCE_TAG, "course_code": code},
                )
                db.add(document)
                db.flush()
            else:
                document.title = title
                document.file_path = file_path
                meta = dict(document.metadata_info or {})
                meta["source"] = SOURCE_TAG
                meta["course_code"] = code
                document.metadata_info = meta
            documents_written += 1

            db.query(models.DocumentChunk).filter_by(document_id=document.id).delete(
                synchronize_session=False
            )
            for index, entry in enumerate(doc_entries):
                db.add(
                    models.DocumentChunk(
                        id=f"chunk_{document.id}_{index}",
                        document_id=document.id,
                        chunk_index=index,
                        text=entry["text"],
                        token_count=max(1, len(entry["text"].split())),
                        metadata_info={
                            "course_code": code,
                            "doc_type": "LECTURE",
                            "doc_title": title,
                            "section": entry["section"],
                            "source_label": entry["source_label"],
                            "source": SOURCE_TAG,
                        },
                    )
                )
                chunks_written += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return documents_written, chunks_written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--courses", help="Comma-separated course codes to limit to (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Extract/report only, write nothing")
    args = parser.parse_args()

    if not SUBJECT_DATA_DIR.is_dir():
        raise SystemExit(f"Not found: {SUBJECT_DATA_DIR}")

    official_names = load_official_names()
    course_dirs = sorted(p for p in SUBJECT_DATA_DIR.iterdir() if p.is_dir())
    wanted = {c.strip().upper() for c in args.courses.split(",")} if args.courses else None

    total_courses = 0
    total_documents = 0
    total_chunks = 0
    all_skipped: list[tuple[str, str, str]] = []

    for course_dir in course_dirs:
        code = course_dir.name.upper()
        if wanted and code not in wanted:
            continue
        name = course_name_for(code, official_names)
        entries, skipped = extract_course_pdfs(code, course_dir)
        for filename, reason in skipped:
            all_skipped.append((code, filename, reason))
        if not entries:
            logger.warning("course=%s -> 0 usable chunks, skipping DB/JSON write", code)
            continue

        if not args.dry_run:
            write_chunks_json(code, name, entries)
            documents_written, chunks_written = write_db(code, name, entries)
        else:
            documents_written = len({e["document_id"] for e in entries})
            chunks_written = len(entries)

        total_courses += 1
        total_documents += documents_written
        total_chunks += chunks_written
        logger.info(
            "course=%s name=%r documents=%s chunks=%s skipped=%s",
            code, name, documents_written, chunks_written, len(skipped),
        )

    logger.info("=" * 60)
    logger.info(
        "DONE courses=%s documents=%s chunks=%s skipped_files=%s%s",
        total_courses, total_documents, total_chunks, len(all_skipped),
        " (dry-run, nothing written)" if args.dry_run else "",
    )
    if all_skipped:
        logger.info("Skipped files:")
        for code, filename, reason in all_skipped:
            logger.info("  %s/%s: %s", code, filename, reason)


if __name__ == "__main__":
    main()
