# src/api/student.py
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.security.authorization import require_roles
from src.security.ownership import (
    require_student_assignment_access,
    require_student_course_access,
)
from src.services.academic.timetable_service import monday_of
from src.services.ai.plan_builder import is_study_plan, serialize_plan
from src.services.ai.reflection_engine import ReflectionEngine, serialize_reflection
from src.services.mock import gate2_demo
from src.services.mock.gate2_demo import Gate2DemoService
from src.services.mock.student_mock_data_service import StudentMockDataService
from src.services.rag.document_ingest_service import DocumentIngestService

router = APIRouter(
    prefix="/student",
    tags=["student"],
    dependencies=[Depends(require_roles(models.UserRole.STUDENT))],
)

class PrivacySettingsUpdateRequest(BaseModel):
    share_reflection_summary: bool

@router.get("/privacy-settings")
def get_privacy_settings(
    current_user: models.User = Depends(get_current_user_from_token),
):
    return {"shareReflectionSummary": bool(current_user.share_reflection_summary)}

@router.patch("/privacy-settings")
def update_privacy_settings(
    payload: PrivacySettingsUpdateRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    current_user.share_reflection_summary = payload.share_reflection_summary
    db.commit()
    return {"shareReflectionSummary": current_user.share_reflection_summary}

@router.get("/dashboard")
def get_student_dashboard(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    # Auto-provision mock academic data for newly registered students, then
    # make sure the canonical Gate-2 SSA101 class/assignment exists on top.
    StudentMockDataService(db).ensure_if_missing(current_user.id)
    Gate2DemoService(db).ensure_student(current_user.id)

    # Retrieve enrollment sections
    sections = db.query(models.CourseSection).join(models.Enrollment).filter(
        models.Enrollment.student_id == current_user.id
    ).all()

    # Get course details
    courses_list = []
    course_ids = []
    for sec in sections:
        c = db.query(models.Course).filter_by(id=sec.course_id).first()
        if c:
            courses_list.append({
                "id": c.id,
                "code": c.code,
                "name": c.name,
                "description": c.description
            })
            course_ids.append(c.id)

    # Get upcoming assignments
    assignments = db.query(models.Assignment).filter(
        models.Assignment.section_id.in_([s.id for s in sections])
    ).all()

    upcoming_asg = []
    for a in assignments:
        # Check if already submitted
        sub = db.query(models.Submission).filter_by(
            assignment_id=a.id, student_id=current_user.id
        ).first()

        sec = next((s for s in sections if s.id == a.section_id), None)
        course_id = sec.course_id if sec else ""
        course_name = ""
        if course_id:
            co = next((c for c in courses_list if c["id"] == course_id), None)
            if co:
                course_name = co["name"]

        upcoming_asg.append({
            "id": a.id,
            "courseId": course_id,
            "courseName": course_name,
            "title": a.title,
            "dueDate": a.due_date.isoformat(),
            "estimatedMinutes": int(a.max_points * 20) if a.max_points else 120, # estimated mock minutes
            "weight": int(a.max_points) if a.max_points else 10,
            "submitted": sub is not None,
            "grade": sub.grade if sub else None
        })

    # Retrieve Weekly Plans
    weekly_plans = db.query(models.WeeklyPlan).filter_by(
        student_id=current_user.id
    ).order_by(models.WeeklyPlan.week_number.desc()).all()

    # Calculate workload and weekly progress
    hours_planned = 0.0
    hours_available = 12.0
    completed_tasks = 0
    total_tasks = 0
    current_week = 6

    if weekly_plans:
        latest_plan = weekly_plans[0]
        current_week = latest_plan.week_number
        hours_available = latest_plan.study_hours_allocated or 12.0

        # Get tasks under this weekly plan
        daily_plans = db.query(models.DailyPlan).filter_by(
            weekly_plan_id=latest_plan.id
        ).all()

        for dp in daily_plans:
            blocks = db.query(models.ScheduleBlock).filter_by(
                daily_plan_id=dp.id
            ).all()
            for b in blocks:
                tasks = db.query(models.StudyTask).filter_by(
                    schedule_block_id=b.id
                ).all()
                for t in tasks:
                    total_tasks += 1
                    hours_planned += (t.planned_minutes / 60.0)
                    if t.status == "COMPLETED":
                        completed_tasks += 1

    # Check risk signals
    active_risks = db.query(models.RiskSignal).filter_by(
        student_id=current_user.id, resolved_at=None
    ).all()

    risk_level = "LOW"
    if any(r.risk_level == "HIGH" for r in active_risks):
        risk_level = "HIGH"
    elif any(r.risk_level == "MEDIUM" for r in active_risks):
        risk_level = "MEDIUM"

    return {
        "curriculum": {
            "id": 3007,
            "code": "BIT_SE_K20D_K21A",
            "program": "Software Engineering",
            "institution": "FPT University",
            "referenceLinks": []
        },
        "currentWeek": current_week,
        "courses": courses_list,
        "upcomingAssignments": upcoming_asg,
        "weeklyProgress": {
            "completed": completed_tasks or 3,
            "total": total_tasks or 8
        },
        "workload": {
            "hoursPlanned": round(hours_planned, 1) or 9.0,
            "hoursAvailable": hours_available
        },
        "riskStatus": risk_level
    }

@router.get("/courses")
def get_student_courses(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    sections = db.query(models.CourseSection).join(models.Enrollment).filter(
        models.Enrollment.student_id == current_user.id
    ).all()
    courses = []
    for s in sections:
        c = db.query(models.Course).filter_by(id=s.course_id).first()
        if c:
            courses.append({
                "id": c.id,
                "code": c.code,
                "name": c.name,
                "credits": 3,
                "description": c.description
            })
    return courses

@router.get("/courses/{course_id}")
def get_student_course_detail(
    course_id: str,
    _: None = Depends(require_student_course_access),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    course = db.query(models.Course).filter_by(id=course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    sections = db.query(models.CourseSection).filter_by(course_id=course_id).all()

    # Find modules and lessons
    modules_list = []
    for s in sections:
        mods = db.query(models.Module).filter_by(section_id=s.id).all()
        for m in mods:
            lessons = db.query(models.Lesson).filter_by(module_id=m.id).all()
            modules_list.append({
                "id": m.id,
                "title": m.title,
                "description": m.description,
                "week_number": m.week_number,
                "sequence_order": m.sequence_order,
                "lessons": [
                    {
                        "id": lesson.id,
                        "title": lesson.title,
                        "content": lesson.content,
                        "sequence_order": lesson.sequence_order,
                    }
                    for lesson in lessons
                ]
            })

    documents = db.query(models.Document).filter_by(course_id=course_id).all()
    visible_docs = []
    for document in documents:
        meta = document.metadata_info or {}
        source = meta.get("source") or "curriculum"
        uploaded_by = meta.get("uploaded_by")
        if source == "student_upload" and uploaded_by != current_user.id:
            continue
        visible_docs.append(
            {
                "id": document.id,
                "title": document.title,
                "file_path": document.file_path,
                "doc_type": document.doc_type,
                "source": source,
                "uploadedBy": uploaded_by,
                "canDelete": source == "student_upload"
                and uploaded_by == current_user.id,
            }
        )

    return {
        "id": course.id,
        "code": course.code,
        "name": course.name,
        "description": course.description,
        "syllabus": course.syllabus,
        "assessment_structure": course.assessment_structure,
        "modules": modules_list,
        "documents": visible_docs,
    }


@router.post("/courses/{course_id}/documents", status_code=201)
async def upload_student_document(
    course_id: str,
    _: None = Depends(require_student_course_access),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
):
    """Upload a personal .md/.txt note for an enrolled course (feeds Study Assistant)."""
    content = await file.read()
    service = DocumentIngestService(db)
    try:
        return service.upload_for_student(
            student_id=current_user.id,
            course_id=course_id,
            filename=file.filename or "notes.txt",
            content=content,
            title=title,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/courses/{course_id}/documents/{document_id}", status_code=204)
def delete_student_document(
    course_id: str,
    document_id: str,
    _: None = Depends(require_student_course_access),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    document = db.query(models.Document).filter_by(id=document_id, course_id=course_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    service = DocumentIngestService(db)
    try:
        service.delete_for_student(student_id=current_user.id, document_id=document_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return None

@router.get("/assignments/{assignment_id}")
def get_student_assignment_detail(
    assignment_id: str,
    _: None = Depends(require_student_assignment_access),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    a = db.query(models.Assignment).filter_by(id=assignment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")

    sub = db.query(models.Submission).filter_by(
        assignment_id=a.id, student_id=current_user.id
    ).first()

    sec = db.query(models.CourseSection).filter_by(id=a.section_id).first()
    course_id = sec.course_id if sec else ""
    course_name = ""
    if sec:
        c = db.query(models.Course).filter_by(id=sec.course_id).first()
        if c:
            course_name = c.name

    return {
        "id": a.id,
        "courseId": course_id,
        "courseName": course_name,
        "title": a.title,
        "description": a.description,
        "dueDate": a.due_date.isoformat(),
        "estimatedMinutes": int(a.max_points * 20) if a.max_points else 120,
        "weight": int(a.max_points) if a.max_points else 10,
        "maxPoints": a.max_points,
        "submitted": sub is not None,
        "submission": {
            "id": sub.id,
            "submittedAt": sub.submitted_at.isoformat(),
            "grade": sub.grade,
            "gradingStatus": sub.grading_status,
            "isLate": sub.is_late,
            "content": sub.content
        } if sub else None
    }

@router.get("/risks")
def get_student_risks(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    risks = db.query(models.RiskSignal).filter_by(
        student_id=current_user.id
    ).order_by(models.RiskSignal.generated_at.desc()).all()

    result = []
    for r in risks:
        sec = db.query(models.CourseSection).filter_by(id=r.section_id).first()
        course_id = sec.course_id if sec else ""
        result.append({
            "id": r.id,
            "courseId": course_id,
            "assignmentId": r.assignment_id,
            "riskType": r.risk_type,
            "riskLevel": r.risk_level,
            "evidence": r.evidence,
            "resolvedAt": r.resolved_at.isoformat() if r.resolved_at else None,
            "resolutionType": r.resolution_type,
            "generatedAt": r.generated_at.isoformat()
        })
    return result


@router.get("/reflections")
def get_student_reflections(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.WeeklyReflection)
        .filter_by(student_id=current_user.id)
        .order_by(models.WeeklyReflection.week_number.desc())
        .all()
    )
    return [serialize_reflection(row) for row in rows]


class ReflectionAnswer(BaseModel):
    questionId: str  # noqa: N815
    # `text` questions (self_notes, and the legacy free-text catalog).
    answer: str | None = Field(default=None, max_length=2000)
    # `single_choice` questions (the 5 fixed scales) — always a single code.
    selectedCodes: list[str] = Field(default_factory=list)  # noqa: N815
    # Unused by the current catalog — kept so a legacy client / stored
    # reflection row from before the fixed 6-question catalog never breaks
    # this schema.
    reasonCode: str | None = None  # noqa: N815
    items: list[str] = Field(default_factory=list)


class SaveReflectionRequest(BaseModel):
    plan_id: str | None = None
    week_number: int | None = None
    answers: list[ReflectionAnswer] = Field(default_factory=list)
    adjustments: list[str] = Field(default_factory=list)
    # The memory preview the student edited. Empty -> regenerate the template.
    summary: str | None = Field(default=None, max_length=4000)
    student_confirmed: bool = False
    share_with_advisor: bool = False


def _resolve_plan_for_reflection(
    db: Session, *, student_id: str, plan_id: str | None, week_number: int | None
) -> models.WeeklyPlan:
    if plan_id:
        plan = db.query(models.WeeklyPlan).filter_by(id=plan_id).first()
        if plan and plan.student_id == student_id:
            return plan
        raise HTTPException(status_code=404, detail="Weekly plan not found")

    target_week = (
        week_number
        if week_number is not None
        else monday_of(date.today()).isocalendar().week
    )
    plans = [
        plan
        for plan in db.query(models.WeeklyPlan)
        .filter_by(student_id=student_id, week_number=target_week)
        .all()
        if is_study_plan(plan)
    ]
    if not plans:
        plans = [
            plan
            for plan in db.query(models.WeeklyPlan)
            .filter_by(student_id=student_id)
            .order_by(models.WeeklyPlan.week_number.desc())
            .all()
            if is_study_plan(plan)
        ]
    if not plans:
        raise HTTPException(status_code=404, detail="Weekly plan not found")
    plans.sort(
        key=lambda item: (
            1 if (item.goals or {}).get("assignment_id") else 0,
            item.id,
        ),
        reverse=True,
    )
    return plans[0]


@router.get("/reflections/preview")
def preview_reflection(
    week_number: int | None = Query(default=None),
    plan_id: str | None = Query(default=None),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Real facts + the adaptive question set for this completion band."""
    plan = _resolve_plan_for_reflection(
        db, student_id=current_user.id, plan_id=plan_id, week_number=week_number
    )
    return ReflectionEngine(db).preview(plan)


@router.post("/reflections/preview-summary")
def preview_reflection_summary(
    payload: SaveReflectionRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Draft the memory text WITHOUT storing it, so the student can edit it
    before anything is written (Blueprint §3.1 'Preview memory trước khi lưu')."""
    plan = _resolve_plan_for_reflection(
        db,
        student_id=current_user.id,
        plan_id=payload.plan_id,
        week_number=payload.week_number,
    )
    engine = ReflectionEngine(db)
    facts = engine.facts_for_plan(plan)
    summary, trace = engine.build_summary_llm(
        facts=facts,
        answers=[item.model_dump() for item in payload.answers],
        adjustments=payload.adjustments,
    )
    return {
        "planId": plan.id,
        "weekNumber": plan.week_number,
        "facts": facts,
        "summary": summary,
        "editable": True,
        # P0#8 trace — this endpoint is the only place this service actually
        # calls the LLM; not persisted (the student may edit/replace this
        # draft before /reflections saves anything), but exposed here so a
        # caller (e.g. eval tooling) can tell an LLM draft from a
        # deterministic one without guessing from the text.
        "trace": trace,
    }


@router.post("/reflections")
def save_reflection(
    payload: SaveReflectionRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Store answers + structured adjustments. Only `student_confirmed`
    reflections are allowed to feed the next plan."""
    plan = _resolve_plan_for_reflection(
        db,
        student_id=current_user.id,
        plan_id=payload.plan_id,
        week_number=payload.week_number,
    )
    row = ReflectionEngine(db).save(
        plan=plan,
        answers=[item.model_dump() for item in payload.answers],
        adjustments=payload.adjustments,
        summary=payload.summary,
        student_confirmed=payload.student_confirmed,
        share_with_advisor=payload.share_with_advisor,
    )
    result = serialize_reflection(row)
    result["plan"] = serialize_plan(db, plan)
    return result


class GenerateReflectionRequest(BaseModel):
    week_number: int


@router.post("/reflections/generate")
def generate_weekly_reflection(
    payload: GenerateReflectionRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Back-compat entry point: returns the evidence + question set rather
    than a canned paragraph. Kept so older clients do not 404."""
    plan = _resolve_plan_for_reflection(
        db,
        student_id=current_user.id,
        plan_id=None,
        week_number=payload.week_number,
    )
    engine = ReflectionEngine(db)
    preview = engine.preview(plan)
    existing = preview.get("existing")
    if existing:
        return existing
    facts = preview["facts"]
    return {
        "id": None,
        "weekNumber": plan.week_number,
        "planId": plan.id,
        "summary": engine.build_summary(facts=facts, answers=[], adjustments=[]),
        "content": engine.build_summary(facts=facts, answers=[], adjustments=[]),
        "facts": facts,
        "answers": [],
        "adjustments": [],
        "band": preview["band"],
        "questions": preview["questions"],
        "studentConfirmed": False,
        "metrics": facts,
        "generatedAt": None,
    }


@router.get("/demo/state")
def get_demo_state(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """One canonical read for the whole student slice.

    Frontend pages read this instead of holding their own mock: same shapes
    on Dashboard, Planner and Reflection, so a task edited in one place is
    the same record everywhere.
    """
    StudentMockDataService(db).ensure_if_missing(current_user.id)
    info = Gate2DemoService(db).ensure_student(current_user.id)

    assignment = (
        db.query(models.Assignment)
        .filter_by(id=gate2_demo.PART1_ASSIGNMENT_ID)
        .first()
    )
    week_number = monday_of(date.today()).isocalendar().week
    plans = [
        plan
        for plan in db.query(models.WeeklyPlan)
        .filter_by(student_id=current_user.id)
        .order_by(models.WeeklyPlan.week_number.desc())
        .all()
        if is_study_plan(plan)
    ]
    current_plan = next(
        (plan for plan in plans if plan.week_number == week_number), None
    )
    if current_plan is None and plans:
        current_plan = plans[0]
    next_plan = next(
        (
            plan
            for plan in plans
            if plan.week_number > week_number
            or (plan.goals or {}).get("created_from_reflection_id")
        ),
        None,
    )

    reflections = (
        db.query(models.WeeklyReflection)
        .filter_by(student_id=current_user.id)
        .order_by(models.WeeklyReflection.week_number.desc())
        .all()
    )

    return {
        "fixtureVersion": info.get("fixtureVersion"),
        "demo": True,
        "student": {
            "id": current_user.id,
            "displayName": current_user.full_name,
            "email": current_user.email,
        },
        "course": {
            "id": info.get("courseId"),
            "code": gate2_demo.SSA101_CODE,
            "name": "Kỹ năng học thuật / Academic Skills",
            "sectionId": info.get("sectionId"),
            "syllabusVersion": gate2_demo.SSA101_SYLLABUS_VERSION,
        },
        "assignment": {
            "id": assignment.id,
            "title": assignment.title,
            "description": assignment.description,
            "dueAt": assignment.due_date.isoformat(),
            "deliverables": gate2_demo.deliverables_payload(),
            "sourceRefs": list(gate2_demo.PART1_SOURCE_REFS),
            "sourceNote": (
                "Syllabus chỉ chứng minh có Project Part 1 ở Session 13–15. "
                "Deadline và 4 hạng mục nộp là dữ liệu mô phỏng cho demo."
            ),
            "provenance": {
                "source_type": "simulated",
                "source_id": gate2_demo.PART1_ASSIGNMENT_ID,
            },
        }
        if assignment
        else None,
        "weekNumber": week_number,
        "currentPlan": serialize_plan(db, current_plan) if current_plan else None,
        "nextPlan": serialize_plan(db, next_plan)
        if next_plan is not None and next_plan is not current_plan
        else None,
        "reflections": [serialize_reflection(row) for row in reflections],
        "deferReasons": [
            {"code": code, "label": label}
            for code, label in gate2_demo.DEFER_REASON_CODES
        ],
    }


@router.post("/personal-data/delete")
def delete_my_personal_data(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """mục 6.3/6.4 Cài đặt: self-service hard delete of the caller's own
    reflections and Cursus Assistant chat history. Aggregated class/school
    metrics are untouched -- they carry no student_id link to this user."""
    conversation_ids = [
        row[0]
        for row in db.query(models.Conversation.id).filter_by(student_id=current_user.id).all()
    ]
    messages_deleted = 0
    if conversation_ids:
        messages_deleted = (
            db.query(models.Message)
            .filter(models.Message.conversation_id.in_(conversation_ids))
            .delete(synchronize_session=False)
        )
    conversations_deleted = (
        db.query(models.Conversation)
        .filter_by(student_id=current_user.id)
        .delete(synchronize_session=False)
    )
    reflections_deleted = (
        db.query(models.WeeklyReflection)
        .filter_by(student_id=current_user.id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return {
        "reflectionsDeleted": reflections_deleted,
        "conversationsDeleted": conversations_deleted,
        "messagesDeleted": messages_deleted,
    }
