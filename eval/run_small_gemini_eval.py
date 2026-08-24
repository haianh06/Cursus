"""P0#5 (mục 9 ý5) — small, budget-approved real-Gemini validation batch.

NOT a full benchmark (mục 16.5 already scoped that out of 23/08). Exactly
what was asked: 5 QA questions + 3 Plan scenarios + 3 Reflection scenarios
(<=11 real Gemini calls total), run against the real production code paths
(QaAnswerService.answer / PlanBuilder.generate / ReflectionEngine.
build_summary_llm), using the P0#8 trace fields to confirm each call was a
genuine llm_success=True, not a quiet quota/error fallback.

Runs against a throwaway in-memory SQLite DB (same established pattern as
eval/run_eval.py) -- never touches the Supabase dev DB. The GOOGLE_API_KEY
already configured in .env is used as-is; this script does not fetch or
print it.

Usage:
    python eval/run_small_gemini_eval.py --out eval/results/report.md
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Windows console defaults to cp1252, which can't encode Vietnamese
# diacritics in the questions/summaries this script prints as it runs --
# without this, a UnicodeEncodeError on a print() call kills the whole
# batch mid-run (confirmed: happened on the very first QA question),
# which looks indistinguishable from a real failure unless you read the
# traceback closely.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

QUOTA_SIGNAL_KEYWORDS = ("quota", "rate limit", "resource_exhausted", "429", "resourceexhausted")


class _TraceLogCapture(logging.Handler):
    """Captures qa_answer_service's structured qa_answer_trace log line (see
    src/services/ai/qa_answer_service.py::answer() docstring for why this
    service logs instead of writing a DB row)."""

    def __init__(self):
        super().__init__()
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record.getMessage())
        if record.exc_info:
            import traceback

            self.records.append("".join(traceback.format_exception(*record.exc_info)))


def _looks_like_quota_error(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in QUOTA_SIGNAL_KEYWORDS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    import os

    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("JWT_SECRET_KEY", "eval-harness-secret-key-at-least-32-characters")
    os.environ["DATABASE_URL"] = "sqlite://"

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from src.db import models
    from src.db.models import Base, Course, Document, DocType
    from src.repositories.chunk_repository import ChunkRepository
    from src.security.passwords import hash_password
    from src.services.ai.plan_builder import PlanBuilder
    from src.services.ai.qa_answer_service import QaAnswerService
    from src.services.ai.reflection_engine import ReflectionEngine
    from src.services.mock.gate2_demo import SSA101_CODE, SSA101_DOC_ID, SSA101_DOC_TITLE, load_ssa101_chunks
    from src.services.mock.real_curriculum_service import ingest_real_course
    from src.services.rag.retrieval_service import RetrievalService

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    # SSA101 real content (for QA)
    ssa_course = Course(id="course_eval_ssa101", code=SSA101_CODE, name="Kỹ năng học thuật", description="eval")
    db.add(ssa_course)
    db.add(
        Document(
            id=SSA101_DOC_ID, course_id=ssa_course.id, title=SSA101_DOC_TITLE,
            file_path="docs/planning/v2/data/chunks_SSA101.json", doc_type=DocType.SYLLABUS.value,
            version="2025-11-27", metadata_info={"source": "curriculum"},
        )
    )
    for chunk in load_ssa101_chunks():
        db.add(
            models.DocumentChunk(
                id=chunk["chunk_id"], document_id=SSA101_DOC_ID, chunk_index=chunk["chunk_index"],
                text=chunk["text"], token_count=max(1, len(chunk["text"].split())),
                metadata_info={
                    "course_code": SSA101_CODE, "section": chunk["section"],
                    "source_label": chunk["source_label"], "doc_title": SSA101_DOC_TITLE,
                },
            )
        )
    db.commit()

    # CEA201 real content (for Plan) -- ingest_real_course creates its own
    # Course row + real chunks from chunks_CEA201.json.
    ingest_real_course(db, "CEA201")
    db.commit()
    cea_course = db.query(Course).filter_by(code="CEA201").first()
    db.add(
        models.CourseSection(
            id="sec_eval_cea201", course_id=cea_course.id, instructor_id="inst_eval",
            term="Fall2026", section_code="EV01",
        )
    )
    db.add(
        models.User(
            id="student_eval", email="student.eval@example.test",
            password_hash=hash_password("EvalPassword123"), full_name="Eval Student",
            role=models.UserRole.STUDENT.value, is_email_verified=True, is_active=True,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    db.commit()

    logger_capture = _TraceLogCapture()
    logging.getLogger("src.services.ai.qa_answer_service").addHandler(logger_capture)
    logging.getLogger("src.services.ai.qa_answer_service").setLevel(logging.INFO)

    results = {"qa": [], "plan": [], "reflection": []}
    stopped_early = None

    # ── QA: 5 real, grounded questions phrased to need synthesis (so
    # _needs_llm() routes them to the LLM, not the cheap extractive path) ──
    QA_QUESTIONS = [
        "So sánh CLO4 và CLO9 của SSA101 khác nhau thế nào?",
        "Phân tích mối liên hệ giữa Time Management (session 7-12) và Critical Thinking (session 43-45) trong SSA101.",
        "Tại sao Information Literacy (session 22-23) lại quan trọng trước khi học về AI Hallucination (session 27)?",
        "So sánh Project Part 1 (session 13) và Group Project Part 3 (session 55-59) khác nhau thế nào?",
        "Giải thích vì sao Individual Progress Test (session 52-54) được xếp sau nội dung Metacognition (session 49)?",
    ]
    retrieval = RetrievalService(ChunkRepository(db))
    qa_service = QaAnswerService()
    for question in QA_QUESTIONS:
        logger_capture.records.clear()
        retrieved = retrieval.retrieve(subject_code=SSA101_CODE, question=question, student_id=None)
        answer, citations, mode = qa_service.answer(question=question, subject_code=SSA101_CODE, retrieved=retrieved)
        trace_line = next((r for r in logger_capture.records if r.startswith("qa_answer_trace")), "")
        exc_text = "\n".join(r for r in logger_capture.records if "Traceback" in r)
        results["qa"].append(
            {"question": question, "mode": mode, "trace": trace_line, "answer_preview": answer[:200], "exception": exc_text}
        )
        print(f"[QA] {question[:50]}... -> mode={mode} | {trace_line}")
        if exc_text and _looks_like_quota_error(exc_text):
            stopped_early = f"QA question {len(results['qa'])}/5"
            break

    # ── Plan: 3 real scenarios against real CEA201 content ──
    if not stopped_early:
        PLAN_TITLES = [
            ("Bài tập Chapter 3: Cache Memory", "Phân tích và thiết kế hệ thống bộ nhớ cache cho CPU theo nội dung Chapter 3."),
            ("Bài tập Chapter 8: Instruction Sets", "Viết báo cáo về đặc điểm và chức năng của tập lệnh CPU theo nội dung Chapter 8."),
            ("Bài tập Chapter 11: Parallel Processing", "Trình bày về xử lý song song và siêu vô hướng theo nội dung Chapter 11."),
        ]
        for index, (title, description) in enumerate(PLAN_TITLES):
            assignment = models.Assignment(
                id=f"asg_eval_cea201_{index}", section_id="sec_eval_cea201", title=title,
                description=description, due_date=datetime.now(UTC).replace(tzinfo=None), max_points=100,
                assessment_type="ASSIGNMENT",
            )
            db.add(assignment)
            db.flush()
            try:
                plan = PlanBuilder(db).generate(student_id="student_eval", assignment=assignment, available_hours=10)
                goals = plan.goals
                results["plan"].append(
                    {
                        "title": title,
                        "llm_attempted": goals.get("llm_attempted"),
                        "llm_success": goals.get("llm_success"),
                        "fallback_used": goals.get("fallback_used"),
                        "retrieval_empty": goals.get("retrieval_empty"),
                        "task_count": len(goals.get("task_meta") or {}),
                    }
                )
                print(f"[PLAN] {title} -> llm_success={goals.get('llm_success')} fallback_used={goals.get('fallback_used')} retrieval_empty={goals.get('retrieval_empty')}")
            except Exception as exc:
                results["plan"].append({"title": title, "error": str(exc)})
                print(f"[PLAN] {title} -> ERROR: {exc}")
                if _looks_like_quota_error(str(exc)):
                    stopped_early = f"Plan scenario {index + 1}/3"
                    break

    # ── Reflection: 3 realistic scenarios (own-week facts, not tied to a
    # specific document -- reflection summaries are about the student's
    # week, not course content) ──
    if not stopped_early:
        REFLECTION_SCENARIOS = [
            {
                "facts": {"weekNumber": 4, "totalTasks": 5, "completedTasks": 4, "deferredTasks": 1,
                          "estimatedMinutes": 300, "actualMinutes": 340, "completionRate": 0.8},
                "answers": [{"questionId": "q_obstacle", "answer": "Sơ đồ use-case mất nhiều thời gian hơn dự kiến."}],
                "adjustments": ["increase_diagram_estimate"],
            },
            {
                "facts": {"weekNumber": 5, "totalTasks": 4, "completedTasks": 2, "deferredTasks": 2,
                          "estimatedMinutes": 240, "actualMinutes": 150, "completionRate": 0.5},
                "answers": [{"questionId": "q_obstacle", "answer": "Bận việc gia đình đột xuất giữa tuần."}],
                "adjustments": [],
            },
            {
                "facts": {"weekNumber": 6, "totalTasks": 6, "completedTasks": 6, "deferredTasks": 0,
                          "estimatedMinutes": 360, "actualMinutes": 350, "completionRate": 1.0},
                "answers": [{"questionId": "q_next_priority", "answer": "Muốn bắt đầu ôn thi sớm hơn."}],
                "adjustments": [],
            },
        ]
        engine_svc = ReflectionEngine(db)
        for index, scenario in enumerate(REFLECTION_SCENARIOS):
            try:
                summary, trace = engine_svc.build_summary_llm(
                    facts=scenario["facts"], answers=scenario["answers"], adjustments=scenario["adjustments"],
                )
                results["reflection"].append({"week": scenario["facts"]["weekNumber"], "trace": trace, "summary_preview": summary[:200]})
                print(f"[REFLECTION] week={scenario['facts']['weekNumber']} -> {trace}")
            except Exception as exc:
                results["reflection"].append({"week": scenario["facts"]["weekNumber"], "error": str(exc)})
                print(f"[REFLECTION] week={scenario['facts']['weekNumber']} -> ERROR: {exc}")
                if _looks_like_quota_error(str(exc)):
                    stopped_early = f"Reflection scenario {index + 1}/3"
                    break

    db.close()

    # ── report ──
    lines = [
        "# P0#5 — Small real-Gemini validation batch",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
        "**Scope note: this is a SMALL, budget-approved validation batch "
        "(<=11 real Gemini calls: 5 QA + 3 Plan + 3 Reflection), NOT a full "
        "benchmark.** Full benchmark scale is explicitly out of scope for "
        "23/08 (mục 16.5). This batch exists to confirm the pipeline "
        "actually works against the real Gemini API, using the P0#8 trace "
        "fields to tell a genuine LLM success apart from a quota/error "
        "fallback -- not to measure quality at scale.",
        "",
    ]
    if stopped_early:
        lines += [f"**⚠️ STOPPED EARLY at {stopped_early} — quota/error signal detected. Not retried.**", ""]

    qa_success = sum(1 for r in results["qa"] if "llm_success=True" in r.get("trace", ""))
    lines += [
        "## QA", "",
        f"{qa_success}/{len(results['qa'])} calls confirmed llm_success=True via qa_answer_trace log.",
        "",
        "| question | mode | trace |",
        "|---|---|---|",
    ]
    for r in results["qa"]:
        lines.append(f"| {r['question'][:60]} | {r['mode']} | `{r['trace']}` |")
    lines.append("")

    plan_success = sum(1 for r in results["plan"] if r.get("llm_success") is True)
    lines += [
        "## Plan", "",
        f"{plan_success}/{len(results['plan'])} scenarios confirmed llm_success=True.",
        "",
        "| assignment | llm_attempted | llm_success | fallback_used | retrieval_empty | task_count |",
        "|---|---|---|---|---|---|",
    ]
    for r in results["plan"]:
        if "error" in r:
            lines.append(f"| {r['title']} | ERROR: {r['error']} | | | | |")
        else:
            lines.append(
                f"| {r['title']} | {r['llm_attempted']} | {r['llm_success']} | {r['fallback_used']} | {r['retrieval_empty']} | {r['task_count']} |"
            )
    lines.append("")

    reflection_success = sum(1 for r in results["reflection"] if r.get("trace", {}).get("llm_success") is True)
    lines += [
        "## Reflection", "",
        f"{reflection_success}/{len(results['reflection'])} scenarios confirmed llm_success=True.",
        "",
        "| week | trace |",
        "|---|---|",
    ]
    for r in results["reflection"]:
        if "error" in r:
            lines.append(f"| {r['week']} | ERROR: {r['error']} |")
        else:
            lines.append(f"| {r['week']} | {r['trace']} |")
    lines.append("")

    report = "\n".join(lines)
    print("\n" + "=" * 80 + "\n" + report)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"\nWritten to {out}")

    return 1 if stopped_early else 0


if __name__ == "__main__":
    raise SystemExit(main())
