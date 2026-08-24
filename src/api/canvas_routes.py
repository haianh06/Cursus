# src/api/canvas_routes.py
"""Canvas-shaped mock LMS API — ADMIN only.

These routes expose PII (emails, grades, enrollments) and can write
submissions. They must never be anonymously reachable.
"""
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.db import models
from src.db.connection import get_db
from src.security.authorization import require_roles

router = APIRouter(
    prefix="/canvas",
    dependencies=[Depends(require_roles(models.UserRole.ADMIN))],
)

@router.get("/users/{user_id}")
def get_canvas_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "name": user.full_name,
        "email": user.email,
        "role": user.role
    }

@router.get("/courses")
def get_canvas_courses(db: Session = Depends(get_db)):
    courses = db.query(models.Course).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "course_code": c.code,
            "description": c.description
        } for c in courses
    ]

@router.get("/courses/{course_id}")
def get_canvas_course_detail(course_id: str, db: Session = Depends(get_db)):
    c = db.query(models.Course).filter_by(id=course_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")
    return {
        "id": c.id,
        "name": c.name,
        "course_code": c.code,
        "description": c.description
    }

@router.get("/courses/{course_id}/users")
def get_canvas_course_users(course_id: str, db: Session = Depends(get_db)):
    # Find enrollments in sections of this course
    users = db.query(models.User).join(models.Enrollment).join(models.CourseSection).filter(
        models.CourseSection.course_id == course_id
    ).all()
    return [
        {
            "id": u.id,
            "name": u.full_name,
            "email": u.email,
            "role": u.role
        } for u in users
    ]

@router.get("/courses/{course_id}/enrollments")
def get_canvas_course_enrollments(course_id: str, db: Session = Depends(get_db)):
    enrolls = db.query(models.Enrollment).join(models.CourseSection).filter(
        models.CourseSection.course_id == course_id
    ).all()
    return [
        {
            "id": e.id,
            "user_id": e.student_id,
            "course_id": course_id,
            "course_section_id": e.section_id,
            "enrollment_state": e.status.lower()
        } for e in enrolls
    ]

@router.get("/courses/{course_id}/modules")
def get_canvas_course_modules(course_id: str, db: Session = Depends(get_db)):
    mods = db.query(models.Module).join(models.CourseSection).filter(
        models.CourseSection.course_id == course_id
    ).all()
    return [
        {
            "id": m.id,
            "name": m.title,
            "position": m.sequence_order,
            "unlock_at": None
        } for m in mods
    ]

@router.get("/courses/{course_id}/assignments")
def get_canvas_course_assignments(course_id: str, db: Session = Depends(get_db)):
    assigns = db.query(models.Assignment).join(models.CourseSection).filter(
        models.CourseSection.course_id == course_id
    ).all()
    return [
        {
            "id": a.id,
            "name": a.title,
            "description": a.description,
            "due_at": a.due_date.isoformat(),
            "points_possible": a.max_points,
            "submission_types": ["online_url", "online_upload"]
        } for a in assigns
    ]

@router.get("/courses/{course_id}/assignments/{assignment_id}")
def get_canvas_assignment_detail(course_id: str, assignment_id: str, db: Session = Depends(get_db)):
    a = db.query(models.Assignment).filter_by(id=assignment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return {
        "id": a.id,
        "name": a.title,
        "description": a.description,
        "due_at": a.due_date.isoformat(),
        "points_possible": a.max_points
    }

@router.get("/courses/{course_id}/assignments/{assignment_id}/submissions")
def get_canvas_assignment_submissions(course_id: str, assignment_id: str, db: Session = Depends(get_db)):
    subs = db.query(models.Submission).filter_by(assignment_id=assignment_id).all()
    return [
        {
            "id": s.id,
            "assignment_id": s.assignment_id,
            "user_id": s.student_id,
            "submitted_at": s.submitted_at.isoformat(),
            "grade": s.grade,
            "late": s.is_late,
            "workflow_state": s.grading_status.lower()
        } for s in subs
    ]

@router.get("/courses/{course_id}/files")
def get_canvas_files(course_id: str, db: Session = Depends(get_db)):
    docs = db.query(models.Document).filter_by(course_id=course_id).all()
    return [
        {
            "id": d.id,
            "display_name": d.title,
            "url": d.file_path,
            "size": 1024,
            "created_at": datetime.now(UTC).isoformat()
        } for d in docs
    ]

@router.get("/courses/{course_id}/pages")
def get_canvas_pages(course_id: str, db: Session = Depends(get_db)):
    lessons = db.query(models.Lesson).join(models.Module).join(models.CourseSection).filter(
        models.CourseSection.course_id == course_id
    ).all()
    return [
        {
            "url": f"page_{lesson.id}",
            "title": lesson.title,
            "body": lesson.content,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        for lesson in lessons
    ]

@router.get("/courses/{course_id}/announcements")
def get_canvas_announcements(course_id: str, db: Session = Depends(get_db)):
    anns = db.query(models.Announcement).join(models.CourseSection).filter(
        models.CourseSection.course_id == course_id
    ).all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "message": a.content,
            "posted_at": a.created_at.isoformat()
        } for a in anns
    ]

@router.get("/calendar_events")
def get_canvas_calendar_events(db: Session = Depends(get_db)):
    events = db.query(models.CalendarEvent).all()
    return [
        {
            "id": ev.id,
            "title": ev.title,
            "start_at": ev.start_time.isoformat(),
            "end_at": ev.end_time.isoformat(),
            "description": ev.description
        } for ev in events
    ]

@router.get("/courses/{course_id}/quizzes")
def get_canvas_quizzes(course_id: str, db: Session = Depends(get_db)):
    quizzes = db.query(models.Quiz).join(models.CourseSection).filter(
        models.CourseSection.course_id == course_id
    ).all()
    return [
        {
            "id": q.id,
            "title": q.title,
            "due_at": q.due_date.isoformat(),
            "time_limit": q.time_limit_minutes,
            "points_possible": q.max_points
        } for q in quizzes
    ]

@router.post("/courses/{course_id}/assignments/{assignment_id}/submissions")
def create_canvas_submission(course_id: str, assignment_id: str, payload: dict, db: Session = Depends(get_db)):
    student_id = payload.get("student_id")
    content = payload.get("content", {})
    if not student_id:
        raise HTTPException(status_code=400, detail="student_id is required")

    sub = models.Submission(
        id=f"sub_api_{uuid.uuid4().hex[:6]}",
        assignment_id=assignment_id,
        quiz_id=None,
        student_id=student_id,
        submitted_at=datetime.now(UTC),
        content=content,
        grading_status="PENDING",
        grade=None,
        is_late=False
    )
    db.merge(sub)
    db.commit()
    return {
        "id": sub.id,
        "assignment_id": sub.assignment_id,
        "user_id": sub.student_id,
        "submitted_at": sub.submitted_at.isoformat(),
        "workflow_state": "submitted"
    }
