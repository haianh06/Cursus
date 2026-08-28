"""Admin and instructor APIs for institutional class schedules."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.security.authorization import require_roles
from src.services.academic.class_schedule_service import ClassScheduleService

admin_router = APIRouter(prefix="/admin/class-schedule", tags=["admin-class-schedule"], dependencies=[Depends(require_roles(models.UserRole.ADMIN))])
instructor_router = APIRouter(prefix="/instructor/class-schedule", tags=["instructor-class-schedule"], dependencies=[Depends(require_roles(models.UserRole.INSTRUCTOR))])
student_router = APIRouter(prefix="/student/class-schedule", tags=["student-class-schedule"], dependencies=[Depends(require_roles(models.UserRole.STUDENT))])


class SlotPayload(BaseModel):
    term_name: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=80)
    start_minute: int = Field(ge=0, le=1439)
    end_minute: int = Field(ge=1, le=1440)
    display_order: int = Field(ge=0)
    is_active: bool = True


class FixedSchedulePayload(BaseModel):
    section_id: str
    slot_id: str
    weekday: int = Field(ge=0, le=6)
    room: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=1000)
    effective_from: date
    effective_to: date


class ExceptionPayload(BaseModel):
    schedule_id: str | None = None
    section_id: str
    kind: str
    event_date: date
    start_minute: int = Field(ge=0, le=1439)
    end_minute: int = Field(ge=1, le=1440)
    room: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=1000)
    reason: str = Field(min_length=3, max_length=1000)


def _slot_out(slot: models.TermStudySlot) -> dict:
    return {"id": slot.id, "termName": slot.term_name, "name": slot.name, "startMinute": slot.start_minute, "endMinute": slot.end_minute, "displayOrder": slot.display_order, "isActive": slot.is_active}


def _section_or_404(db: Session, section_id: str, organization_id: str | None) -> models.CourseSection:
    row = db.query(models.CourseSection).join(models.Course).filter(
        models.CourseSection.id == section_id,
        (models.Course.organization_id.is_(None)) | (models.Course.organization_id == organization_id),
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="section_not_found")
    return row


@admin_router.get("/slots")
def list_slots(term_name: str, current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    rows = db.query(models.TermStudySlot).filter_by(organization_id=current_user.organization_id, term_name=term_name).order_by(models.TermStudySlot.display_order).all()
    return {"items": [_slot_out(row) for row in rows]}


@admin_router.post("/slots", status_code=status.HTTP_201_CREATED)
def create_slot(payload: SlotPayload, current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    if payload.end_minute <= payload.start_minute:
        raise HTTPException(status_code=400, detail="slot_end_must_be_after_start")
    row = models.TermStudySlot(id=f"slot_{uuid.uuid4().hex[:16]}", organization_id=current_user.organization_id, term_name=payload.term_name, name=payload.name, start_minute=payload.start_minute, end_minute=payload.end_minute, display_order=payload.display_order, is_active=payload.is_active)
    db.add(row); db.commit(); db.refresh(row)
    return _slot_out(row)


@admin_router.post("/fixed", status_code=status.HTTP_201_CREATED)
def create_fixed_schedule(payload: FixedSchedulePayload, current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    if payload.effective_to < payload.effective_from:
        raise HTTPException(status_code=400, detail="invalid_effective_range")
    _section_or_404(db, payload.section_id, current_user.organization_id)
    slot = db.query(models.TermStudySlot).filter_by(id=payload.slot_id, organization_id=current_user.organization_id).first()
    if not slot or not slot.is_active:
        raise HTTPException(status_code=404, detail="active_slot_not_found")
    conflict = db.query(models.FixedClassSchedule).filter(
        models.FixedClassSchedule.section_id == payload.section_id, models.FixedClassSchedule.weekday == payload.weekday,
        models.FixedClassSchedule.effective_from <= payload.effective_to, models.FixedClassSchedule.effective_to >= payload.effective_from,
        models.FixedClassSchedule.start_minute < slot.end_minute, models.FixedClassSchedule.end_minute > slot.start_minute,
    ).first()
    if conflict:
        raise HTTPException(status_code=409, detail="fixed_schedule_conflict")
    row = models.FixedClassSchedule(id=f"fixed_{uuid.uuid4().hex[:16]}", section_id=payload.section_id, slot_id=slot.id, weekday=payload.weekday, start_minute=slot.start_minute, end_minute=slot.end_minute, room=payload.room, note=payload.note, effective_from=payload.effective_from, effective_to=payload.effective_to, created_by=current_user.id)
    db.add(row); db.commit()
    return {"id": row.id}


@admin_router.get("/week")
def admin_week(section_id: str, week_start: date, current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    _section_or_404(db, section_id, current_user.organization_id)
    start = datetime.combine(week_start, time.min)
    meetings = ClassScheduleService(db)._meetings(section_ids=[section_id], start=start, end=start + timedelta(days=7))
    return {"items": [item.__dict__ | {"start": item.start.isoformat(), "end": item.end.isoformat()} for item in meetings]}


def _create_exception(payload: ExceptionPayload, actor: models.User, db: Session) -> dict:
    if payload.kind not in {"CANCELLED", "MAKEUP"} or payload.end_minute <= payload.start_minute:
        raise HTTPException(status_code=400, detail="invalid_schedule_exception")
    section = _section_or_404(db, payload.section_id, actor.organization_id)
    role = actor.role.value if isinstance(actor.role, models.UserRole) else actor.role
    if role == models.UserRole.INSTRUCTOR.value and section.instructor_id != actor.id:
        raise HTTPException(status_code=403, detail="section_not_assigned")
    if payload.kind == "CANCELLED" and not payload.schedule_id:
        raise HTTPException(status_code=400, detail="cancelled_requires_schedule")
    if payload.schedule_id:
        schedule = db.query(models.FixedClassSchedule).filter_by(id=payload.schedule_id, section_id=payload.section_id).first()
        if not schedule:
            raise HTTPException(status_code=404, detail="schedule_not_found")
    if payload.kind == "MAKEUP":
        start = datetime.combine(payload.event_date, time(hour=payload.start_minute // 60, minute=payload.start_minute % 60))
        end = datetime.combine(payload.event_date, time(hour=payload.end_minute // 60, minute=payload.end_minute % 60))
        try:
            ClassScheduleService(db).ensure_no_section_overlap(section_id=payload.section_id, start=start, end=end)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    row = models.ClassScheduleException(id=f"exception_{uuid.uuid4().hex[:16]}", **payload.model_dump(), created_by=actor.id)
    db.add(row); db.flush(); ClassScheduleService(db).notify_exception(row); db.commit()
    return {"id": row.id, "recipientCount": db.query(models.ClassScheduleNotification).filter_by(exception_id=row.id).count()}


@admin_router.post("/exceptions", status_code=status.HTTP_201_CREATED)
def admin_create_exception(payload: ExceptionPayload, current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    return _create_exception(payload, current_user, db)


@instructor_router.get("/week")
def instructor_week(week_start: date, current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    start = datetime.combine(week_start, time.min)
    meetings = ClassScheduleService(db).instructor_meetings(instructor_id=current_user.id, start=start, end=start + timedelta(days=7))
    return {"items": [item.__dict__ | {"start": item.start.isoformat(), "end": item.end.isoformat()} for item in meetings]}


@instructor_router.post("/exceptions", status_code=status.HTTP_201_CREATED)
def instructor_create_exception(payload: ExceptionPayload, current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    return _create_exception(payload, current_user, db)


@student_router.get("/notifications")
def student_notifications(current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    rows = db.query(models.ClassScheduleNotification).filter_by(recipient_id=current_user.id).order_by(models.ClassScheduleNotification.created_at.desc()).limit(50).all()
    return {"items": [{"id": row.id, "title": row.title, "body": row.body, "createdAt": row.created_at.isoformat(), "readAt": row.read_at.isoformat() if row.read_at else None} for row in rows]}
