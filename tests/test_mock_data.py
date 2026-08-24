# tests/test_mock_data.py

import pytest

from src.db.connection import SessionLocal
from src.db.models import (
    CourseSection,
    Enrollment,
    RiskSignal,
    StudyTask,
    User,
    WeeklyReflection,
    task_dependencies,
)


def _has_full_seed() -> bool:
    db = SessionLocal()
    try:
        return db.query(User).count() >= 600
    except Exception:  # noqa: BLE001 — empty/ephemeral test DB has no users table yet
        return False
    finally:
        db.close()


requires_full_seed = pytest.mark.skipif(
    not _has_full_seed(),
    reason="Full mock seed not loaded (run seed.py or TEST_DATABASE_URL with seeded DB)",
)


@requires_full_seed
def test_database_connections():
    """Verify that database connection is active and we can query the schema."""
    db = SessionLocal()
    try:
        users_count = db.query(User).count()
        assert users_count >= 600
        print(f"[test] Successfully queried database. Found {users_count} users.")
    finally:
        db.close()


@requires_full_seed
def test_referential_integrity():
    """Verify referential integrity of enrollments and course sections."""
    db = SessionLocal()
    try:
        enrollments = db.query(Enrollment).all()
        for e in enrollments:
            student = db.query(User).filter_by(id=e.student_id).first()
            section = db.query(CourseSection).filter_by(id=e.section_id).first()
            assert student is not None
            assert section is not None
    finally:
        db.close()


@requires_full_seed
def test_task_dependency_cycles():
    """Verify that there are no cycles in study task dependencies."""
    db = SessionLocal()
    try:
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
        assert not has_cycle, "Cycles detected in study task dependencies!"
    finally:
        db.close()


@requires_full_seed
def test_weekly_reflection_coverage():
    """Verify that reflections are populated for all students across 10 weeks."""
    db = SessionLocal()
    try:
        reflections_count = db.query(WeeklyReflection).count()
        # 600 students * 10 weeks = 6000 reflections
        assert reflections_count == 6000
    finally:
        db.close()


@requires_full_seed
def test_ethan_storyline_consistency():
    """Verify that Ethan's story and risk signals match the narrative timeline."""
    db = SessionLocal()
    try:
        ethan_risks = (
            db.query(RiskSignal)
            .filter_by(student_id="student_ethan")
            .order_by(RiskSignal.generated_at)
            .all()
        )
        # Ethan has risks triggered throughout the weeks
        assert len(ethan_risks) >= 3
        # Check that Week 6 is resolved
        w6_risk = db.query(RiskSignal).filter_by(id="risk_student_ethan_w6").first()
        assert w6_risk is not None
        assert w6_risk.resolved_at is not None
        assert w6_risk.resolution_type == "INSTRUCTOR_INTERVENTION"
    finally:
        db.close()


@pytest.mark.skip(
    reason=(
        "canvas_router disabled in src/main.py 2026-08-20 (Phase 2b security "
        "cleanup) — it exposed real Cursus PII via Canvas-shaped JSON gated only "
        "by admin session (not OAuth, not a separate datastore), and did not "
        "meet the Mock LMS bar in PROJECT_CONTEXT.md mục 6.6/9. Route now 404s, "
        "so this would fail on the 401 assertion. Left unmarked-deleted on "
        "purpose: if/when the real Mock LMS is built (mục 6.6), canvas_routes.py "
        "stays as a field-mapping reference and this test is the trace of what "
        "auth behavior it used to have."
    )
)
@pytest.mark.asyncio
async def test_canvas_mock_endpoints_require_admin_auth(client):
    """Canvas mock API must reject anonymous access (PII + write surface)."""
    paths = (
        "/api/v1/canvas/courses",
        "/api/v1/canvas/calendar_events",
        "/api/v1/canvas/courses/course_fake/users",
        "/api/v1/canvas/courses/course_fake/assignments/asg_fake/submissions",
    )
    for path in paths:
        resp = await client.get(path)
        assert resp.status_code == 401, path

    resp = await client.post(
        "/api/v1/canvas/courses/course_fake/assignments/asg_fake/submissions",
        json={"student_id": "user_fake", "content": {"url": "https://example.test"}},
    )
    assert resp.status_code == 401
