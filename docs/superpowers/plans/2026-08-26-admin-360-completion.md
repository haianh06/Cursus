# Admin 360 Completion Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with test-first checkpoints.

**Goal:** Hoàn tất luồng Admin 360 bằng cách bổ sung tab phiên tự học, giữ audit-before-release cho mọi dữ liệu raw nhạy cảm và xác nhận toàn bộ quyền truy cập bằng test tích hợp.

**Architecture:** Tái sử dụng `admin_student360.py` và helper `_audited_read`, không tạo service hoặc bảng mới vì `SelfStudySession` và migration đã tồn tại. Frontend chỉ thêm resource vào cấu hình tab hiện có; Instructor 360 tiếp tục aggregate-only, không mở đường dẫn xuống dữ liệu từng sinh viên.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, Vite, pytest, Ruff, Docker Compose.

**Spec:** `docs/archive/SPEC_ADMIN_REBUILD_TU_CHUNG_23AUG.md` mục 3.3–3.4 và `docs/branch-audit/chung-admin-backend.md` mục 2.2.

## Global Constraints

- Không trả raw data Student 360 trước khi `ADMIN_SENSITIVE_READ` được ghi và commit thành công.
- Mọi raw route phải kiểm tra `Permission.READ_SENSITIVE` theo đúng resource.
- Không thêm migration/bảng mới; dùng bảng `self_study_sessions` đã có trong `20260902_student_role_restore`.
- Instructor 360 chỉ trả số liệu tổng hợp, không trả dữ liệu sinh viên cụ thể.
- Giữ tương thích các route Student 360 hiện có và không thay đổi luồng Admin đã hoàn thiện.

---

### Task 1: Add the missing Student 360 self-study sessions route

**Files:**
- Modify: `src/api/admin_student360.py`
- Test: `tests/test_api/test_admin_student360.py`

**Interfaces:**
- Consumes: `models.SelfStudySession`, `models.User`, `_require_student`, `_audited_read`.
- Produces: `GET /api/v1/admin/students/{student_id}/sessions` returning audited session rows with `id`, `title`, `plannedMinutes`, `startedAt`, `scheduledEndAt`, `endedAt`, `actualMinutes`, `pomodorosCompleted`, `status`.

- [x] Write a failing API test that requests `/sessions`, asserts HTTP 200 for Admin, checks the response shape and verifies an `ADMIN_SENSITIVE_READ` event with resource `SELF_STUDY_SESSION`.
- [x] Run the single test and confirm it fails because the route is missing.
- [x] Add the route with `Permission.READ_SENSITIVE`, filter by `student_id`, paginate by `started_at`, serialize datetimes, then release rows only through `_audited_read`.
- [x] Run the test again and confirm it passes.

### Task 2: Expose sessions in the Student 360 UI

**Files:**
- Modify: `frontend/src/components/admin/adminSensitiveResources.js`
- Modify: `frontend/src/components/admin/AdminStudent360.jsx`
- Modify: `frontend/src/lib/api.js` only if the generic resource helper does not cover `sessions`.

**Interfaces:**
- Consumes: generic `readAdminStudentResource`, the new `/sessions` route and `describeAdminRawItem`.
- Produces: a visible “Phiên tự học / Self-study sessions” tab with loading, empty, error and audited-data states.

- [x] Add `sessions` to the existing raw resource map and labels for all returned fields.
- [x] Add the tab label in Vietnamese and English while preserving all existing tab keys.
- [x] Run frontend lint and build to catch missing fields/imports.

### Task 3: Audit and permission regression coverage

**Files:**
- Modify: `tests/test_api/test_admin_student360.py`
- Modify: `tests/test_security/test_permissions.py` only if the new resource is absent from the Admin sensitive permission matrix.

**Interfaces:**
- Consumes: the new sessions route and existing `AuditRepository` failure behavior.
- Produces: tests proving Admin access, Student/Instructor denial, org-scoped 404 and fail-closed audit behavior.

- [x] Confirm the existing permission-matrix tests deny non-Admin access to every Admin Student 360 route, including sessions.
- [x] Add a test that an audit insert failure returns 503 and does not return session rows.
- [x] Run all Student 360 and permission tests; fix only the implementation if a regression appears.

### Task 4: Full verification and staging smoke

**Files:**
- No production file changes unless verification reveals a concrete defect.

- [x] Run Admin API tests, Student 360 tests, Ruff and `git diff --check`.
- [x] Run frontend lint and Vite build.
- [x] Rebuild/restart backend and frontend containers.
- [x] Verify Docker health and `/health` endpoint.
- [x] Record any remaining limitation: analytics measurement status, mock curriculum data or uncommitted worktree changes.
