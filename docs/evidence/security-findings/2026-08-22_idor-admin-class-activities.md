# IDOR — `GET /api/v1/admin/class-activities` missing cross-instructor ownership check

- **Status:** ✅ Fixed 22/08, same day as found. See bottom of this file for evidence.
- **Found by:** automated RBAC/IDOR sweep (general-purpose subagent) covering `src/api/instructor.py`, `student.py`, `companion.py`, `plans.py` (39/39 routes, all safe) plus a voluntary extended sweep of ~24 more routes across the rest of `src/api/`, specifically looking for the same bug shape as the already-fixed `GET /instructor/guardrail-reviews` issue (21/08).
- **Severity:** Medium. Not student PII/grades/chat — but it lets any authenticated INSTRUCTOR (or a cross-org instructor) read another instructor's class-activity log for a course they have no relationship to, directly violating mục 9 P0#2's literal requirement ("Lecturer A gọi API lấy dữ liệu lớp của Lecturer B phải trả 403") and mục 16.5's checklist ("không lecturer nào xem được lớp ngoài phạm vi").

## Route

`GET /api/v1/admin/class-activities?course_id=<X>` — `src/api/admin.py:749-763`, mounted on `academic_router` (`src/api/admin.py:717-721`), gated only by `dependencies=[require_roles(ADMIN, INSTRUCTOR)]` at the router level. Confirmed live (not disabled) via `src/main.py:7,92`.

## Root cause

The handler calls `AcademicTermService.list_class_activities(organization_id=current_user.organization_id, course_id=course_id)` (`src/services/academic/academic_term_service.py:198-203`), which only calls `_require_course(course_id, organization_id)` before listing. `_require_course` → `AcademicTermRepository.get_course` (`src/repositories/academic_term_repository.py:161-163`) doesn't even bound the lookup by `organization_id` (`del organization_id` in that path). `AcademicTermRepository.list_class_activities` (`:217-234`) filters only by `course_id` — no join back to `CourseSection.instructor_id` or `Enrollment` for the calling user.

The sibling **write** path, `POST /admin/class-activities` → `AcademicTermService.log_class_activity` (`academic_term_service.py:184-187`), DOES call `instructor_teaches_course(...)` and has a passing negative test (`test_instructor_cannot_log_activity_for_course_they_do_not_teach`). The **read** path never calls that same guard. Repo-wide grep confirms `instructor_teaches_course` has exactly one call site (the write path) — the read path was simply never wired to it. Same bug shape as the guardrail-reviews fix from 21/08: a list/read endpoint that checks role but not the instructor↔course relationship, sitting right next to a correctly-guarded write endpoint.

## Repro

Instructor A, teaching zero sections of course X, calls `GET /api/v1/admin/class-activities?course_id=X` with their own valid session/token → `200 OK` with the full activity log (`kind`, freeform `title` text, `created_by` instructor id, timestamps) for a class they have no relationship to.

## Test coverage before fix

None. `tests/` has a negative test for the POST path (`test_instructor_cannot_log_activity_for_course_they_do_not_teach`) but no equivalent for GET.

---

## Fix status

**Fixed 22/08.** `AcademicTermService.list_class_activities()` (`src/services/academic/academic_term_service.py:198-208`) now takes `instructor_id`/`role` and runs the exact same `instructor_teaches_course(...)` check the write path already had, raising `PermissionError` (mapped to `403` in `src/api/admin.py:749-767`) for a non-owning, non-admin instructor. The route now passes `current_user.id`/`current_user.role` through.

**Regression test:** `tests/test_api/test_academic_term_api.py::test_instructor_cannot_read_class_activities_for_course_they_do_not_teach` — an instructor who owns the course can read the log (200, 1 entry); an instructor with zero relationship to it gets 403, not the data.

**pytest evidence:** `docs/evidence/test-runs/20260822-0100-p0-fix-idor-class-activities.xml` — full suite, 393 passed (was 392 before this fix's new test), 7 skipped, 0 failed.
