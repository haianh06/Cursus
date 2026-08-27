"""Ingest real, parsed curriculum syllabi as official_document content.

Phase 2 (21/08): extends the "1 course at a time" pattern used by
`gate2_demo` (SSA101) and `student_mock_data_service._ensure_real_content`
(CSI106) to every course that has a clean parsed chunk file AND an
unambiguous 1:1 catalog match — see `docs/planning/v2/scripts/
parse_all_courses.py`'s module docstring for why 8 of the 44 available
files (elective/combo-slot examples like `PHE_COM_1.docx` -> COV111 "Chess
1") are deliberately excluded here rather than aliased onto a combo
placeholder catalog code.

This is a general curriculum loader, independent of any student's mock
semester — it creates/updates `Course` rows directly from the catalog and
does not touch enrollment, so it is safe to run against courses no demo
student is enrolled in (visible in Admin Console regardless).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import NamedTuple

from sqlalchemy.orm import Session

from src.db import models
from src.services.mock.gate2_demo import ingest_official_chunks, load_official_chunks

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[4]
CATALOG_PATH = ROOT / "docs" / "planning" / "v2" / "data" / "courses_BIT_SE_K20D_K21A.json"
CHUNKS_DIR = ROOT / "docs" / "planning" / "v2" / "data"

# Never ingested through this generic loader — SSA101 has its own richer
# gate2_demo fixture (timetable/assignments tied to it), CSI106 was already
# wired via student_mock_data_service.REAL_CONTENT_COURSES earlier this
# session. Re-ingesting them here would just be a slower no-op duplicate of
# an already-correct path.
_EXCLUDED_CODES = frozenset({"SSA101", "CSI106"})


class RealCourseSpec(NamedTuple):
    code: str
    name: str
    semester: str


def _load_valid_syllabus_payload(path: Path) -> dict | None:
    """Return a payload only when it matches the parsed-syllabus contract.

    Planning summaries can also use the ``chunks_<CODE>.json`` naming
    convention. A filename alone is therefore not enough evidence that a
    document is an official parsed syllabus. Real payloads must carry
    structured metadata and at least one non-empty session chunk.
    """
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("real_curriculum: invalid syllabus JSON at %s", path)
        return None
    if not isinstance(payload, dict):
        return None
    meta = payload.get("meta")
    chunks = payload.get("chunks")
    if not isinstance(meta, dict) or not meta or not isinstance(chunks, list):
        return None
    has_session = any(
        isinstance(chunk, dict)
        and str(chunk.get("section") or "").startswith("Session ")
        and bool(str(chunk.get("text") or "").strip())
        for chunk in chunks
    )
    return payload if has_session else None


def _load_catalog_specs() -> dict[str, RealCourseSpec]:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    specs: dict[str, RealCourseSpec] = {}
    for subject in catalog["subjects"]:
        code = str(subject.get("Subject Code") or "").strip()
        name = str(subject.get("Subject Name") or "").strip()
        semester = str(subject.get("Semester") or "").strip()
        if code and name:
            specs[code] = RealCourseSpec(code=code, name=name, semester=semester)
    return specs


def discover_real_course_codes() -> list[str]:
    """Catalog codes (exact string, `*` included) with BOTH a parsed chunk
    file and an unambiguous 1:1 match — i.e. `chunks_<CODE>.json` exists
    under the code's own catalog identity, not a combo placeholder alias."""
    specs = _load_catalog_specs()
    codes = []
    for code in specs:
        if code in _EXCLUDED_CODES:
            continue
        if _load_valid_syllabus_payload(CHUNKS_DIR / f"chunks_{code}.json") is not None:
            codes.append(code)
    return sorted(codes)


def _sandbox_organization_id(db: Session) -> str | None:
    """`courses.organization_id` is NOT NULL on the real migration chain
    (nullable only at the Python/model level — see the comment on
    `Course.organization_id`). Curriculum content is org-agnostic in
    principle, but the schema forces a tenant, so anchor every course
    created by this loader to the same `cursus-demo` sandbox org every other
    demo/mock Course row already uses (SSA101/PRF192/CEA201/CSI106) rather
    than inventing a second convention."""
    org = db.query(models.Organization).filter_by(slug="cursus-demo").first()
    if org:
        return org.id
    org = db.query(models.Organization).first()
    return org.id if org else None


def ensure_course_row(db: Session, spec: RealCourseSpec) -> models.Course:
    course = db.query(models.Course).filter_by(code=spec.code).first()
    if course:
        course.name = spec.name
        return course
    course = models.Course(
        id=f"course_real_{spec.code.lower().replace('*', '_')}",
        code=spec.code,
        name=spec.name,
        description=spec.name,
        organization_id=_sandbox_organization_id(db),
    )
    db.add(course)
    db.flush()
    return course


def ingest_real_course(db: Session, code: str) -> int:
    """Ensure the Course row exists and its official chunks are ingested.
    Returns the number of chunks written (0 if the code has no catalog
    entry or no parsed chunk file — never raises for a missing course, same
    contract as `load_official_chunks`)."""
    specs = _load_catalog_specs()
    spec = specs.get(code)
    if spec is None:
        logger.warning("real_curriculum: %s is not a catalog subject code", code)
        return 0

    payload_path = CHUNKS_DIR / f"chunks_{code}.json"
    payload = _load_valid_syllabus_payload(payload_path)
    if payload is None:
        logger.warning("real_curriculum: %s has no valid parsed syllabus", code)
        return 0

    course = ensure_course_row(db, spec)
    chunks = load_official_chunks(code, fallback_title=spec.name)
    if not chunks:
        return 0

    meta = payload["meta"]
    syllabus_id = str(meta.get("Syllabus ID") or "").strip()
    approved = str(meta.get("ApprovedDate") or "").strip()
    version = f"{syllabus_id}-{approved}" if syllabus_id else "unknown"

    document_id = f"doc_real_{code.lower().replace('*', '_')}_syllabus"
    count = ingest_official_chunks(
        db,
        course=course,
        subject_code=code,
        document_id=document_id,
        title=f"Syllabus {code} — {spec.name}",
        version=version,
        chunks=chunks,
    )
    return count


def _parse_session_text(section: str, text: str) -> dict[str, str | None]:
    """`chunks_<CODE>.json` session chunks are one prose blob per session:
    ``"Session {N} — {topic}\nTài liệu: {materials}\nNhiệm vụ sinh viên: {task}"``.
    Confirmed consistent ordering (topic, then Tài liệu, then Nhiệm vụ sinh
    viên) across a full scan of all 44 files (docs/EVALUATION_2_KETLUAN.md
    research, 22/08) — exam/review sessions legitimately omit the trailing
    labels (91%/84% of 1937 sessions have them), never reorder them, so a
    plain partition on the known labels is enough; no regex needed."""
    marker = f"{section} — "
    body = text[len(marker) :] if text.startswith(marker) else text
    task = None
    if "\nNhiệm vụ sinh viên:" in body:
        body, _, task_part = body.partition("\nNhiệm vụ sinh viên:")
        task = task_part.strip() or None
    materials = None
    if "\nTài liệu:" in body:
        body, _, materials_part = body.partition("\nTài liệu:")
        materials = materials_part.strip() or None
    return {"topic": body.strip(), "materials": materials, "task": task}


def get_curriculum_detail(code: str) -> dict | None:
    """Read a course's already-parsed syllabus straight from its
    ``chunks_<CODE>.json`` file — deliberately NOT from the DB, so Admin
    Console can show a course's real CLO/session content regardless of
    whether `ingest_real_course` has run for it yet (ingestion and
    "has parseable content" are separate questions). Returns None if no
    chunk file exists for this code (e.g. a course added manually through
    the Admin "add course" form, with no real syllabus behind it).

    Field-by-field verified present before this was written (not assumed):
    `meta` is a flat, structured dict on every one of the 44 files (course
    name/credits/time allocation/description/prerequisite/tools/scoring
    scale/grading-policy Note/pass mark/decision no/approved date); every
    CLO chunk is a clean single-line "CLOn: <description>"; `clo_count`/
    `session_count` match the actual chunk counts on all 44 files with zero
    mismatches. There is NO per-session "LO" field anywhere in this data
    (only course-level CLOs) and no structured per-line assessment-weight
    table (when grading weights exist at all, e.g. SSA101, they're free
    text inside `meta.Note`, not separate rows) — neither is fabricated
    here; `Note` is returned as-is under its own key, and no LO column
    exists in the returned session shape.
    """
    payload = _load_valid_syllabus_payload(CHUNKS_DIR / f"chunks_{code}.json")
    if payload is None:
        return None
    chunks = payload.get("chunks") or []
    clos: list[dict] = []
    sessions: list[dict] = []
    for chunk in chunks:
        section = str(chunk.get("section") or "")
        text = str(chunk.get("text") or "").strip()
        if not section or not text:
            continue
        if section.startswith("Learning Outcome CLO"):
            clo_code, _, description = text.partition(":")
            clos.append({"code": clo_code.strip(), "text": description.strip() or text})
        elif section.startswith("Session "):
            number_str = section.removeprefix("Session ").strip()
            sessions.append(
                {
                    "number": int(number_str) if number_str.isdigit() else None,
                    **_parse_session_text(section, text),
                }
            )
    sessions.sort(key=lambda s: (s["number"] is None, s["number"]))
    return {
        "meta": payload.get("meta") or {},
        "clo_count": payload.get("clo_count", len(clos)),
        "session_count": payload.get("session_count", len(sessions)),
        "clos": clos,
        "sessions": sessions,
    }


def purge_superseded_mock_catalog_docs(db: Session) -> list[str]:
    """Delete the old generic-loader `doc_catalog_<code>_chunks` Document
    (source="mock") for any course that now ALSO has a real, official
    Document (this loader's own `doc_real_*`, or gate2_demo/
    student_mock_data_service's SSA101/CSI106 fixtures) -- these were
    written before `docker_entrypoint.py` was fixed to only run
    `seed_curriculum.py --files-only`, and being a straight duplicate under
    a different document_id, they sit alongside the real content in
    retrieval forever unless removed: the RAG blended score can still pick
    the mock chunk as top match, which both mislabels a real citation as
    simulated (MOCK_CONTENT_DISCLAIMER) and surfaces raw, unedited chunk
    text instead of the real document's citation. A course whose only
    content is this mock doc (no real replacement exists, e.g. combo-slot
    codes like PHE_COM*1) is left untouched -- it's the only source
    available for that course, disclaimer included.

    DocumentChunk rows cascade via ondelete=CASCADE on document_id, so
    deleting the Document is enough. Safe to call on every boot: a no-op
    once the superseded docs are gone."""
    docs = db.query(models.Document).all()
    real_codes = {
        meta["course_code"]
        for meta in (d.metadata_info or {} for d in docs)
        if meta.get("source") != "mock" and meta.get("course_code")
    }
    superseded = [
        d
        for d in docs
        if (d.metadata_info or {}).get("source") == "mock"
        and (d.metadata_info or {}).get("course_code") in real_codes
    ]
    for doc in superseded:
        db.delete(doc)
    db.commit()
    return [d.id for d in superseded]


def ingest_all_real_courses(db: Session) -> dict[str, int]:
    """Ingest every discoverable real course. Commits once at the end so a
    partial failure doesn't leave some courses half-migrated mid-batch."""
    results: dict[str, int] = {}
    for code in discover_real_course_codes():
        results[code] = ingest_real_course(db, code)
    db.commit()
    return results
