"""Gate-2 evaluation harness (Data Contract §6).

Runs two suites and writes an honest report — failures included:

  guardrail  every case in ``datasets/guardrail_eval.jsonl`` against the real
             ``GuardrailService`` (DB-backed rule toggles, ADR-008 — runs
             against a throwaway in-memory SQLite session, still no network).
  rag        every case in ``datasets/rag_eval.jsonl`` against the real
             ``RetrievalService`` over the ingested SSA101 syllabus chunks,
             loaded into a throwaway in-memory SQLite database. Semantic
             embedding is attempted if a real GOOGLE_API_KEY is configured;
             on any failure it silently falls back to lexical-only scoring
             (see embedding_service.py) — the report below records whether
             the embedding backend actually answered a canary call this run,
             so a report generated on lexical-only fallback is never mistaken
             for one that used real embeddings.

Usage:
    python eval/run_eval.py                 # print summary
    python eval/run_eval.py --out eval/results/report.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATASETS = ROOT / "eval" / "datasets"


def _dataset_fingerprint(name: str) -> str:
    """Short hash of a dataset file's exact bytes — changes the moment a case
    is added/edited/removed, so a report can't silently be compared against
    a different dataset version without it showing up here."""
    path = DATASETS / name
    if not path.exists():
        return "missing"
    return hashlib.sha1(path.read_bytes()).hexdigest()[:12]


def _embedding_backend_reachable() -> bool:
    """Canary call, not a config check — has_embedding_backend() only means
    a key-shaped string is set, it does not mean the hardcoded model name
    (embedding_service.GEMINI_EMBED_MODEL) is still valid against the live
    API. A wrong model name fails closed (returns None, retrieval falls back
    to lexical) rather than crashing, so without this canary a report could
    look identical whether real embeddings ran or not."""
    from src.services.rag.embedding_service import embed_query, has_embedding_backend

    if not has_embedding_backend():
        return False
    return embed_query("eval harness reachability canary") is not None


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    expected: str
    actual: str
    detail: str = ""


def _load(name: str) -> list[dict]:
    path = DATASETS / name
    if not path.exists():
        raise SystemExit(f"Missing dataset: {path}")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ── guardrail ────────────────────────────────────────────────────────────
def run_guardrail() -> list[CaseResult]:
    import os

    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault(
        "JWT_SECRET_KEY", "eval-harness-secret-key-at-least-32-characters"
    )

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from src.db.models import Base
    from src.services.core.guardrail_service import (
        INTENT_BLOCKED,
        INTENT_HINT,
        INTENT_INJECTION,
        INTENT_OUT_OF_SCOPE,
        GuardrailService,
    )

    # GuardrailService is DB-backed (admin-toggleable rule groups, ADR-008) —
    # it no longer takes zero args. A throwaway in-memory session is enough:
    # GuardrailRuleRepository.enabled_codes() auto-seeds every rule group as
    # enabled on first read (see ensure_seeded()), which is exactly the
    # production default this harness is meant to measure against.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    service = GuardrailService(session)
    results: list[CaseResult] = []
    for case in _load("guardrail_eval.jsonl"):
        decision = service.evaluate(case["prompt"])
        if decision.intent == INTENT_BLOCKED:
            actual = "blocked_transform"
        elif decision.intent == INTENT_INJECTION:
            actual = "blocked_injection"
        elif decision.intent == INTENT_HINT:
            actual = "hint"
        elif decision.intent == INTENT_OUT_OF_SCOPE:
            actual = "out_of_scope"
        else:
            actual = "allowed"

        expected = case["expected"]
        # A blocked case must also carry redirect guidance, otherwise the
        # guardrail is a dead end and the case does not really pass.
        detail = ""
        passed = actual == expected
        if passed and expected == "blocked_transform":
            guidance = decision.guidance or {}
            if not (
                guidance.get("concept")
                and guidance.get("socraticQuestions")
                and guidance.get("template")
            ):
                passed = False
                detail = "blocked but missing concept/socratic/template redirect"
        results.append(
            CaseResult(case["id"], passed, expected, actual, detail or case.get("reason", ""))
        )
    session.close()
    return results


# ── rag / retrieval ──────────────────────────────────────────────────────
def run_rag() -> list[CaseResult]:
    import os

    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault(
        "JWT_SECRET_KEY", "eval-harness-secret-key-at-least-32-characters"
    )
    os.environ["DATABASE_URL"] = "sqlite://"

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from src.db.models import Base, Course, Document, DocumentChunk, DocType
    from src.repositories.chunk_repository import ChunkRepository
    from src.services.mock.gate2_demo import (
        SSA101_CODE,
        SSA101_DOC_ID,
        SSA101_DOC_TITLE,
        load_ssa101_chunks,
    )
    from src.services.rag.retrieval_service import RetrievalService

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    course = Course(
        id="course_eval_ssa101",
        code=SSA101_CODE,
        name="Kỹ năng học thuật",
        description="eval",
        syllabus="eval",
    )
    session.add(course)
    session.add(
        Document(
            id=SSA101_DOC_ID,
            course_id=course.id,
            title=SSA101_DOC_TITLE,
            file_path="docs/planning/v2/data/chunks_SSA101.json",
            doc_type=DocType.SYLLABUS.value,
            version="2025-11-27",
            metadata_info={"source": "curriculum"},
        )
    )
    chunks = load_ssa101_chunks()
    if not chunks:
        raise SystemExit("SSA101 chunk file not found — cannot run RAG eval.")
    for chunk in chunks:
        session.add(
            DocumentChunk(
                id=chunk["chunk_id"],
                document_id=SSA101_DOC_ID,
                chunk_index=chunk["chunk_index"],
                text=chunk["text"],
                token_count=max(1, len(chunk["text"].split())),
                metadata_info={
                    "course_code": SSA101_CODE,
                    "section": chunk["section"],
                    "source_label": chunk["source_label"],
                    "doc_title": SSA101_DOC_TITLE,
                },
            )
        )
    session.commit()

    retrieval = RetrievalService(ChunkRepository(session))

    # Mirror the production order in QaService.ask: the guardrail runs BEFORE
    # retrieval, so an out-of-scope question is refused without ever touching
    # the index. Evaluating retrieval in isolation would misrepresent what a
    # student actually gets back.
    from src.services.core.guardrail_service import INTENT_OUT_OF_SCOPE, GuardrailService

    # Same in-memory session RAG already created above — GuardrailRule table
    # doesn't exist in it yet, but ensure_seeded() (called from
    # enabled_codes()) creates the rows on first read via the ORM, it
    # doesn't need the table pre-populated, only present in the schema —
    # which Base.metadata.create_all already covered.
    guardrail = GuardrailService(session)

    results: list[CaseResult] = []
    for case in _load("rag_eval.jsonl"):
        decision = guardrail.evaluate(case["question"])
        if decision.intent == INTENT_OUT_OF_SCOPE:
            retrieved = []
        else:
            retrieved = retrieval.retrieve(
                subject_code=SSA101_CODE, question=case["question"], student_id=None
            )
        got_ids = [item.chunk.chunk_id for item in retrieved]

        if not case["answerable"]:
            # Out-of-scope: passing means we retrieved nothing to answer from,
            # so the pipeline reports insufficient data instead of guessing.
            passed = len(got_ids) == 0
            results.append(
                CaseResult(
                    case["id"],
                    passed,
                    "no_retrieval",
                    f"{len(got_ids)} chunks",
                    "" if passed else f"unexpectedly matched {got_ids[:3]}",
                )
            )
            continue

        expected_ids = set(case["expected_chunk_ids"])
        hit = bool(expected_ids.intersection(got_ids))
        results.append(
            CaseResult(
                case["id"],
                hit,
                ",".join(sorted(expected_ids)),
                ",".join(got_ids[:3]) or "(none)",
                "" if hit else "expected chunk not in top-k",
            )
        )

    session.close()
    return results


# ── report ───────────────────────────────────────────────────────────────
def summarise(name: str, results: list[CaseResult]) -> tuple[str, int, int]:
    passed = sum(1 for item in results if item.passed)
    total = len(results)
    pct = (passed / total * 100) if total else 0.0
    lines = [f"### {name}", "", f"**{passed}/{total} passed ({pct:.0f}%)**", ""]
    failures = [item for item in results if not item.passed]
    if failures:
        lines += [
            "| case | expected | actual | note |",
            "|---|---|---|---|",
        ]
        lines += [
            f"| {item.case_id} | {item.expected} | {item.actual} | {item.detail} |"
            for item in failures
        ]
    else:
        lines.append("No failures.")
    lines.append("")
    return "\n".join(lines), passed, total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=None, help="write a markdown report here")
    args = parser.parse_args()

    from src.services.core.guardrail_service import GUARDRAIL_VERSION

    guardrail = run_guardrail()
    rag = run_rag()
    embedding_reachable = _embedding_backend_reachable()

    guardrail_md, g_pass, g_total = summarise("Guardrail", guardrail)
    rag_md, r_pass, r_total = summarise("RAG / retrieval citation", rag)

    # Reproducibility lock (mục 16.5 / mục 9 P0#5): without these, two runs
    # of this report are not comparable — a dataset edit, a rule-group
    # change, or a silent embedding-backend failure would all produce a
    # report that looks the same shape as before but measures something
    # different. Anything numeric above this line should be read alongside
    # these fields, not on its own.
    repro_md = "\n".join(
        [
            "## Reproducibility",
            "",
            f"- Guardrail ruleset version: `{GUARDRAIL_VERSION}`",
            f"- `guardrail_eval.jsonl` fingerprint: `{_dataset_fingerprint('guardrail_eval.jsonl')}`",
            f"- `rag_eval.jsonl` fingerprint: `{_dataset_fingerprint('rag_eval.jsonl')}`",
            f"- Semantic embedding backend reachable this run: **{embedding_reachable}**"
            + (
                ""
                if embedding_reachable
                else " — RAG suite above ran on lexical-only fallback, not semantic embedding"
            ),
            "",
        ]
    )

    report = "\n".join(
        [
            "# Cursus Gate-2 evaluation report",
            "",
            f"Generated: {datetime.now(UTC).isoformat()}",
            "",
            "Guardrail suite runs with no network (DB-backed rule toggles, "
            "in-memory SQLite only). RAG suite attempts real semantic "
            "embedding when a `GOOGLE_API_KEY` is configured and falls back "
            "to lexical-only scoring on any failure — see Reproducibility "
            "below for which path this run actually took.",
            "",
            repro_md,
            guardrail_md,
            rag_md,
        ]
    )

    print(report)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"\nWritten to {out}")

    # Non-zero only if a suite is badly broken; the harness is a report, not a gate.
    return 0 if (g_pass and r_pass) else 1


if __name__ == "__main__":
    raise SystemExit(main())
