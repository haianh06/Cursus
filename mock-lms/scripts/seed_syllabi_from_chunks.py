"""Ingest the real, parsed syllabus content from `docs/planning/v2/data/
chunks_<CODE>.json` into Mock LMS's own `Syllabus` table, for every course
that has one -- not just CSI106 and SWE202c (see seed_curriculum.py).

Those chunk files are the RAG-ingestion output of every `.docx` under
`data/clean/courses/` (see `docs/planning/v2/scripts/parse_all_courses.py`),
already used by Cursus's own mock data services
(`src/services/mock/real_curriculum_service.py`). Mock LMS never read them --
this script is the missing ingestion step, turning the syllabus-detail flow
from 2/44 real courses into however many chunk files actually exist.

Each chunk file's `meta` dict already carries the same field names the
Syllabus model expects (NoCredit, Learning-Teaching Method, Pre-Requisite,
etc.) -- lifted straight out, no re-authoring. `clos` and `sessions` are
reconstructed by parsing the "Learning Outcome CLOn" and "Session n" chunks'
`text` field (see `_parse_sessions`/`_parse_clos` below for the exact shape
observed across sampled files).

Honest limitation: this parsed corpus has no materials/questions/assessments
structure (only overview/CLO/session-plan chunks were extracted from the
source docx) -- rows seeded here get real CLOs and a real session plan, but
empty `materials`/`questions`/`assessments` arrays, same as this model's own
defaults. CSI106 and SWE202c's own hand-authored rows (seed_curriculum.py,
which HAS that detail) are left untouched by this script -- see `main()`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db import Base, ENGINE, SessionLocal  # noqa: E402
from app.models import Syllabus  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_DIR = REPO_ROOT / "docs" / "planning" / "v2" / "data"

# These two already have a much richer hand-authored row from
# seed_curriculum.py (full materials/questions/assessments) -- overwriting
# them with the thinner auto-parsed version would be a regression, not an
# improvement.
SKIP_CODES = {"CSI106", "SWE202c"}

_SESSION_HEADER_RE = re.compile(r"^Session\s+(\d+)\s*—\s*(.*)", re.DOTALL)
_MATERIALS_RE = re.compile(r"Tài liệu:\s*(.*?)(?:\n|$)")
_TASKS_RE = re.compile(r"Nhiệm vụ sinh viên:\s*(.*)", re.DOTALL)
_CLO_RE = re.compile(r"^(CLO\d+):\s*(.*)", re.DOTALL)


def _parse_clo(text: str) -> tuple[str, str] | None:
    m = _CLO_RE.match(text.strip())
    if not m:
        return None
    return m.group(1), m.group(2).strip()


def _parse_session(text: str) -> dict | None:
    m = _SESSION_HEADER_RE.match(text.strip())
    if not m:
        return None
    session_no = int(m.group(1))
    body = m.group(2)

    materials_m = _MATERIALS_RE.search(body)
    tasks_m = _TASKS_RE.search(body)

    # Topic is everything before the "Tài liệu:" line (or the whole body if
    # that line is missing) -- multi-line topics (sub-points like "1.1 ...\n
    # 1.2 ...") are joined into one readable line rather than truncated to
    # just the first line, since the sub-points are real session content.
    topic_end = materials_m.start() if materials_m else (tasks_m.start() if tasks_m else len(body))
    topic = " / ".join(line.strip() for line in body[:topic_end].strip().splitlines() if line.strip())

    return {
        "sessionNo": session_no,
        "topic": topic,
        "studentMaterials": materials_m.group(1).strip() if materials_m else "",
        "studentTasks": tasks_m.group(1).strip() if tasks_m else "",
    }


def _bool(meta: dict, key: str, default: bool = True) -> bool:
    return str(meta.get(key, default)).strip().lower() == "true"


def _int(meta: dict, key: str, default: int = 0) -> int:
    try:
        return int(str(meta.get(key, default)).strip())
    except ValueError:
        return default


def _build_syllabus(chunk_doc: dict) -> dict | None:
    meta = chunk_doc.get("meta", {})
    code = chunk_doc["subject_code"]

    clos: list[dict] = []
    sessions: list[dict] = []
    for chunk in chunk_doc.get("chunks", []):
        section = chunk.get("section", "")
        text = chunk.get("text", "")
        if section.startswith("Learning Outcome"):
            parsed = _parse_clo(text)
            if parsed:
                clos.append({"no": len(clos) + 1, "cloName": parsed[0], "details": parsed[1]})
        elif section.startswith("Session "):
            parsed = _parse_session(text)
            if parsed:
                sessions.append(parsed)

    if not clos and not sessions:
        # Overview-only chunk file (no CLO/session content survived parsing)
        # -- not worth a near-empty Syllabus row.
        return None

    sessions.sort(key=lambda s: s["sessionNo"])

    return {
        "subject_code": code,
        "syllabus_id": _int(meta, "Syllabus ID"),
        "syllabus_name": meta.get("Syllabus Name") or chunk_doc.get("subject_name", code),
        "course_name_english": meta.get("Course Name English", ""),
        "learning_teaching_method": meta.get("Learning-Teaching Method", ""),
        "no_credit": _int(meta, "NoCredit", 3),
        "degree_level": meta.get("Degree Level", "Bachelor"),
        "time_allocation": meta.get("Time Allocation", ""),
        "pre_requisite": meta.get("Pre-Requisite", "") or "None",
        "description": meta.get("Description", ""),
        "student_tasks": meta.get("StudentTasks", ""),
        "tools": meta.get("Tools", ""),
        "scoring_scale": _int(meta, "Scoring Scale", 10),
        "decision_no": meta.get("DecisionNo MM/dd/yyyy", ""),
        "approved_date": meta.get("ApprovedDate", ""),
        "is_active": _bool(meta, "IsActive"),
        "is_approved": _bool(meta, "IsApproved"),
        # Not present in this parsed corpus -- see module docstring.
        "materials": [],
        "questions": [],
        "assessments": [],
        "clos": clos,
        "sessions": sessions,
    }


def main() -> None:
    Base.metadata.create_all(bind=ENGINE)
    db = SessionLocal()
    seeded, skipped_existing, skipped_empty = [], [], []
    try:
        for chunk_path in sorted(CHUNKS_DIR.glob("chunks_*.json")):
            code = chunk_path.stem.removeprefix("chunks_")
            if code in SKIP_CODES:
                skipped_existing.append(code)
                continue

            chunk_doc = json.loads(chunk_path.read_text(encoding="utf-8"))
            data = _build_syllabus(chunk_doc)
            if data is None:
                skipped_empty.append(code)
                continue

            row = db.get(Syllabus, data["subject_code"])
            if row is None:
                row = Syllabus(subject_code=data["subject_code"])
                db.add(row)
            for key, value in data.items():
                setattr(row, key, value)
            seeded.append(code)

        db.commit()
    finally:
        db.close()

    print(f"Seeded {len(seeded)} syllabi from chunks: {', '.join(seeded)}")
    if skipped_existing:
        print(f"Skipped (already hand-authored, richer): {', '.join(skipped_existing)}")
    if skipped_empty:
        print(f"Skipped (no CLO/session content parsed): {', '.join(skipped_empty)}")


if __name__ == "__main__":
    main()
