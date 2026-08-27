"""Seed BIT_SE catalog chunks and database from the official 48-course JSON.

Reads (never overwrites if already valid):
  docs/planning/v2/data/courses_BIT_SE_K20D_K21A.json
  docs/planning/v2/data/seed_students_SSA101.json
  docs/planning/v2/data/chunks_*.json  (keeps rich files such as FLM SSA101)

Writes missing/stub `chunks_<CODE>.json`, then upserts `courses`, `documents`,
and `document_chunks` (source=mock) for Admin F6 / RAG.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.mock.demo_data import CURRICULUM_FILE, DATA_DIR  # noqa: E402

logger = logging.getLogger("seed-curriculum")

STUB_MARKERS = ("Synthetic QA helper resource",)
MIN_RICH_CHUNKS = 5
MIN_RICH_CHARS = 800


def _catalog_path() -> Path:
    return DATA_DIR / CURRICULUM_FILE


def load_catalog() -> dict[str, Any]:
    path = _catalog_path()
    if not path.is_file():
        raise FileNotFoundError(f"Curriculum catalog missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    subjects = payload.get("subjects") if isinstance(payload, dict) else None
    count = payload.get("subject_count") if isinstance(payload, dict) else None
    if not isinstance(subjects, list) or count != 48 or len(subjects) != 48:
        raise ValueError(f"Curriculum catalog must contain 48 subjects: {path}")
    for subject in subjects:
        if not isinstance(subject, dict):
            raise ValueError("Curriculum subject is invalid")
        code = str(subject.get("Subject Code") or "").strip()
        name = str(subject.get("Subject Name") or "").strip()
        semester = str(subject.get("Semester") or "").strip()
        if not code or not name or not semester:
            raise ValueError(f"Curriculum subject fields are incomplete: {subject}")
    return payload


def _chunk_filename(code: str) -> str:
    return f"chunks_{code.replace('*', 'x')}.json"


def _prereq(subject: dict[str, Any]) -> str | None:
    raw = subject.get("PreRequisite")
    if raw is None:
        raw = subject.get("Pre-Requisite")
    text = str(raw).strip() if raw is not None else ""
    if text in {"", "None", "null"}:
        return None
    return text


def _credits(subject: dict[str, Any]) -> str:
    return str(subject.get("NoCredit") or "").strip() or "0"


def _description(subject: dict[str, Any]) -> str:
    text = str(subject.get("Description") or "").strip()
    if text:
        return text
    return str(subject["Subject Name"]).strip()


def _slug(code: str) -> str:
    return code.lower().replace("*", "x")


def _paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()][:80]


def _heading(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def _is_stub_text(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 80:
        return True
    return any(marker in stripped for marker in STUB_MARKERS)


def _is_rich_chunk_file(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    chunks = payload.get("chunks") if isinstance(payload, dict) else None
    if not isinstance(chunks, list) or not chunks:
        return False
    if len(chunks) >= MIN_RICH_CHUNKS:
        return True
    total = sum(len(str(item.get("text") or "")) for item in chunks if isinstance(item, dict))
    return total >= MIN_RICH_CHARS


def _markdown_docs(code: str) -> list[dict[str, str]]:
    docs_root = ROOT / "mock_data" / "documents" / code
    found: list[dict[str, str]] = []
    if not docs_root.is_dir():
        return found
    for path in sorted(docs_root.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if _is_stub_text(text):
            continue
        stem = path.stem.lower()
        if "faq" in stem:
            doc_type = "FAQ"
        elif "lab" in stem:
            doc_type = "LAB"
        elif "lecture" in stem:
            doc_type = "LECTURE"
        else:
            doc_type = "SYLLABUS"
        found.append(
            {
                "filename": path.name,
                "title": f"{code} {path.stem}",
                "doc_type": doc_type,
                "text": text,
            }
        )
    return found


def _bundled_docs(code: str) -> list[dict[str, str]]:
    from src.services.student_mock_data_service import COURSE_DOCUMENTS

    bundled = COURSE_DOCUMENTS.get(code)
    if not bundled:
        return []
    return [
        {
            "filename": item["filename"],
            "title": item["title"],
            "doc_type": item["doc_type"],
            "text": item["text"],
        }
        for item in bundled
    ]


def _config_docs(code: str, name: str) -> list[dict[str, str]]:
    from mock_data.config import COURSES_CONFIG

    cfg = COURSES_CONFIG.get(code)
    if not cfg:
        return []
    topics = "\n".join(
        f"{index}. {topic}" for index, topic in enumerate(cfg.get("topics") or [], start=1)
    )
    assessment = cfg.get("assessment_structure") or {}
    weights = ", ".join(
        f"{key.replace('_', ' ')} {int(value * 100)}%"
        for key, value in assessment.items()
        if isinstance(value, (int, float))
    )
    text = (
        f"# {code} — {cfg.get('name') or name}\n\n"
        f"Description: {cfg.get('description') or name}\n\n"
        f"Weekly outline:\n{topics}\n\n"
        f"Assessment (illustrative): {weights or 'See faculty syllabus'}.\n\n"
        "StudentTasks: Attend lectures/labs, complete assignments on time, "
        "and do not submit AI-generated graded work as your own.\n\n"
        "Conditions to pass: Final exam ≥ 4/10 and overall average ≥ 5/10; "
        "attendance according to faculty rules.\n"
    )
    return [
        {
            "filename": "syllabus.md",
            "title": f"{code} Syllabus — {cfg.get('name') or name}",
            "doc_type": "SYLLABUS",
            "text": text,
        }
    ]


def _synthetic_docs(subject: dict[str, Any]) -> list[dict[str, str]]:
    code = str(subject["Subject Code"]).strip()
    name = str(subject["Subject Name"]).strip()
    semester = str(subject.get("Semester") or "").strip()
    credits = _credits(subject)
    prereq = _prereq(subject) or "None"
    description = _description(subject)
    text = (
        f"# {code} — {name}\n\n"
        f"Description: {description}\n\n"
        f"NoCredit: {credits}\n"
        f"Pre-Requisite: {prereq}\n"
        f"Semester: {semester}\n"
        "Time Allocation: 30h lecture + 60h self-study (typical FLM pattern).\n\n"
        "StudentTasks: Attend lectures/labs, complete assignments on time, "
        "keep a weekly study log, and do not submit AI-generated graded work as your own.\n\n"
        "Conditions to pass: Final exam ≥ 4/10 and overall average ≥ 5/10; "
        "attendance according to faculty rules.\n\n"
        "Progress marks: Participation 10%; Assignments/Labs 30%; "
        "Progress test 20%; Final 40% (illustrative weights for grounded Q&A).\n\n"
        f"Overview: {name} ({code}) is part of BIT_SE_K20D_K21A. "
        "Cursus answers must stay inside this syllabus and cite the section used.\n"
    )
    return [
        {
            "filename": "syllabus.md",
            "title": f"{code} Syllabus — {name}",
            "doc_type": "SYLLABUS",
            "text": text,
        }
    ]


def _documents_for(subject: dict[str, Any]) -> list[dict[str, str]]:
    code = str(subject["Subject Code"]).strip()
    name = str(subject["Subject Name"]).strip()
    bundled = _bundled_docs(code)
    if bundled:
        return bundled
    config_docs = _config_docs(code, name)
    markdown_docs = _markdown_docs(code)
    if config_docs:
        return config_docs + markdown_docs
    if markdown_docs:
        return markdown_docs
    return _synthetic_docs(subject)


def _chunks_from_docs(subject: dict[str, Any], docs: list[dict[str, str]]) -> list[dict[str, str]]:
    code = str(subject["Subject Code"]).strip()
    name = str(subject["Subject Name"]).strip()
    chunks: list[dict[str, str]] = []
    chunk_index = 0
    for doc in docs:
        for paragraph in _paragraphs(doc["text"]):
            chunk_index += 1
            section = _heading(paragraph) or doc["title"]
            chunks.append(
                {
                    "chunk_id": f"{code}-{doc['filename']}-{chunk_index}",
                    "subject_code": code,
                    "subject_name": name,
                    "section": section,
                    "text": paragraph,
                    "source_label": f"{doc['title']} — {section}",
                }
            )
    return chunks


def ensure_chunk_files(catalog: dict[str, Any]) -> tuple[int, int]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    kept = 0
    allowed = {_chunk_filename(str(row["Subject Code"]).strip()) for row in catalog["subjects"]}
    for path in DATA_DIR.glob("chunks_*.json"):
        if path.name not in allowed:
            path.unlink()
            logger.info("removed_orphan_chunk_file name=%s", path.name)
    for subject in catalog["subjects"]:
        code = str(subject["Subject Code"]).strip()
        path = DATA_DIR / _chunk_filename(code)
        if _is_rich_chunk_file(path):
            kept += 1
            continue
        chunks = _chunks_from_docs(subject, _documents_for(subject))
        payload = {
            "subject_code": code,
            "subject_name": subject["Subject Name"],
            "chunks": chunks,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written += 1
    logger.info("chunk_files kept=%s written=%s", kept, written)
    return kept, written


def _load_chunk_file(code: str) -> list[dict[str, Any]]:
    path = DATA_DIR / _chunk_filename(code)
    payload = json.loads(path.read_text(encoding="utf-8"))
    chunks = payload.get("chunks") if isinstance(payload, dict) else None
    if not isinstance(chunks, list):
        return []
    return [item for item in chunks if isinstance(item, dict) and str(item.get("text") or "").strip()]


def seed_database(catalog: dict[str, Any]) -> dict[str, int]:
    from src.db.connection import SessionLocal
    from src.db.models import Course, Document, DocumentChunk, Organization

    db = SessionLocal()
    created_courses = 0
    updated_courses = 0
    documents = 0
    chunks = 0
    try:
        organization = db.query(Organization).filter_by(slug="cursus-demo").first()
        if organization is None:
            raise RuntimeError(
                "The cursus-demo organization must be provisioned before curriculum seeding"
            )
        for subject in catalog["subjects"]:
            code = str(subject["Subject Code"]).strip()
            name = str(subject["Subject Name"]).strip()
            description = _description(subject)
            course = db.query(Course).filter_by(code=code).first()
            syllabus_chunks = _load_chunk_file(code)
            syllabus = "\n\n".join(str(item.get("text") or "") for item in syllabus_chunks[:8])
            if course is None:
                db.add(
                    Course(
                        id=code,
                        code=code,
                        name=name,
                        description=description,
                        syllabus=syllabus or None,
                        organization_id=organization.id,
                    )
                )
                created_courses += 1
            else:
                course.name = name
                course.description = description
                if syllabus:
                    course.syllabus = syllabus
                updated_courses += 1
        db.flush()

        for subject in catalog["subjects"]:
            code = str(subject["Subject Code"]).strip()
            slug = _slug(code)
            course = db.query(Course).filter_by(code=code).one()
            records = _load_chunk_file(code)
            document_id = f"doc_catalog_{slug}_chunks"
            old_docs = (
                db.query(Document)
                .filter(Document.id.like(f"doc_catalog_{slug}_%"))
                .all()
            )
            for old in old_docs:
                (
                    db.query(DocumentChunk)
                    .filter_by(document_id=old.id)
                    .delete(synchronize_session=False)
                )
                if old.id != document_id:
                    db.delete(old)
            db.flush()

            document = db.query(Document).filter_by(id=document_id).first()
            title = f"{code} curriculum chunks"
            file_path = f"docs/planning/v2/data/{_chunk_filename(code)}"
            if document is None:
                document = Document(
                    id=document_id,
                    course_id=course.id,
                    title=title,
                    file_path=file_path,
                    doc_type="SYLLABUS",
                    version="1.0",
                    metadata_info={"source": "mock", "course_code": code},
                )
                db.add(document)
                db.flush()
            else:
                document.title = title
                document.file_path = file_path
                document.doc_type = "SYLLABUS"
                meta = dict(document.metadata_info or {})
                meta["source"] = "mock"
                meta["course_code"] = code
                document.metadata_info = meta
            documents += 1

            (
                db.query(DocumentChunk)
                .filter_by(document_id=document.id)
                .delete(synchronize_session=False)
            )
            db.flush()
            for index, item in enumerate(records):
                text = str(item.get("text") or "").strip()
                section = str(item.get("section") or "") or None
                source_label = str(item.get("source_label") or title)
                db.add(
                    DocumentChunk(
                        id=f"chunk_catalog_{document.id}_{index}",
                        document_id=document.id,
                        chunk_index=index,
                        text=text,
                        token_count=max(1, len(text.split())),
                        metadata_info={
                            "course_code": code,
                            "doc_type": "SYLLABUS",
                            "doc_title": title,
                            "section": section,
                            "source_label": source_label,
                            "source": "mock",
                        },
                    )
                )
                chunks += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    logger.info(
        "seeded_curriculum created=%s updated=%s documents=%s chunks=%s",
        created_courses,
        updated_courses,
        documents,
        chunks,
    )
    return {
        "created_courses": created_courses,
        "updated_courses": updated_courses,
        "documents": documents,
        "chunks": chunks,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Seed BIT_SE curriculum catalog and chunks")
    parser.add_argument(
        "--files-only",
        action="store_true",
        help="Write missing JSON chunks only; do not touch the database",
    )
    args = parser.parse_args()
    catalog = load_catalog()
    kept, written = ensure_chunk_files(catalog)
    print(f"catalog subjects=48 chunk_files kept={kept} written={written}")
    if args.files_only:
        return 0
    stats = seed_database(catalog)
    print(
        "seeded courses created={created_courses} updated={updated_courses} "
        "documents={documents} chunks={chunks}".format(**stats)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
