"""Read API for curriculum/syllabus content — see app/models.py's Syllabus /
CurriculumProgram / PrerequisiteNode and scripts/seed_curriculum.py for where
this data comes from. Session-cookie authenticated (require_identity_json),
same as the rest of app/web.py's /web-api/* surface: never called by Cursus,
only by this app's own SPA.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CurriculumProgram, PrerequisiteNode, Syllabus
from app.sso import require_identity_json

router = APIRouter(prefix="/web-api", tags=["curriculum"])


def _syllabus_summary(row: Syllabus) -> dict:
    return {
        "syllabusId": row.syllabus_id,
        "syllabusName": row.syllabus_name,
        "courseNameEnglish": row.course_name_english,
        "subjectCode": row.subject_code,
        "learningTeachingMethod": row.learning_teaching_method,
        "noCredit": row.no_credit,
        "preRequisite": row.pre_requisite,
        "decisionNo": row.decision_no,
        "isActive": row.is_active,
        "sessionCount": len(row.sessions or []),
        "questionCount": len(row.questions or []),
        "cloCount": len(row.clos or []),
    }


def _syllabus_detail(row: Syllabus) -> dict:
    return {
        "metadata": {
            "syllabusId": row.syllabus_id,
            "syllabusName": row.syllabus_name,
            "courseNameEnglish": row.course_name_english,
            "subjectCode": row.subject_code,
            "learningTeachingMethod": row.learning_teaching_method,
            "noCredit": row.no_credit,
            "degreeLevel": row.degree_level,
            "timeAllocation": row.time_allocation,
            "preRequisite": row.pre_requisite,
            "description": row.description,
            "studentTasks": row.student_tasks,
            "tools": row.tools,
            "scoringScale": row.scoring_scale,
            "decisionNo": row.decision_no,
            "approvedDate": row.approved_date,
            "isActive": row.is_active,
            "isApproved": row.is_approved,
        },
        "materials": row.materials or [],
        "clos": row.clos or [],
        "sessions": row.sessions or [],
        "questions": row.questions or [],
        "assessments": row.assessments or [],
    }


@router.get("/syllabi")
def list_syllabi(
    q: str | None = None,
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_identity_json),
):
    """Search across the subjects that actually have full syllabus detail
    seeded — deliberately NOT every course in the catalog, so a result here
    never links to a detail page with nothing behind it."""
    rows = db.scalars(select(Syllabus).order_by(Syllabus.subject_code)).all()
    if q:
        needle = q.strip().lower()
        rows = [
            r
            for r in rows
            if needle in r.subject_code.lower()
            or needle in r.course_name_english.lower()
            or needle in r.syllabus_name.lower()
        ]
    return [_syllabus_summary(r) for r in rows]


@router.get("/syllabi/{code}")
def get_syllabus(
    code: str,
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_identity_json),
):
    row = db.get(Syllabus, code)
    if not row:
        raise HTTPException(status_code=404, detail="syllabus_not_found")
    return _syllabus_detail(row)


@router.get("/curriculum-programs")
def list_curriculum_programs(
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_identity_json),
):
    rows = db.scalars(select(CurriculumProgram).order_by(CurriculumProgram.code)).all()
    return [
        {
            "code": r.code,
            "name": r.name,
            "totalCredits": r.total_credits,
            "semesterCount": len(r.semesters or []),
        }
        for r in rows
    ]


@router.get("/curriculum-programs/{code}")
def get_curriculum_program(
    code: str,
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_identity_json),
):
    row = db.get(CurriculumProgram, code)
    if not row:
        raise HTTPException(status_code=404, detail="program_not_found")
    return {
        "code": row.code,
        "name": row.name,
        "faculty": row.faculty,
        "decisionNo": row.decision_no,
        "effectiveYear": row.effective_year,
        "totalCredits": row.total_credits,
        "description": row.description,
        "semesters": row.semesters or [],
    }


@router.get("/prerequisites")
def list_prerequisites(
    db: Session = Depends(get_db),
    _identity: dict = Depends(require_identity_json),
):
    rows = db.scalars(select(PrerequisiteNode).order_by(PrerequisiteNode.semester, PrerequisiteNode.code)).all()
    return [
        {
            "code": r.code,
            "name": r.name,
            "semester": r.semester,
            "credits": r.credits,
            "category": r.category,
            "prerequisites": r.prerequisites or [],
            "isPrerequisiteOf": r.is_prerequisite_of or [],
        }
        for r in rows
    ]
