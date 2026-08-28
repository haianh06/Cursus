"""Idempotent Cursus Uni demo schedule seed; never deletes curriculum/documents."""
from __future__ import annotations

import os, sys, uuid
from datetime import date

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.connection import SessionLocal
from src.db.models import (ClassScheduleException, Course, CourseSection, Enrollment,
    EnrollmentStatus, FixedClassSchedule, Organization, OrganizationMembership,
    TermStudySlot, User, UserRole)
from src.security.passwords import hash_password
from src.services.academic.class_schedule_service import ClassScheduleService

ORG_SLUG = "fpt-university"; TERM = "Fall2026"; START = date(2026, 8, 10); END = date(2026, 10, 18)
COURSES = {"CSI106": "Computer Organization", "CEA201": "Computer Architecture", "PRF192": "Programming Fundamentals", "PRO192": "Object-Oriented Programming"}
COHORTS = ("SE2001", "SE2002", "SE2003")
SLOT_DATA = (("Ca 1", 480, 600, 1), ("Ca 2", 615, 735, 2), ("Ca 3", 780, 900, 3), ("Ca 4", 915, 1035, 4))

def get_or_make(db, model, defaults=None, **filters):
    row = db.query(model).filter_by(**filters).first()
    if row: return row
    row = model(**filters, **(defaults or {})); db.add(row); db.flush(); return row

def main():
    db = SessionLocal()
    try:
        org = db.query(Organization).filter_by(slug=ORG_SLUG).first()
        if not org: raise RuntimeError("Run organization migration/seed first; fpt-university is missing.")
        instructor = get_or_make(db, User, dict(id="inst_nguyen_duc_chung", full_name="Nguyễn Đức Chung", role=UserRole.INSTRUCTOR.value, password_hash=hash_password("password123"), organization_id=org.id, is_email_verified=True), email="nguyen.ducchung@cursus.demo")
        get_or_make(db, OrganizationMembership, dict(id=f"orgmem_{uuid.uuid4().hex}", role=UserRole.INSTRUCTOR.value), user_id=instructor.id, organization_id=org.id)
        courses = {code: get_or_make(db, Course, dict(id=code, name=name, description=f"Demo {name}", organization_id=org.id), code=code) for code, name in COURSES.items()}
        slots = []
        for name, begin, end, order in SLOT_DATA:
            slots.append(get_or_make(db, TermStudySlot, dict(id=f"slot_{TERM}_{order}", start_minute=begin, end_minute=end, display_order=order, is_active=True), organization_id=org.id, term_name=TERM, name=name))
        students = []
        for idx in range(1, 61):
            student = get_or_make(db, User, dict(id=f"student_se20_{idx:02d}", full_name=f"Sinh viên Demo {idx:02d}", role=UserRole.STUDENT.value, password_hash=hash_password("password123"), organization_id=org.id, is_email_verified=True), email=f"student{idx:02d}@cursus.demo")
            get_or_make(db, OrganizationMembership, dict(id=f"orgmem_{uuid.uuid4().hex}", role=UserRole.STUDENT.value), user_id=student.id, organization_id=org.id)
            students.append(student)
        exceptions = []
        for cohort_index, cohort in enumerate(COHORTS):
            cohort_students = students[cohort_index * 20:(cohort_index + 1) * 20]
            for course_index, (code, course) in enumerate(courses.items()):
                section = get_or_make(db, CourseSection, dict(id=f"section_{cohort}_{code}", instructor_id=instructor.id if code == "CEA201" else None), course_id=course.id, section_code=cohort, term=TERM)
                for student in cohort_students:
                    get_or_make(db, Enrollment, dict(id=f"enroll_{section.id}_{student.id}", status=EnrollmentStatus.ENROLLED.value), student_id=student.id, section_id=section.id)
                slot = slots[(cohort_index + course_index) % len(slots)]
                weekday = (course_index * 2 + cohort_index) % 5
                schedule = get_or_make(db, FixedClassSchedule, dict(id=f"fixed_{section.id}", slot_id=slot.id, weekday=weekday, start_minute=slot.start_minute, end_minute=slot.end_minute, room=f"A{101 + cohort_index}", effective_from=START, effective_to=END, created_by=instructor.id), section_id=section.id)
                if code == "CEA201" and cohort == "SE2001": exceptions.append(schedule)
        schedule = exceptions[0]
        exception = db.query(ClassScheduleException).filter_by(schedule_id=schedule.id, event_date=date(2026, 8, 24), kind="CANCELLED").first()
        if not exception:
            exception = ClassScheduleException(id="exception_demo_cea201", schedule_id=schedule.id, section_id=schedule.section_id, kind="CANCELLED", event_date=date(2026, 8, 24), start_minute=schedule.start_minute, end_minute=schedule.end_minute, reason="Giảng viên tham gia hội thảo chuyên môn.", created_by=instructor.id)
            db.add(exception); db.flush(); ClassScheduleService(db).notify_exception(exception)
        db.commit(); print("Seeded 60 students, 3 cohorts, 12 sections and demo CEA201 cancellation.")
    except Exception:
        db.rollback(); raise
    finally: db.close()

if __name__ == "__main__": main()
