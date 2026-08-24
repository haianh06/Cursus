"""Batch-parse every .docx in data/clean/courses/ into chunks_<CODE>.json.

Phase 2 (21/08) fix: the earlier plan assumed the only problem was a
`*` (catalog placeholder, e.g. "PHE_COM*1") vs `_` (filename, "PHE_COM_1.docx")
naming mismatch. Cross-checking every file's OWN embedded "Subject Code"
table field against the 48-row catalog revealed a second, more important
issue: 8 of the 44 files are elective/combo-slot examples whose embedded
code does not match any catalog row at all (e.g. `PHE_COM_1.docx` embeds
`COV111` / "Cờ Vua 1 - Chess 1", one specific PE elective — not a fixed
"PHE_COM*1" syllabus, which could equally be badminton/swimming/etc for a
different student's combo pick). Forcing that one arbitrary elective's
content onto the combo placeholder row would misrepresent it as the fixed
syllabus for that slot — the same class of data-integrity problem fixed in
Phase 1 for CEA201's mock content. So: identity is taken from the file's own
embedded Subject Code (source of truth), NEVER guessed from the filename.
A file whose embedded code isn't one of the 48 catalog rows is still parsed
(the content is real) but flagged `catalog_row: null` so the ingest step can
decide not to alias it onto a combo placeholder.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flm_parser import parse_syllabus  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
CLEAN_DIR = ROOT / "data" / "clean" / "courses"
DATA_DIR = ROOT / "docs" / "planning" / "v2" / "data"
CATALOG_PATH = DATA_DIR / "courses_BIT_SE_K20D_K21A.json"

# Already ingested through a different pathway before this script existed —
# never overwritten by a batch run (SSA101 = gate2_demo fixture chunks,
# CSI106 = first Phase-2-style real ingest done earlier this session).
SKIP_CODES = {"SSA101", "CSI106"}


def _iter_source_files():
    for entry in sorted(CLEAN_DIR.iterdir()):
        if entry.is_dir():
            inner = sorted(p for p in entry.iterdir() if p.suffix.lower() == ".docx")
            if inner:
                yield entry.name, inner[0]
        elif entry.suffix.lower() == ".docx":
            yield entry.stem, entry


def main() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    catalog_codes = {s.get("Subject Code", "").strip() for s in catalog["subjects"]}

    report = {"direct": [], "elective_example": [], "errors": [], "skipped": []}

    for file_stem, path in _iter_source_files():
        try:
            parsed = parse_syllabus(str(path))
        except Exception as exc:  # noqa: BLE001 - report and continue the batch
            report["errors"].append({"file": file_stem, "error": str(exc)})
            continue

        code = parsed["subject_code"].strip()
        if not code or code == "UNKNOWN":
            report["errors"].append({"file": file_stem, "error": "no Subject Code found in file"})
            continue

        if code in SKIP_CODES:
            report["skipped"].append(code)
            continue

        in_catalog = code in catalog_codes
        out_path = DATA_DIR / f"chunks_{code}.json"
        out_path.write_text(
            json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        entry = {
            "file": file_stem,
            "code": code,
            "name": parsed["subject_name"],
            "chunks": len(parsed["chunks"]),
            "sessions": parsed["session_count"],
            "clos": parsed["clo_count"],
        }
        if in_catalog:
            report["direct"].append(entry)
        else:
            report["elective_example"].append(entry)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(
        f"\ndirect={len(report['direct'])} "
        f"elective_example={len(report['elective_example'])} "
        f"errors={len(report['errors'])} "
        f"skipped={len(report['skipped'])}"
    )


if __name__ == "__main__":
    main()
