from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import (
    Base,
    CourseSection,
    DailyPlan,
    Enrollment,
    RiskSignal,
    ScheduleBlock,
    StudyTask,
    User,
    UserRole,
    WeeklyPlan,
)
from src.services.ai.risk_engine import DEFAULT_SEVERITY_BANDS, DEFAULT_SIGNAL_THRESHOLDS, DEFAULT_SIGNAL_WEIGHTS
from src.services.core.risk_policy_service import (
    RiskPolicyService,
    RiskPolicyValidationError,
    validate_policy_input,
)

VALID_BANDS = [list(band) for band in DEFAULT_SEVERITY_BANDS]


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_validate_accepts_the_shipped_defaults():
    validate_policy_input(DEFAULT_SIGNAL_WEIGHTS, DEFAULT_SIGNAL_THRESHOLDS, VALID_BANDS)


def test_validate_rejects_negative_weight():
    bad_weights = dict(DEFAULT_SIGNAL_WEIGHTS, OVERDUE_TASKS_2_PLUS=-1)
    with pytest.raises(RiskPolicyValidationError):
        validate_policy_input(bad_weights, DEFAULT_SIGNAL_THRESHOLDS, VALID_BANDS)


def test_validate_rejects_absurd_needs_support_threshold_of_one():
    """mục 14.1's own example of what must be rejected: 'ngưỡng nên hỗ trợ = 1'."""
    bad_bands = [[0, "normal", "LOW"], [1, "watch", "MEDIUM"], [1, "needs_support", "HIGH"]]
    with pytest.raises(RiskPolicyValidationError):
        validate_policy_input(DEFAULT_SIGNAL_WEIGHTS, DEFAULT_SIGNAL_THRESHOLDS, bad_bands)


def test_validate_rejects_missing_signal_code():
    incomplete = {k: v for k, v in DEFAULT_SIGNAL_WEIGHTS.items() if k != "INACTIVE_7_DAYS"}
    with pytest.raises(RiskPolicyValidationError):
        validate_policy_input(incomplete, DEFAULT_SIGNAL_THRESHOLDS, VALID_BANDS)


def test_publish_requires_a_reason(db):
    service = RiskPolicyService(db)
    with pytest.raises(RiskPolicyValidationError):
        service.publish(
            signal_weights=DEFAULT_SIGNAL_WEIGHTS,
            signal_thresholds=DEFAULT_SIGNAL_THRESHOLDS,
            severity_bands=VALID_BANDS,
            reason="   ",
            actor_user_id=None,
        )


def test_publish_creates_increasing_versions_without_overwriting_history(db):
    service = RiskPolicyService(db)
    v1 = service.publish(
        signal_weights=DEFAULT_SIGNAL_WEIGHTS,
        signal_thresholds=DEFAULT_SIGNAL_THRESHOLDS,
        severity_bands=VALID_BANDS,
        reason="initial",
        actor_user_id=None,
    )
    tightened = dict(DEFAULT_SIGNAL_THRESHOLDS, COMPLETION_BELOW_40=0.5)
    v2 = service.publish(
        signal_weights=DEFAULT_SIGNAL_WEIGHTS,
        signal_thresholds=tightened,
        severity_bands=VALID_BANDS,
        reason="tighten completion threshold",
        actor_user_id=None,
    )

    assert v2.policy_version == v1.policy_version + 1
    history = service.list_history()
    assert [p.policy_version for p in history] == [v2.policy_version, v1.policy_version]
    # v1 itself must still read back exactly as published — publishing v2 must
    # not have mutated it.
    assert service.get_active().policy_version == v2.policy_version


def test_rollback_creates_a_new_version_copying_the_target_not_reverting_in_place(db):
    service = RiskPolicyService(db)
    v1 = service.publish(
        signal_weights=DEFAULT_SIGNAL_WEIGHTS,
        signal_thresholds=DEFAULT_SIGNAL_THRESHOLDS,
        severity_bands=VALID_BANDS,
        reason="initial",
        actor_user_id=None,
    )
    service.publish(
        signal_weights=dict(DEFAULT_SIGNAL_WEIGHTS, OVERDUE_TASKS_2_PLUS=4),
        signal_thresholds=DEFAULT_SIGNAL_THRESHOLDS,
        severity_bands=VALID_BANDS,
        reason="experiment",
        actor_user_id=None,
    )

    v3 = service.rollback(target_version=v1.policy_version, reason="experiment made things worse", actor_user_id=None)

    assert v3.policy_version == 3  # new version, not v1 reused
    assert v3.rolled_back_from == v1.policy_version
    assert v3.signal_weights == DEFAULT_SIGNAL_WEIGHTS
    assert len(service.list_history()) == 3  # v1 and v2 both still readable


def test_rollback_unknown_version_raises_lookup_error(db):
    service = RiskPolicyService(db)
    with pytest.raises(LookupError):
        service.rollback(target_version=999, reason="does not exist", actor_user_id=None)


def _seed_student_with_overdue_tasks(db, student_id: str, section_id: str, overdue_count: int) -> None:
    """Full WeeklyPlan -> DailyPlan -> ScheduleBlock -> StudyTask chain —
    `RiskEngine._tasks_with_schedule()` inner-joins all four, so a bare
    StudyTask row is invisible to assess() without it."""
    now = datetime.now(UTC).replace(tzinfo=None)
    db.add(
        User(
            id=student_id,
            email=f"{student_id}@example.test",
            password_hash="x",
            full_name=student_id,
            role=UserRole.STUDENT.value,
            is_active=True,
            created_at=now,
        )
    )
    db.add(CourseSection(id=section_id, course_id="course_x", instructor_id="inst_x", term="Fall2026", section_code="SE1"))
    db.add(Enrollment(id=f"enr_{student_id}", student_id=student_id, section_id=section_id, status="ENROLLED", enrolled_at=now))

    db.add(WeeklyPlan(id=f"wp_{student_id}", student_id=student_id, week_number=1, goals={}, study_hours_allocated=5.0))
    db.add(DailyPlan(id=f"dp_{student_id}", weekly_plan_id=f"wp_{student_id}", date=now, status="IN_PROGRESS"))
    db.add(
        ScheduleBlock(
            id=f"sb_{student_id}",
            daily_plan_id=f"dp_{student_id}",
            start_time=now,
            end_time=now,  # in the past relative to RiskEngine's `now` (set later in the test)
            activity_description="study block",
        )
    )
    for i in range(overdue_count):
        db.add(
            StudyTask(
                id=f"task_{student_id}_{i}",
                schedule_block_id=f"sb_{student_id}",
                title=f"task {i}",
                planned_minutes=30,
                priority="MEDIUM",
                status="TODO",
                difficulty="MEDIUM",
            )
        )
    db.commit()


def test_preview_reports_severity_changes_without_persisting_anything(db):
    service = RiskPolicyService(db)
    service.publish(
        signal_weights=DEFAULT_SIGNAL_WEIGHTS,
        signal_thresholds=DEFAULT_SIGNAL_THRESHOLDS,
        severity_bands=VALID_BANDS,
        reason="initial",
        actor_user_id=None,
    )
    _seed_student_with_overdue_tasks(db, "stu_preview", "sec_preview", overdue_count=5)
    db.add(
        RiskSignal(
            id="alert_preview_seed",
            student_id="stu_preview",
            section_id="sec_preview",
            risk_type="WEEKLY_GOAL_FAILURE",
            risk_level="LOW",
            triggered_rules={},
            evidence={},
            recommended_action="",
            generated_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    db.commit()

    # stu_preview has no ProgressEvent rows at all (never touched the app in
    # the assessment window) on top of the overdue/low-completion tasks, so
    # it scores 6 under the default bands (OVERDUE_TASKS_2_PLUS +2,
    # COMPLETION_BELOW_40 +2, INACTIVE_7_DAYS +2) -> "needs_support" (>=5).
    # Raising that band's threshold from 5 to 7 demotes the same score to
    # "watch" without touching any weight/threshold that produces it.
    looser_bands = [[0, "normal", "LOW"], [3, "watch", "MEDIUM"], [7, "needs_support", "HIGH"]]
    preview = service.preview(
        signal_weights=DEFAULT_SIGNAL_WEIGHTS,
        signal_thresholds=DEFAULT_SIGNAL_THRESHOLDS,
        severity_bands=looser_bands,
    )

    assert preview["totalEvaluated"] == 1
    assert preview["changedCount"] == 1
    assert preview["changes"][0]["studentId"] == "stu_preview"
    assert preview["changes"][0]["afterSeverity"] != preview["changes"][0]["beforeSeverity"]

    # Preview must not have written a new policy version or touched the seed row.
    assert len(service.list_history()) == 1
    untouched = db.query(RiskSignal).filter_by(id="alert_preview_seed").one()
    assert untouched.risk_level == "LOW"
