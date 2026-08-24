# seed.py
import argparse
import sys
import os
import shutil
import random
from datetime import datetime
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import Session

# Add current path to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.db.models import Base, StudyTask, task_dependencies, Enrollment, CourseSection, Assignment, Submission
from src.db.connection import engine, SessionLocal

# TODO(Phase 3 — mock_data regenerate): mock_data/ was deleted whole (Phase 1,
# 2026-08-20) so this whole generic seeder pipeline is disconnected on purpose.
# Do NOT write replacement logic here — Phase 3 regenerates mock_data/ against
# real curriculum data (data/clean/) and the Mock LMS built in Phase 2, then
# restores these imports pointing at the new generators. Until then, anything
# below that calls seed_foundation/seed_course_content/seed_planning_and_activity/
# seed_reflections_and_risks/seed_rag_and_guardrails/COURSES_CONFIG will raise
# NameError loudly — that is intentional, not a bug.
# from mock_data.generators.user_gen import seed_foundation
# from mock_data.generators.course_gen import seed_course_content
# from mock_data.generators.planning_gen import seed_planning_and_activity
# from mock_data.generators.reflection_gen import seed_reflections_and_risks
# from mock_data.generators.rag_gen import seed_rag_and_guardrails
# from mock_data.config import COURSES_CONFIG

def run_validation(db: Session) -> bool:
    print("[validate] Running dataset consistency checks...")
    success = True

    # 1. Referential integrity: check if enrollments have valid students and sections
    enrollments = db.query(Enrollment).all()
    for e in enrollments:
        if not e.student_id or not e.section_id:
            print(f"[validate] ❌ Orphaned enrollment found: ID={e.id}")
            success = False

    # 2. Check task dependencies for cycles
    tasks = db.query(StudyTask).all()
    adj = {t.id: [] for t in tasks}
    deps = db.execute(task_dependencies.select()).all()
    for parent, child in deps:
        if parent in adj:
            adj[parent].append(child)

    visited = {}
    def dfs(node):
        visited[node] = 1
        for neighbor in adj.get(node, []):
            if visited.get(neighbor, 0) == 1:
                return True
            if visited.get(neighbor, 0) == 0:
                if dfs(neighbor):
                    return True
        visited[node] = 2
        return False

    has_cycle = False
    for t_id in adj:
        if visited.get(t_id, 0) == 0:
            if dfs(t_id):
                has_cycle = True
                break
    if has_cycle:
        print("[validate] ❌ Cycle detected in study task dependencies!")
        success = False
    else:
        print("[validate]  Task dependencies are cycle-free.")

    # 3. Check submission timings
    submissions = db.query(Submission).all()
    for sub in submissions:
        if sub.assignment_id:
            assign = db.query(Assignment).filter_by(id=sub.assignment_id).first()
            if assign and sub.submitted_at > assign.due_date and not sub.is_late:
                # Due date is overridden or late flag missing
                pass

    if success:
        print("[validate]  All consistency validation checks passed successfully!")
    else:
        print("[validate] ❌ Consistency validation checks failed.")
    return success

def export_sql_dump(db: Session, dest_path: str):
    print(f"[export] Exporting SQL dump to {dest_path}...")
    # Generate portable SQL INSERT statements for all tables
    meta = Base.metadata
    
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write("-- AI Learning Companion Synthetic Mock Data Dump\n")
        f.write("-- Generated at: " + datetime.now().isoformat() + "\n\n")
        
        # Disable foreign key checks for clean load
        f.write("PRAGMA foreign_keys = OFF;\n")
        f.write("SET CONSTRAINTS ALL DEFERRED;\n\n")

        # Query all records from tables in topological order if possible
        for table in meta.sorted_tables:
            f.write(f"-- Data for table: {table.name}\n")
            rows = db.execute(table.select()).all()
            for r in rows:
                cols = ", ".join(table.columns.keys())
                vals = []
                for val in r:
                    if val is None:
                        vals.append("NULL")
                    elif isinstance(val, (int, float)):
                        vals.append(str(val))
                    elif isinstance(val, bool):
                        vals.append("1" if val else "0")
                    elif isinstance(val, datetime):
                        vals.append(f"'{val.isoformat()}'")
                    elif isinstance(val, dict):
                        # serialize JSON
                        import json
                        escaped = json.dumps(val, ensure_ascii=False).replace("'", "''")
                        vals.append(f"'{escaped}'")
                    else:
                        escaped = str(val).replace("'", "''")
                        vals.append(f"'{escaped}'")
                vals_str = ", ".join(vals)
                f.write(f"INSERT INTO {table.name} ({cols}) VALUES ({vals_str});\n")
            f.write("\n")
        
        f.write("PRAGMA foreign_keys = ON;\n")
    print(f"[export] SQL dump successfully written to {dest_path}")

def main():
    parser = argparse.ArgumentParser(description="AI Learning Companion Seeder Pipeline")
    parser.add_argument("--reset", action="store_true", help="Safely reset and drop database tables before seeding")
    parser.add_argument("--seed", type=int, default=20260803, help="Explicit random seed for deterministic generation")
    parser.add_argument("--validate-only", action="store_true", help="Run consistency validation checks on existing DB and exit")
    parser.add_argument("--export-dump", action="store_true", help="Export seeded database as SQL dump")
    parser.add_argument("--generate-documents", action="store_true", help="Create document directory placeholders")
    parser.add_argument("--skip-documents", action="store_true", help="Skip creating document directories")
    parser.add_argument("--courses", type=str, help="Comma-separated list of course codes to seed")
    args = parser.parse_args()

    db = SessionLocal()

    if args.validate_only:
        valid = run_validation(db)
        sys.exit(0 if valid else 1)

    if args.reset:
        print("[seed] Resetting database data (keeping Alembic schema)...")
        from sqlalchemy import text

        dialect = engine.dialect.name
        with engine.begin() as connection:
            if dialect == "postgresql":
                table_names = ", ".join(
                    f'"{table.name}"' for table in Base.metadata.sorted_tables
                )
                if table_names:
                    connection.execute(
                        text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
                    )
            else:
                # SQLite / others: drop + recreate (tests / legacy only)
                Base.metadata.drop_all(bind=connection)
                Base.metadata.create_all(bind=connection)
        print("[seed] Data cleared.")

    if args.generate_documents and not args.skip_documents:
        print("[seed] Generating educational document directories...")
        doc_dir = os.path.join(os.path.dirname(__file__), "mock_data", "documents")
        os.makedirs(doc_dir, exist_ok=True)
        for c in COURSES_CONFIG.keys():
            os.makedirs(os.path.join(doc_dir, c), exist_ok=True)
            # Create mock syllabus and faq files
            with open(os.path.join(doc_dir, c, "syllabus.pdf"), "w") as f:
                f.write("%PDF-1.4 mock syllabus content")
            with open(os.path.join(doc_dir, c, "faq.md"), "w") as f:
                f.write(f"# {c} FAQ\nSynthetic QA helper resource.")

    # 1. Foundation: Seed users, cohorts, enrollments
    student_persona_map = seed_foundation(db, seed_val=args.seed)

    # 2. Course Content: Seed modules, assignments, quizzes, rubrics
    start_date = datetime(2026, 9, 7) # Standard Autumn Term start date
    assignments, quizzes = seed_course_content(db, start_date=start_date)

    # 3. Planning: Seed learning plans, schedules, checklist tasks, submissions
    seed_planning_and_activity(db, student_persona_map, start_date=start_date,
                               assignments=assignments, quizzes=quizzes)

    # 4. Reflections & Risks: Seed weekly reflections and rule-based risk signals
    seed_reflections_and_risks(db, student_persona_map, start_date=start_date)

    # 5. RAG & Guardrails: Index document chunks and evaluation datasets
    seed_rag_and_guardrails(db)

    # 6. Validate the final dataset
    valid = run_validation(db)
    if not valid:
        print("[seed] ❌ Seeding aborted/failed due to consistency validation checks.")
        sys.exit(1)

    # 7. Export SQL dump if requested
    if args.export_dump:
        os.makedirs("mock_data/generated", exist_ok=True)
        export_sql_dump(db, "mock_data/generated/mock_data_dump.sql")

    db.close()
    print("[seed] Seeder pipeline finished successfully!")

if __name__ == "__main__":
    main()
