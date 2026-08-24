# Tài liệu siêu chi tiết — Backend Admin Console (nhánh `chung`)

> Nguồn: worktree `D:\VINAI_Team_093\P-093-chung-worktree` (checkout riêng của nhánh `chung`).
> Mục tiêu: mô tả đầy đủ logic backend phần Admin để một AI khác có thể viết lại (vibe-code) y hệt trên nhánh `develop` mà **không cần đọc lại source gốc**.
> Ngôn ngữ: tiếng Việt. Tất cả tên hàm/route/model/exception giữ nguyên bản tiếng Anh (identifier) để tránh sai lệch khi implement lại.

---

## 1. Tổng quan kiến trúc Admin backend

### 1.1 Sơ đồ thư mục liên quan

```
src/
  api/
    admin.py                     # Router "/admin": courses, guardrail rules, analytics, curriculum docs, academic-term
    admin_invitations.py         # Router "/admin/invites": mời Student/Instructor
    admin_observability.py       # Router "/admin": overview, people explorer, student/instructor 360, raw T2 reads
    admin_observability_schemas.py  # Pydantic schemas cho router trên
    admin_policy.py              # Router "/admin/risk-policy": risk policy CRUD + preview/rollback
    admin_policy_schemas.py      # Schemas risk-policy + admin-settings
    admin_schemas.py             # Schemas dùng chung: courses, guardrail rules, documents, users, invitations
    admin_settings.py            # Router "/admin/settings": auto_risk_alert, default_semester
    admin_users.py               # Router "/admin/users": list users, set active/inactive, đổi role+scope
    data_requests.py             # (KHÔNG có tiền tố admin_ nhưng chứa route "/admin/data-requests/*")
  services/
    admin_account_service.py             # Bootstrap + ràng buộc "chỉ 1 tài khoản ADMIN"
    admin_account_recovery_service.py    # Recovery tài khoản ADMIN qua kênh OPS (không qua API HTTP, dùng script)
    admin_data_request_service.py        # Business logic DSAR (access/export/correction/deletion) cho Admin
    admin_document_ingest_service.py     # Ingest/replace/delete tài liệu curriculum do Admin upload
    admin_document_lifecycle_service.py  # validate -> publish -> archive -> rollback tài liệu
    admin_document_serializer.py         # Chuẩn hoá 1 Document ORM -> dict response
    admin_ingest_runner.py               # BackgroundTasks worker chạy ingest/replace/delete bất đồng bộ
    admin_observability_read_service.py  # ADM-09 (overview/people/360) + ADM-10 (T2 raw reads) DTO builder
    admin_people_service.py              # Đổi role + class-scope (Student <-> Instructor) có transfer-safety
    admin_read_service.py                # Danh sách courses hợp nhất từ catalog + override + ingest job
    admin_work_queue_service.py          # Xây dựng Work Queue (risk/safety/data-request/ingest) cho Overview
  repositories/
    admin_course_repository.py           # CRUD AdminCourseOverride + CourseIngestJob
    admin_observability_repository.py    # Query T0/T1 (đếm/aggregat) + T2 (raw, bounded, phân trang) cho observability
  db/models.py                           # ORM models liên quan (User, Invitation, Document, RiskPolicy, GuardrailRule, ...)
  security/
    authorization.py                     # require_roles(), require_permission() — 2 lớp guard FastAPI
    permissions.py                       # Enum Permission/Resource + PERMISSION_MATRIX (RBAC tĩnh)
    policy.py                            # is_allowed(role, resource, permission)
    sensitive_access.py                  # SensitiveAccessContext + các exception T2
  services/sensitive_read_executor.py    # Cổng duy nhất để trả dữ liệu "sensitive" (T2), audit-before-release
migrations/versions/                     # 21 file, ~15 file liên quan Admin (xem mục 4)
```

### 1.2 Luồng request điển hình

Một request Admin đi qua đúng 3 lớp gate theo thứ tự, không có lớp thứ 4:

1. **Router-level RBAC**: mọi router Admin khai báo `dependencies=[Depends(require_roles(UserRole.ADMIN))]` ngay trên `APIRouter(...)`. Không phải ADMIN → HTTP 403 ngay từ đây (401 nếu chưa đăng nhập, vì `get_current_user_from_token` chạy trước).
2. **Route-level permission**: từng route còn khai báo thêm `dependencies=[Depends(require_permission(Resource.X, Permission.Y))]`. `is_allowed()` tra `PERMISSION_MATRIX[UserRole.ADMIN][Resource.X]` xem có chứa `Permission.Y` không (MANAGE là superset của READ/WRITE/DELETE/APPROVE/MANAGE).
3. **Service/repository logic**: sau khi qua 2 gate trên, handler gọi service (business rule, validate, side-effect) → repository (SQL) → commit/rollback thủ công (không dùng middleware transaction).

Điểm đặc biệt của thiết kế:
- **Không có "Admin Case" hay "TOTP session"** đứng chắn thêm cho các route đọc dữ liệu nhạy cảm (T2) — comment trong code nói rõ: "Two gates stand in front of every route below... There is no third gate". Đây là một thay đổi kiến trúc so với các bản trước (từng có `AdminAccessCase`/`SensitiveAccessSession`/TOTP — bảng này **vẫn tồn tại trong migration/model nhưng không còn được dùng bởi route T2 hiện tại**, xem mục 7).
- **Audit-before-release**: với các route đọc dữ liệu định danh (T1: `/people`, `/students/{id}/summary`, `/instructors/{id}/summary`) và dữ liệu thô (T2: `/students/{id}/plans`, `/tasks`, ...), service phải **commit được audit event trước khi trả response**. Nếu audit-log insert thất bại → toàn bộ dữ liệu đã load bị huỷ, trả lỗi 503 (`SensitiveAuditUnavailableError` / fail-closed). Đây là cơ chế `SensitiveReadExecutor.execute()`.
- **Mọi mutation ghi Audit Log qua `AuditService(AuditRepository(db)).log_event(...)`** với `commit=False` (gộp vào transaction chính), rồi handler tự `db.commit()`. Nếu lỗi ở bất kỳ bước nào → `db.rollback()` trong khối `except Exception: raise`.
- **change_reason bắt buộc** cho hầu hết các mutation quan trọng: guardrail toggle, guardrail restore/rollback, risk-policy publish/rollback, admin settings update, user status/access change, curriculum publish/archive/rollback. Schema `ChangeReason` (xem `src/api/schema_types.py`, không đọc chi tiết ở đây nhưng dùng lặp lại khắp nơi — độ dài tối thiểu là ràng buộc Pydantic).

---

## 2. Danh sách đầy đủ endpoint theo router file

Ghi chú chung: mọi response bọc trong `{"success": true, "data": {...}}`. Router-level dependency luôn là `require_roles(UserRole.ADMIN)` (401 nếu không login, 403 nếu không phải ADMIN) — bảng dưới đây chỉ liệt kê thêm **permission cụ thể của route**.

### 2.1 `src/api/admin.py` — prefix `/admin` (mount tại `/api/v1/admin`)

| Method | Path | Permission | Mục đích | Lỗi chính |
|---|---|---|---|---|
| GET | `/admin/courses` | `COURSE:READ` | Liệt kê course (hợp nhất catalog + override + ingest status); trước đó tự động fail các ingest job "processing" quá 1800s | 503 nếu catalog curriculum lỗi (`AdminDataUnavailable`) |
| GET | `/admin/guardrail-rules` | `AI_POLICY:READ` | Liệt kê 6 guardrail rule + trạng thái enable, version chính sách hiện hành | — |
| GET | `/admin/guardrail-rules/history` | `AI_POLICY:READ` | Lịch sử các `GuardrailPolicyVersion` | — |
| POST | `/admin/guardrail-rules/{code}/preview` | `AI_POLICY:WRITE` | Xem trước ảnh hưởng khi bật/tắt 1 rule (không ghi DB, luôn rollback) | 409 nếu rule là core-locked và đang tắt (`CoreGuardrailLockedError`); 404 nếu code không tồn tại |
| PATCH | `/admin/guardrail-rules/{code}` | `AI_POLICY:WRITE` | Bật/tắt 1 guardrail rule, publish version chính sách mới, ghi audit `guardrail_rule_updated` | 409 core-locked; 404 unknown rule |
| POST | `/admin/guardrail-rules/restore-defaults` | `AI_POLICY:APPROVE` | Bật lại tất cả rule mặc định (enabled=True hết), publish version mới | — |
| POST | `/admin/guardrail-rules/versions/{policy_version}/rollback` | `AI_POLICY:APPROVE` | Rollback về 1 policy version cũ, publish version mới kế thừa snapshot đó (status 201) | 409 core-locked (nếu source snapshot vi phạm); 404 version không tồn tại |
| GET | `/admin/analytics/summary` | `KPI:READ` | Tổng hợp: at_risk_students (distinct student có RiskSignal MEDIUM/HIGH chưa resolve), ingested_courses, total_courses, total_documents/chunks (chỉ đếm nguồn admin_curriculum/mock/mock_lms) | 503 nếu catalog lỗi |
| POST | `/admin/courses` | `COURSE:WRITE` | Thêm 1 course mới vào `AdminCourseOverride` (is_added=True) (status 201) | 409 nếu code đã tồn tại trong catalog/override/DB |
| DELETE | `/admin/courses/{code}` | `COURSE:DELETE` | "Ẩn" course (tạo/patch override `hidden=True`), KHÔNG xoá dữ liệu | 404 nếu không tìm thấy course |
| POST | `/admin/courses/{code}/restore` | `COURSE:WRITE` | Bỏ ẩn course (nếu override do catalog bị hide thì xoá override; nếu override do Admin add thì set hidden=False) | 404 nếu override không tồn tại |
| GET | `/admin/courses/{code}/documents` | `CURRICULUM:READ` | Liệt kê document "readable curriculum" (nguồn admin_curriculum/mock/mock_lms) của 1 course | 404 course ẩn/không tồn tại |
| GET | `/admin/courses/{code}/documents/{document_id}/content` | `CURRICULUM:READ` | Đọc nội dung UTF-8 gốc của 1 document | 404 document/nội dung không đọc được |
| POST | `/admin/courses/{code}/documents` | `CURRICULUM:WRITE` | Upload file mới (.md/.txt, ≤2MB), tạo `CourseIngestJob` (status=processing), chạy `run_admin_ingest_job` qua BackgroundTasks (status 202) | 400 nếu file sai định dạng/rỗng/quá lớn/không phải UTF-8 |
| PUT | `/admin/courses/{code}/documents/{document_id}` | `CURRICULUM:WRITE` | Thay thế (tạo version mới) 1 document Admin-owned (status 202, async) | 400 file invalid; 404 document không thuộc Admin |
| DELETE | `/admin/courses/{code}/documents/{document_id}` | `CURRICULUM:DELETE` | Xoá document Admin-owned (status 202, async: unlink file job DB) | 404 not found; 409 nếu đang PUBLISHED/ARCHIVED hoặc có version phụ thuộc |
| POST | `/admin/ingest-jobs/{job_id}/retry-cleanup` | `CURRICULUM:DELETE` | Retry dọn file vật lý khi job "delete" thất bại giữa chừng (status 202) | 404 job not found; 409 nếu job không ở trạng thái "failed" hoặc không phải delete-cleanup-pending |
| POST | `/admin/courses/{code}/documents/{document_id}/validate` | `CURRICULUM:WRITE` | Tính lại validation snapshot (checksum, chunk limit, provenance...) đồng bộ | 409 nếu document đã PUBLISHED/ARCHIVED; 404 not found |
| POST | `/admin/courses/{code}/documents/{document_id}/publish` | `CURRICULUM:APPROVE` | Publish 1 document READY_FOR_REVIEW, tự archive bản đang PUBLISHED cùng version_group | 409 nếu đã published hoặc chưa READY_FOR_REVIEW hoặc conflict đồng thời; 404 not found |
| POST | `/admin/courses/{code}/documents/{document_id}/archive` | `CURRICULUM:APPROVE` | Archive 1 document (không cho archive lại doc đã archived) | 409 already archived; 404 not found |
| POST | `/admin/courses/{code}/documents/{document_id}/rollback` | `CURRICULUM:APPROVE` | Tạo 1 document PUBLISHED mới clone nội dung + chunk từ 1 bản ARCHIVED, archive bản đang active | 409 nhiều điều kiện validate (xem mục 3.4); 404 not found |
| GET | `/admin/courses/{code}/documents/{document_id}/versions` | `CURRICULUM:READ` | Liệt kê tất cả version trong version_group, sắp xếp mới nhất trước (theo version numeric) | 404 not found |
| GET | `/admin/academic-term` | `COURSE:READ` | Lấy academic term đang active (có thể null) | — |
| PUT | `/admin/academic-term` | `COURSE:WRITE` | Upsert academic term | 400 ValueError từ service |
| GET | `/admin/academic-term/exams` | `COURSE:READ` | Liệt kê kỳ thi | 404 LookupError |
| PUT | `/admin/academic-term/exams` | `COURSE:WRITE` | Upsert 1 kỳ thi (course_id + kind + sessions[]) | 404 LookupError; 400 ValueError |
| DELETE | `/admin/academic-term/exams/{exam_id}` | `COURSE:DELETE` | Xoá 1 kỳ thi (204 No Content) | 404 LookupError |

Lưu ý: academic-term/exams dùng `AcademicTermService`/`AcademicTermRepository` — không thuộc phạm vi "admin_*" module nhưng được mount trong cùng router `admin.py`. Không nằm sâu trong phạm vi audit này (không đọc source `academic_term_service.py`).

### 2.2 `src/api/admin_invitations.py` — prefix `/admin/invites`

| Method | Path | Permission | Mục đích | Lỗi chính |
|---|---|---|---|---|
| GET | `` (`/admin/invites`) | (chỉ role ADMIN, không thêm permission riêng) | Liệt kê tất cả invitation, tính `status` runtime (pending quá hạn → "expired") | — |
| POST | `` | `USER:MANAGE` | Tạo invitation (chỉ role STUDENT/INSTRUCTOR), gửi email nếu `settings.email_provider == "smtp"` (status 201) | 400 role không hợp lệ / class không hợp lệ / instructor thiếu class; 409 nếu đã có pending invite cùng email |
| POST | `/{invitation_id}/revoke` | `USER:MANAGE` | Revoke 1 invitation pending | 404 not found; 409 nếu không còn pending |
| POST | `/{invitation_id}/resend` | `USER:MANAGE` | Tạo lại token mới (rotate), gửi lại email | 404 not found; 409 nếu không pending / mất pending giữa race |
| PATCH | `/{invitation_id}` | `USER:MANAGE` | Sửa `class_ids` của invitation đang pending | 404 not found; 409 not pending; 400 instructor thiếu class |

Chi tiết business rule quan trọng:
- `role` chuẩn hoá `.strip().upper()`, chỉ chấp nhận `STUDENT`/`INSTRUCTOR`.
- `class_ids` được resolve qua `_resolve_class_ids()`: chấp nhận cả `CourseSection.id` lẫn `section_code`; nếu 1 identifier match 0 hoặc >1 section → HTTP 400 "Unknown or ambiguous classes".
- Instructor invitation **bắt buộc** có ít nhất 1 class_id.
- Token: `secrets.token_urlsafe(32)` raw, lưu `hashlib.sha256(...).hexdigest()` — **raw token chỉ trả về 1 lần trong response** (`activation_token`), không lưu plaintext.
- Gửi email: `delivery_status` ∈ {"sent", "disabled", "failed"}. Nếu `email_provider != "smtp"` → "disabled" (không gọi API email nào). Nếu gửi lỗi → catch exception, log, `delivery_status="failed"`, `last_delivery_error = "EMAIL_DELIVERY_FAILED:{ExceptionClassName}"[:255]` (không log chi tiết exception message ra field DB — tránh leak).
- `_deliver_and_persist()` commit riêng biệt sau khi gửi email (tách với transaction tạo invitation).

### 2.3 `src/api/admin_observability.py` — prefix `/admin` (T0/T1/T2 observability)

Router-level: `require_roles(UserRole.ADMIN)`. Có 2 nhóm permission dependency dùng lại nhiều lần:
- `_PEOPLE_READ = require_permission(Resource.USER, Permission.MANAGE)` — dùng cho `/people`, `/students/{id}/summary`, `/instructors/{id}/summary` (T0/T1: identified nhưng không phải nội dung thô).
- `_sensitive(resource, permission=READ_SENSITIVE)` — dùng cho các route T2 raw-read.

| Method | Path | Permission | Tier | Mục đích | Lỗi |
|---|---|---|---|---|---|
| GET | `/admin/overview` | `RISK_CASE:READ_SENSITIVE` | T0 | Dashboard tổng quan: work queue, school pulse (active students/instructors, courses, sections, unresolved_risk rate, invitation_activation rate), recent_critical_changes (10 audit log events gần nhất trong whitelist sự kiện) | 503 nếu audit fail (không áp dụng trực tiếp ở route này vì build_overview không tự audit) |
| GET | `/admin/people` | `USER:MANAGE` | T1 | Danh sách người dùng có filter (search/role/is_active/course_id/section_id), phân trang, kèm `academic_summary` (enrollments/unresolved_risks cho Student, sections cho Instructor). Ghi audit `ADMIN_IDENTIFIED_READ` trước khi trả | 503 nếu audit không commit được |
| GET | `/admin/students/{student_id}/summary` | `USER:MANAGE` | T1 | 360 view 1 student: identity, enrollments, activity (đếm), risk_summary | 404 nếu id không tồn tại hoặc không phải STUDENT |
| GET | `/admin/instructors/{instructor_id}/summary` | `USER:MANAGE` | T1 | 360 view 1 instructor: identity, sections, roster, risk_workload, interventions (đếm) | 404 tương tự |
| GET | `/admin/students/{student_id}/plans` | `PLAN:READ_SENSITIVE` | T2 | Weekly plans + daily plans + schedule blocks + replan proposals + learning goals (raw, phân trang) | 404 subject not found; 422 nếu activity window quá rộng (route này không dùng window nhưng class check chung); 503 audit fail |
| GET | `/admin/students/{student_id}/tasks` | `PLAN:READ_SENSITIVE` | T2 | StudyTask + thời điểm bắt đầu block | như trên |
| GET | `/admin/students/{student_id}/progress-events` | `PLAN:READ_SENSITIVE` | T2 | ProgressEvent, hỗ trợ filter `from_time`/`to_time` | 422 nếu `to_time - from_time > 90 ngày` (`ActivityWindowTooWideError`) |
| GET | `/admin/students/{student_id}/reminders` | `PLAN:READ_SENSITIVE` | T2 | Reminder + ReminderDelivery lồng nhau | như trên |
| GET | `/admin/students/{student_id}/assignments` | `ASSIGNMENT:READ` | T2 | Assignment definition của các section student đang enroll (không dropped) | như trên |
| GET | `/admin/students/{student_id}/submissions` | `SUBMISSION:READ_SENSITIVE` | T2 | Submission | như trên |
| GET | `/admin/students/{student_id}/reflections` | `REFLECTION:READ_SENSITIVE` | T2 | WeeklyReflection (bao gồm `content` raw) | như trên |
| GET | `/admin/students/{student_id}/conversations` | `CHAT:READ_SENSITIVE` | T2 | Danh sách conversation + message_count | như trên |
| GET | `/admin/students/{student_id}/conversations/{conversation_id}` | `CHAT:READ_SENSITIVE` | T2 | Chi tiết 1 conversation + messages (kèm RAGTrace, LLMUsageEvent, GuardrailEvent lồng theo message) | 404 nếu conversation không thuộc student (`SensitiveRecordNotFoundError`) |
| GET | `/admin/students/{student_id}/documents` | `STUDENT_DOCUMENT:READ_SENSITIVE` | T2 | Document STUDENT_PRIVATE của học sinh (theo `provenance_info.uploaded_by`) + chunks | như trên |
| GET | `/admin/students/{student_id}/risk` | `RISK_CASE:READ_SENSITIVE` | T2 | RiskSignal raw | như trên |
| GET | `/admin/students/{student_id}/interventions` | `INTERVENTION:READ_SENSITIVE` | T2 | InstructorIntervention + risk_type join | như trên |
| GET | `/admin/students/{student_id}/sessions` | `SESSION:READ_SENSITIVE` | T2 | SelfStudySession | như trên |

Query params chung cho mọi route T2 (qua dependency class `AdminRawRead`):
- `page: int = 1 (ge=1)`, `page_size: int = 25 (ge=1, le=100)`.
- `from_time`, `to_time`: `datetime | None` (chỉ progress-events thực sự dùng để lọc, còn lại vẫn nhận nhưng chỉ đưa vào audit metadata).
- Response header luôn set `Cache-Control: no-store`.
- Mọi route T2 gọi `_require_student()` trước (404 nếu id không tồn tại hoặc role khác STUDENT — cùng thông báo lỗi để không lộ role thật).
- Audit: `SensitiveReadExecutor.execute()` — load dữ liệu (`loader()` chạy TRƯỚC), sau đó cố gắng ghi 1 audit event `ADMIN_SENSITIVE_READ` per-request (không phải per-record) kèm `resource_count`, `page`, `page_size`, `from_time`, `to_time`. Nếu audit insert lỗi → rollback, raise `SensitiveAuditUnavailableError` → HTTP 503. Dữ liệu đã load **không bao giờ** lọt ra ngoài nếu audit thất bại.
- `resource_id` cho collection reads: `collection:{ResourceValue}:{student_id}` (ổn định, để gom nhóm truy vấn cùng 1 subject). Với detail đơn lẻ (message/conversation), `resource_id` = id thực thể đó.

### 2.4 `src/api/admin_policy.py` — prefix `/admin/risk-policy`

| Method | Path | Permission | Mục đích | Lỗi |
|---|---|---|---|---|
| GET | `` | `AI_POLICY:READ` | Lấy risk policy active (nếu DB trống → default projection `v1` không lưu DB) | — |
| GET | `/history` | `AI_POLICY:READ` | Lịch sử risk policy (fallback default nếu rỗng) | — |
| POST | `/preview` | `AI_POLICY:WRITE` | Mô phỏng: chạy `calculate_risk_level()` với policy mới lên toàn bộ RiskSignal chưa resolve, trả `affected_students`, `evaluated_students`, `skipped_signals`, `changes[]` — KHÔNG ghi DB | — |
| POST | `` | `AI_POLICY:APPROVE` | Publish 1 risk policy version mới (status 201), ghi audit `risk_policy_published` | — |
| POST | `/{policy_version}/rollback` | `AI_POLICY:APPROVE` | Tạo version mới copy giá trị từ 1 version cũ, ghi audit `risk_policy_rolled_back` (status 201) | 404 nếu version nguồn không tồn tại |

Request schema `RiskPolicyRequest`:
- `late_days_threshold: int (1..90)`
- `completion_rate_threshold: float (0.0..1.0)`
- `weight_late`, `weight_completion: float (0.0..1.0)`, mặc định 0.5/0.5, **validator bắt buộc `weight_late + weight_completion == 1.0`** (sai số ≤1e-6) — các field weight này **legacy, không còn dùng để tính risk** (xem `calculate_risk_level` mục 3).
- `change_reason: ChangeReason`.

### 2.5 `src/api/admin_settings.py` — prefix `/admin/settings`

| Method | Path | Permission | Mục đích |
|---|---|---|---|
| GET | `` | (role ADMIN only) | Đọc `auto_risk_alert` (bool, mặc định True) và `default_semester` (str, mặc định "Fall 2026") từ bảng `AdminSetting` (key-value) |
| PUT | `` | `SETTING:MANAGE` | Ghi đè 2 setting trên, ghi audit `admin_settings_updated` với `before_state`/`after_state`/`changed_keys` |

Ghi chú: trường `demo_mode` đã bị **xoá khỏi mã nguồn** ở một thời điểm trước (comment: "demo_mode was removed in ADM-13: nothing read it") — bài học thiết kế: đừng thêm toggle không ai đọc.

### 2.6 `src/api/admin_users.py` — prefix `/admin/users`

| Method | Path | Permission | Mục đích | Lỗi |
|---|---|---|---|---|
| GET | `` | (role ADMIN only) | Liệt kê user, filter theo `role` (400 nếu role không hợp lệ), kèm `last_active_at` (max của `AuthSession.last_used_at` hoặc `created_at`) và `class_ids` (qua `AdminPeopleService.class_ids_map`) | 400 unknown role |
| PATCH | `/{user_id}` | `USER:MANAGE` | Bật/tắt `is_active`, ghi audit `user_status_changed` | 409 nếu tự khoá chính mình (`ADMIN_SELF_LOCK_FORBIDDEN`); 404 user not found |
| PATCH | `/{user_id}/access` | `USER:MANAGE` | Đổi role (chỉ STUDENT/INSTRUCTOR) + class scope, có transfer-safety cho Instructor | Nhiều mã lỗi — xem mục 3.1 |

`AdminUserAccessRequest` schema:
- `role`: string, chuẩn hoá upper, độ dài 5-16.
- `class_ids`: list[str], tối đa 100 phần tử.
- `change_reason`: string bắt buộc 10-500 ký tự.

---

## 3. Chi tiết từng service

### 3.1 `AdminPeopleService` (`src/services/admin_people_service.py`)

Mục đích: quản lý transactional việc đổi vai trò Student↔Instructor và class-scope, **không được phá vỡ invariant "Admin là singleton"** và **không được để một Instructor mất hết lớp mà không có người thay thế**.

Public methods:
- `class_ids_for(user) -> list[str]`: Student → danh sách `section_id` đang `ENROLLED`; Instructor → danh sách section đang dạy; role khác → `[]`.
- `class_ids_map(users) -> dict[user_id, list[str]]`: batch version, query theo chunk 500 id (SQLite bound-parameter ceiling).
- `async update_access(*, user_id, target_role, requested_class_ids, current_admin_id, change_reason) -> AdminPeopleResult`: hàm chính, transactional.

Luồng `update_access`:
1. Load `User`; 404 nếu không tồn tại (`AdminPeopleNotFoundError`).
2. Nếu role hiện tại là ADMIN → chặn cứng (`AdminRoleImmutableError`, "singleton Admin role cannot be changed") — **không cho đổi role của chính Admin qua route này**.
3. `AdminAccountService.assert_role_assignment_allowed(target_user_id, target_role, current_admin_id)`: nếu `target_role == "ADMIN"` và (không phải chính actor đang tự gán cho mình, hoặc actor hiện không phải ADMIN) → `AdminAccountLimitError`.
4. `target_role` phải là STUDENT hoặc INSTRUCTOR, nếu không → `AdminPeopleValidationError`.
5. Resolve `class_ids` qua `_resolve_class_ids()` (match theo `CourseSection.id` hoặc `section_code`, phải khớp đúng 1 → nếu không → `AdminPeopleValidationError` "Unknown or ambiguous classes").
6. Nếu target_role == INSTRUCTOR và `class_ids` rỗng → `AdminPeopleValidationError`.
7. Nếu chuyển sang STUDENT: `_apply_student_scope()` — trước tiên kiểm tra user hiện không còn sở hữu section nào (nếu còn → `InstructorScopeTransferRequiredError` "Transfer owned classes before changing an Instructor to Student"); sau đó set các Enrollment cũ không nằm trong `class_ids` mới về `DROPPED`, tạo/update Enrollment mới thành `ENROLLED`.
8. Nếu chuyển sang INSTRUCTOR: `_apply_instructor_scope()` — trước tiên tính "class hiện đang dạy nhưng KHÔNG có trong danh sách mới" (`current - requested`), nếu khác rỗng → `InstructorScopeTransferRequiredError` "Transfer omitted classes before removing them from an Instructor" (không cho tự rút khỏi lớp qua route này, phải transfer tường minh). Sau đó DROP hết Enrollment (nếu trước đó là Student) và gán `CourseSection.instructor_id = user.id` cho các section trong `class_ids`.
   - **Vì `CourseSection.instructor_id` NOT NULL, gán section cho user X luôn "cướp" từ Instructor Y đang giữ.** `_displaced_section_owners()` tính owner bị ảnh hưởng; `_assert_displaced_instructors_retain_scope()` đảm bảo owner đó vẫn còn ≥1 section sau khi bị lấy đi (đếm `CourseSection` họ đang giữ trừ số bị transfer, nếu ≤0 → `InstructorScopeTransferRequiredError` "Every Instructor must retain at least one class").
9. Ghi audit `user_access_changed` cho actor chính (before/after {role, class_ids}), **VÀ ghi thêm 1 audit event riêng cho từng Instructor bị "displaced"** (metadata gồm `transferred_to_user_id`, `section_ids`) — đảm bảo cả 2 phía của 1 transfer đều auditable.
10. Commit; nếu exception ở bất kỳ đâu → rollback toàn bộ.

Exception classes: `AdminPeopleError` (base, code `ADMIN_PEOPLE_ERROR`), `AdminPeopleNotFoundError` (`USER_NOT_FOUND`), `AdminPeopleValidationError` (`INVALID_ACCESS_SCOPE`), `AdminRoleImmutableError` (`ADMIN_ROLE_IMMUTABLE`), `InstructorScopeTransferRequiredError` (`INSTRUCTOR_SCOPE_TRANSFER_REQUIRED`).

### 3.2 `AdminAccountService` (`src/services/admin_account_service.py`)

- `provision_single_admin(command: AdminProvisionCommand) -> User`: bootstrap tài khoản Admin lúc khởi tạo hệ thống (dùng ở script, không qua API HTTP admin thường). Validate email/full_name non-empty, `validate_password_policy(password)`. Nếu email đã tồn tại: nếu role đã là ADMIN → trả về user đó (idempotent); nếu role khác → `AdminEmailConflictError`. Nếu đã có ≥1 Admin → `AdminAccountLimitError`. Insert; nếu `IntegrityError` (race condition unique index `uq_users_single_admin_role`) → rollback, tra lại theo email, nếu ai đó đã tạo Admin trùng email → trả về, ngược lại raise `AdminAccountLimitError`.
- `assert_role_assignment_allowed(*, target_user_id, target_role, current_admin_id)`: nếu `target_role != "ADMIN"` → no-op (pass). Nếu là "ADMIN": chỉ cho phép khi `current_admin_id == target_user_id` VÀ actor hiện tại thực sự có role ADMIN — nói cách khác **API hiện tại không có đường nào thực sự gán role ADMIN cho ai qua `update_access`** vì `AdminPeopleService.update_access` đã chặn target_role ngoài STUDENT/INSTRUCTOR trước khi gọi hàm này; hàm này tồn tại như 1 lớp phòng thủ bổ sung (defense in depth).

### 3.3 `AdminAccountRecoveryService` (`src/services/admin_account_recovery_service.py`)

Không lộ qua route HTTP (dùng bởi `scripts/recover_admin_account.py`, actor_kind=OPS). Recovery **không tạo tài khoản break-glass mới** — chỉ reset password + revoke toàn bộ AuthSession của **chính** tài khoản Admin duy nhất.

`async recover(command: AdminRecoveryCommand) -> AdminRecoveryResult`:
1. Validate `reason` (10-500 ký tự), `external_ref` (≥3 ký tự — incident reference), `ops_actor_ref` (≥3 ký tự).
2. Query toàn bộ user role=ADMIN; phải đúng 1 người VÀ id khớp `command.admin_user_id`, nếu không → `AdminRecoveryTargetError`.
3. `validate_password_policy(new_password)` (cùng policy với provisioning).
4. Revoke tất cả `AuthSession` chưa bị revoke của Admin đó (`revoked_reason="OPS_RECOVERY"`).
5. Set `password_hash` mới, `is_active = True` (đảm bảo không bị khoá do sự cố trước).
6. Ghi audit `admin_account_recovered` với `actor_user_id=None`, `actor_kind=AuditActorKind.OPS`, `external_actor_ref=ops_actor_ref`, `subject_user_id=admin.id`, metadata gồm `auth_sessions_revoked`, `external_ref`, `recovery_id` (uuid mới sinh ra mỗi lần, không phải primary key nào).
7. Commit; trả `AdminRecoveryResult(admin_user_id, audit_event_id, auth_sessions_revoked, password_reset=True)`.

### 3.4 `AdminDocumentLifecycleService` (`src/services/admin_document_lifecycle_service.py`)

State machine của 1 `Document` (chỉ áp dụng cho document Admin-owned: `scope=OFFICIAL_CURRICULUM`, `source_kind="admin_curriculum"`, `metadata_info.source == provenance_info.source == "admin_curriculum"`):

```
DRAFT --validate(pass)--> READY_FOR_REVIEW --publish--> PUBLISHED --archive--> ARCHIVED
DRAFT --validate(fail)--> DRAFT (ở lại)
READY_FOR_REVIEW --validate lại--> DRAFT hoặc READY_FOR_REVIEW (tuỳ kết quả)
ARCHIVED --rollback--> (tạo document PUBLISHED mới, clone nội dung)
```

- `validate(document_id, actor_user_id) -> dict`: Không cho validate document đã PUBLISHED/ARCHIVED (`DocumentLifecycleConflict`). Gọi `recompute_validation_snapshot()` (side-effect-free tính toán) rồi **mới** ghi `document.validation_info`, chuyển `publication_status`: nếu `snapshot["valid"]` → READY_FOR_REVIEW, set `validated_at/by` (chỉ update timestamp nếu snapshot thay đổi hoặc chưa từng validate — tránh nhiễu audit); nếu invalid → DRAFT, xoá `validated_at/by`. Commit ngay trong service (khác các method khác — đây có tự-commit riêng, không đợi transaction ngoài).
- Validation checks (8 tiêu chí, tất cả phải pass để `valid=True`):
  - `official_scope`: `scope == OFFICIAL_CURRICULUM`.
  - `admin_source`: source_kind + metadata + provenance đều `"admin_curriculum"`.
  - `sha256`: checksum khớp regex 64 hex chars.
  - `checksum_matches_file`: đọc file thật, so `hashlib.sha256(bytes)` với `checksum_sha256` bằng `hmac.compare_digest`.
  - `readable_file`: file đọc được, UTF-8 decode được.
  - `has_chunks`: có ≥1 `DocumentChunk`.
  - `chunk_limit`: số chunk ≤ `MAX_CHUNKS=80`.
  - `course_provenance`: `metadata.course_code == provenance.course_code == Course.code`.
- `async publish(document_id, actor_user_id, change_reason) -> Document`: chỉ cho publish từ READY_FOR_REVIEW (409 nếu đã published hoặc chưa ready). Tìm bản đang active (`_active_version`, PUBLISHED cùng `version_group_id`), nếu có và khác chính nó → tự động archive bản đó trước (`_archive()` set ARCHIVED/archived_at/archived_by). Bắt `IntegrityError` từ unique index `uq_documents_one_published_per_version_group` (partial unique index chỉ áp dụng khi `publication_status='PUBLISHED'`) → convert thành `DocumentLifecycleConflict` "concurrent curriculum publication conflict; reload and retry". Ghi audit `curriculum_published` (before/after gồm cả bản bị archive).
- `async archive(...)`: không cho archive lại document đã ARCHIVED. Ghi audit `curriculum_archived`.
- `async rollback(target_document_id, actor_user_id, change_reason) -> Document`: **tạo document mới**, không sửa document cũ.
  1. Target phải đang ARCHIVED (409 nếu không).
  2. Tính lại validation trên target (`_recompute_validation_state`), cho phép bỏ qua lỗi `sha256`/`checksum_matches_file` NẾU document legacy chưa từng có checksum (`legacy_checksum_missing`) — đây là tương thích ngược cho dữ liệu cũ trước khi có checksum.
  3. Các lỗi validation khác (`blocking_errors`) → 409 "Rollback target failed persisted-state validation: ...".
  4. Nếu không legacy nhưng snapshot invalid → 409 "checksum mismatch".
  5. Phải tồn tại 1 bản đang PUBLISHED (`active`) trong version_group để archive khi rollback xong; nếu không → 409 "Rollback requires a currently published version".
  6. Đọc lại bytes gốc từ file (`source_bytes`); nếu None → 409 "readable_file".
  7. Tạo `Document` mới id=`doc_admin_{uuid4}`, version = `next_document_version()`, `provenance_info` merge thêm `rollback_of`/`rollback_by`, publication_status=DRAFT ban đầu.
  8. Clone toàn bộ `DocumentChunk` từ target sang bản mới (id=`chunk_admin_{new_id}_{index}`).
  9. Nếu không có chunk nào để clone → 409 "Rollback target has no persisted chunks".
  10. Tính lại validation trên bản clone (dùng lại `source_bytes` đã đọc, tránh đọc file 2 lần); nếu invalid → 409.
  11. Archive bản `active` cũ, publish bản rollback mới (published_at/by set trực tiếp, publication_status=PUBLISHED) — cùng bắt `IntegrityError` unique-index như `publish()`.
  12. Ghi audit `curriculum_rolled_back`.
- `versions(document_id) -> list[Document]`: liệt kê toàn bộ document cùng `version_group_id` + `course_id` + scope OFFICIAL_CURRICULUM + source_kind admin_curriculum, lọc thêm theo metadata/provenance source để chắc chắn.
- `ensure_deletable(document_id) -> Document`: không cho xoá nếu đang PUBLISHED (409 "must be archived or replaced before deletion") hoặc ARCHIVED (409 "Archived document history is immutable" — lịch sử archived là bất biến); không cho xoá nếu có document khác trỏ `previous_version_id` về nó (409 "A later version depends on this document").
- `_active_version()`: nếu tìm thấy >1 bản PUBLISHED trong cùng version_group (không nên xảy ra do unique index) hoặc có bản PUBLISHED "lạc" ra ngoài ranh giới Admin (course_id/scope/source khác) → raise `DocumentLifecycleConflict` (defense-in-depth, phát hiện dữ liệu bất thường).

Hằng số quan trọng: `_PUBLISHED_GROUP_CONSTRAINT = "uq_documents_one_published_per_version_group"`, dùng để nhận diện lỗi UNIQUE constraint từ cả Postgres (`diag.constraint_name`) lẫn SQLite (match message string `"UNIQUE constraint failed: documents.version_group_id"`).

### 3.5 `AdminDocumentIngestService` (`src/services/admin_document_ingest_service.py`)

Hằng số: `ALLOWED_EXTENSIONS = {".md", ".txt"}`, `MAX_UPLOAD_BYTES = 2MB`, `MAX_CHUNKS = 80`, `READABLE_CURRICULUM_SOURCES = {"admin_curriculum", "mock", "mock_lms"}`, `DEFAULT_UPLOADS_ROOT = ROOT/"data/admin_uploads"`.

- `validate_admin_document(filename, content) -> ValidatedDocument`: filename được "làm sạch" (`_safe_filename`: chỉ giữ `\w.\-`, thay còn lại bằng `_`); suffix phải thuộc allowed; content không rỗng, ≤2MB, decode UTF-8 được, sau `.strip()` không rỗng.
- `ingest_new(course_code, filename, content, actor_user_id) -> dict`: chia văn bản thành đoạn (`_validated_paragraphs`: split theo `\n\s*\n`), kiểm tra `len(paragraphs) <= MAX_CHUNKS` (ValueError nếu vượt). Ghi file vật lý (`_write`, path = `uploads_root/{document_id}_{filename}`), tạo `Document` mới (version="1", DRAFT, scope OFFICIAL_CURRICULUM, source_kind="admin_curriculum", checksum SHA256 của nội dung đã validate). Nếu insert DB lỗi → xoá file vừa ghi (rollback thủ công filesystem). Trả dict kèm `_created_path` (để caller dọn nếu job fail sau đó).
- `replace(document_id, filename, content, actor_user_id) -> dict`: tương tự nhưng version = `next_document_version(version_group_id)`, `previous_version_id` trỏ về bản cũ, giữ nguyên `version_group_id`. Trả thêm `_cleanup_path` (None ở đây — logic dọn file cũ nằm ở `admin_ingest_runner`).
- `delete(document_id, actor_user_id) -> Path`: gọi `AdminDocumentLifecycleService.ensure_deletable()` trước, resolve đường dẫn file qua `resolve_managed_cleanup_path()` (đảm bảo path nằm trong `uploads_root`, chống path traversal — raise `PermissionError` nếu không), xoá `DocumentChunk` rồi xoá `Document`, trả về path để caller unlink file thật sau khi transaction DB thành công.
- `next_document_version(db, version_group_id) -> str`: parse mọi version hiện có thành `Decimal`, next = `floor(max) + 1`. Raise `ValueError` nếu version không phải số, không hữu hạn, trùng lặp giá trị số nhưng khác biểu diễn chuỗi ("ambiguous"), hoặc version kế tiếp bị trùng.
- Chunk hoá (`_chunk`): mỗi đoạn văn 1 chunk, `token_count = max(1, len(words))`, metadata gồm `section` (heading markdown `#` đầu tiên trong đoạn nếu có), `source_label`.

### 3.6 `admin_ingest_runner.py` — background worker

`run_admin_ingest_job(*, job_id, operation, payload)`: chạy trong `BackgroundTasks`, tự mở `SessionLocal()` riêng (không dùng session của request).
- `operation="upload"` → `service.ingest_new(**payload)`; `operation="replace"` → `service.replace(**payload)`; `operation="delete"` → `_run_delete_job(...)`; operation khác → `ValueError`.
- Thành công: `repository.finish_job(status="ingested", document_id=...)`, ghi audit (`admin_document_uploaded`/`admin_document_replaced`), commit, rồi mới unlink file cũ nếu có `cleanup_after_commit` (đảm bảo không xoá file vật lý trước khi DB commit thành công).
- Thất bại: rollback DB, xoá file vừa tạo nếu có (`cleanup_on_failure`), cố gắng ghi job "failed" + audit deny (best-effort, tự bọc try/except riêng để không throw đè lên exception gốc).
- `_run_delete_job`: 2 pha đặc biệt để xử lý **transaction ngắt giữa xoá DB và xoá file vật lý** (ví dụ nếu process crash giữa chừng):
  1. Nếu job đã "ingested", error=None, document_id=None → coi như đã xong (idempotent no-op, tránh chạy lại 2 lần).
  2. `cleanup_pending_state(job, job_id)`: parse `job.error` xem có đang ở dạng `"cleanup_pending:{json}|path=..."` không (tức lần chạy trước đã xoá DB nhưng chưa unlink được file) → nếu có, đây là **lần retry**, bỏ qua bước xoá DB, đi thẳng vào unlink.
  3. Nếu chưa: set `job.document_id = None` trước (break FK) rồi `service.delete()` (xoá Document/Chunk trong cùng transaction với việc break FK — nếu lifecycle check thất bại, cả 2 đều rollback), set `job.error` thành chuỗi "cleanup_pending:..." (đánh dấu cần dọn file), commit **transaction DB xong trước khi động vào file**.
  4. `_unlink_file_strict(path)`: idempotent (bỏ qua `FileNotFoundError`). Nếu `OSError` khác → rollback, set job "failed" với error cleanup_pending y hệt, ghi audit `admin_document_delete_cleanup_failed`, dừng (route "retry-cleanup" sẽ được dùng để thử lại — xem 2.1).
  5. Thành công: `finish_job(status="ingested", error=None, clear_document_id=True)`, audit `admin_document_deleted` (metadata có `cleanup_retry: bool`).
- `_safe_error(exc)`: chỉ lộ message thật nếu exception thuộc `(ValueError, LookupError, PermissionError, RuntimeError)` (domain error có thể public), ngược lại trả chuỗi chung "Document processing failed" (che giấu lỗi hạ tầng/nội bộ).

### 3.7 `AdminReadService` (`src/services/admin_read_service.py`)

- `fail_stale_ingest_jobs(max_age_seconds=1800) -> int`: đánh dấu "failed" mọi `CourseIngestJob` đang "processing" quá 30 phút (trừ khi đã ở dạng cleanup_pending — giữ nguyên error đó). Được gọi ở đầu mỗi lần GET `/admin/courses` (tự-heal).
- `list_courses() -> dict`: hợp nhất 3 nguồn:
  1. Catalog tĩnh từ `load_curriculum()` (file demo data) — bắt buộc đúng định dạng, nếu thiếu/sai → `AdminDataUnavailable` (fail-closed, không trả dữ liệu một phần).
  2. Đếm chunk mỗi course từ `DocumentChunk` join `Document` join `Course`, chỉ tính document có `is_curriculum_document()` (metadata.source ∈ {"admin_curriculum","mock","mock_lms"}).
  3. Override từ `AdminCourseOverride` (course bị hide → loại khỏi kết quả; course Admin tự thêm và chưa hide → override thông tin tên/kỳ, `is_added=True`, `source="manual"`).
  4. Trạng thái ingest: mặc định "ingested" nếu có ≥1 chunk else "not_ingested"; nếu có `CourseIngestJob` mới nhất đang "processing"/"failed" → override status đó (kèm `ingest_error` nếu failed).
  5. Sort: theo `(0, int(semester), code)` nếu semester là số, else `(1, semester_str, code)`.

### 3.8 `AdminWorkQueueService` (`src/services/admin_work_queue_service.py`)

`build_work_queue() -> list[dict]`: gộp 4 nguồn, mỗi nguồn giới hạn 100 bản ghi mới nhất:
1. `RiskSignal` chưa resolve, risk_level ∈ {HIGH, CRITICAL} → priority HIGH.
2. `GuardrailEvent` classification=BLOCKED, review_status IS NULL hoặc "PENDING", join Message→Conversation lấy student_id → priority HIGH.
3. `DataRequest` status ∈ {PENDING, IN_PROGRESS} → priority MEDIUM.
4. `CourseIngestJob` status="failed" → priority MEDIUM, subject_user_id=None.

Sort cuối: theo `priority_rank {CRITICAL:0, HIGH:1, MEDIUM:2, LOW:3}` tăng dần, rồi `age_seconds` giảm dần (cũ nhất trước trong cùng priority). `age_seconds = max(0, now - occurred_at)`; nếu không có timestamp (guardrail event) → 0.

### 3.9 `AdminObservabilityReadService` + `AdminSensitiveReadService` (`src/services/admin_observability_read_service.py`)

**Tầng T0/T1** (`AdminObservabilityReadService`):
- `build_overview()`: tính `active_students`/`active_instructors` (User.is_active=True group by role), `unresolved_students` (distinct student có risk chưa resolve mức HIGH/CRITICAL, chỉ tính active student), `accepted/sent` invitations, work queue, failed ingest jobs. `system_status = DEGRADED nếu failed_jobs > 0 else HEALTHY`. 2 pulse metric (`unresolved_risk`, `invitation_activation`) đều dùng `_metric()`: `value = numerator/denominator` hoặc **`None` nếu denominator=0** (không bao giờ hiển thị "0%" giả khi mẫu số rỗng) — luôn kèm `method_note` mô tả công thức bằng tiếng Anh cho khả năng audit.
- `list_people(...)`: query có filter, PHẢI audit (`ADMIN_IDENTIFIED_READ`) trước khi trả — nếu audit lỗi, toàn bộ exception (`SensitiveAuditUnavailableError`) nổi lên trước response.
- `student_summary`/`instructor_summary`: `_require()` tra đúng role, lỗi 404 y hệt dù id sai hay role sai (chống information leak về việc id có tồn tại không).
- `IDENTIFIED_READ_EVENT = "ADMIN_IDENTIFIED_READ"`; `PEOPLE_COLLECTION_ID = "collection:USER:people"`.

**Tầng T2** (`AdminSensitiveReadService` + hàm `to_*_dto`):
- Toàn bộ DTO là **allow-list viết tay**, comment nhấn mạnh: không dùng `model.__dict__`, không `from_attributes` trên ORM model trực tiếp — một cột DB mới thêm vào sẽ KHÔNG tự động lộ ra response.
- `to_message_dto`: `metadata_info` được lọc qua whitelist `MESSAGE_METADATA_KEYS = {mode, blocked, blockReason, route, degraded, citations, alternatives, warnings}` + nested `observability` lọc qua `MESSAGE_OBSERVABILITY_KEYS = {faq_hit, faq_id, web_used, web_results, latency_ms}`. **`generation_metadata` bị loại bỏ có chủ đích** (chứa config nhà cung cấp LLM). `blocked_answer` của guardrail **được giữ lại** vì mục đích T2 chính là xem lại nội dung bị chặn.
- `to_student_document_dto`: **`file_path` không bao giờ xuất hiện** — comment: "absent by construction, not by filtering".
- `MAX_ACTIVITY_WINDOW = 90 ngày` — `assert_activity_window()` raise `ActivityWindowTooWideError` nếu vượt (chỉ áp dụng route progress-events).
- Repository (`AdminSensitiveReadRepository`) luôn bound child-collection ở `MAX_NESTED_ROWS=500`, trả thêm cờ `nested_truncated` nếu bị cắt — không bao giờ cắt âm thầm.
- `load_conversation_detail`: 404 (`SensitiveRecordNotFoundError`) nếu `conversation_id` không thuộc đúng `student_id` (kiểm tra trong SQL, không phải sau khi load).
- `load_documents`: chỉ document `scope=STUDENT_PRIVATE` và `provenance_info["uploaded_by"] == student_id` (so sánh JSON field trực tiếp trong SQL qua `Document.provenance_info["uploaded_by"].as_string()`).

### 3.10 `AdminDataRequestService` (`src/services/admin_data_request_service.py`)

Không có router riêng `admin_data_request.py`; được gọi từ `src/api/data_requests.py` (router không theo naming convention `admin_*.py` nhưng chứa route `/admin/data-requests/*`).

- `create_for_subject(subject_user_id, DataRequestCreateCommand(request_type, request_note))`: Student tự tạo request cho chính mình (route STUDENT, không phải Admin), audit `data_request_created`.
- `async transition(request_id, DataRequestTransitionCommand(status, resolution_note), actor_id)`: Admin chuyển trạng thái. **Cấm** chuyển DELETION request sang COMPLETED qua route này (`DataRequestTransitionError` — DELETION chỉ hoàn tất qua `confirm_deletion` sau khi đã purge thật). `_assert_transition()`: state machine hợp lệ — PENDING→{IN_PROGRESS, REJECTED}; IN_PROGRESS→{COMPLETED, REJECTED}; bất kỳ transition khác → lỗi.
- `async preview_deletion(request_id, actor_id) -> PurgePreview`: gọi `RetentionService.preview(subject_user_id)`, lưu `dry_run_summary` (bao gồm `preview_hash` — dùng để chống confirm với preview cũ/stale), audit `data_request_deletion_previewed`.
- `async confirm_deletion(request_id, preview_hash, actor_id) -> PurgeResult`: idempotent-replay — nếu `result_summary` đã tồn tại (đã purge trước đó) → trả kết quả rỗng ngay (không purge lại lần 2). Nếu `preview_hash` không khớp `dry_run_summary.preview_hash` → `RetentionPreviewStaleError` (bắt buộc phải preview lại trước khi confirm, chống race giữa preview cũ và dữ liệu mới phát sinh). Gọi `RetentionService.purge()`, set status=COMPLETED, `completed_at`, audit `data_request_purged`.

Endpoint tương ứng (đọc lại từ `data_requests.py`, không thuộc admin_*.py nhưng thuộc phạm vi Admin backend chức năng): `GET/PATCH /admin/data-requests`, `GET /admin/data-requests/{id}`, `POST /admin/data-requests/{id}/deletion-preview`, `POST /admin/data-requests/{id}/confirm-deletion` — permission `_ADMIN_DEPENDENCIES = [require_roles(ADMIN), require_permission(DATA_REQUEST, MANAGE)]`.

---

## 4. Data model & migration timeline liên quan Admin

Thứ tự migration (chỉ các file chạm tới Admin, theo `down_revision` chain):

1. **`20260808_baseline_schema`** — baseline (không đọc chi tiết, chứa hầu hết bảng gốc bao gồm `users`, `documents`, `audit_logs` version đầu).
2. **`20260813_guardrail_rules`** — tạo bảng `guardrail_rules(code PK, enabled, updated_at, updated_by FK users SET NULL)`. Seed 3 rule: HOMEWORK_VI, FULL_CODE, HOMEWORK_EN.
3. **`20260815_admin_course_overlay`** — tạo `admin_course_overrides(subject_code PK, subject_name, semester, is_added, hidden, updated_at, updated_by)` và `course_ingest_jobs(id PK, course_code idx, document_id FK documents SET NULL idx, operation, status idx, error, created_at idx, completed_at)`.
4. **`20260816_guardrail_reviews`** — thêm cột vào `guardrail_events`: `review_status`, `block_reason`, `blocked_answer` (Text), `reviewed_by` (FK users), `reviewed_at`. Idempotent (kiểm tra cột tồn tại trước khi add — tương thích DB tạo bằng `create_all`).
5. **`20260824_admin_invites`** — tạo `invitations(id PK, email idx, role, token_hash unique idx, status idx default "pending", class_ids JSON, invited_by FK users SET NULL, created_at, expires_at idx, accepted_at)`. (Migration này KHÔNG add cột `delivery_status/last_sent_at/resend_count/last_delivery_error` — các cột này chắc chắn được thêm ở 1 migration sau, `20260830_invitation_access_lifecycle`, không nằm trong danh sách được liệt kê ở nhiệm vụ vì tên file không match `admin|invite|guardrail_rule|risk_policy|data_request|audit` — LƯU Ý: file này có tên `20260830_invitation_access_lifecycle.py`, KHÔNG match keyword "invite" theo grep case-sensitive kiểm tra thực tế — cần đọc riêng nếu cần chính xác 100% cột `delivery_status`. Model `Invitation` ở mục 4.2 phản ánh state đầy đủ hiện tại bao gồm các cột này.)
6. **`20260825_admin_policy`** — tạo `risk_policies(policy_version PK, late_days_threshold, completion_rate_threshold, weight_late, weight_completion, change_reason, effective_from, is_active idx, created_by FK users SET NULL, created_at)`, seed `v1` (late_days=5, completion_rate=0.4, weight 0.6/0.4). Tạo `admin_settings(key PK, value, updated_by FK users, updated_at)`. Thêm cột `risk_signals.policy_version` (server_default "v1").
7. **`20260826_risk_policy_version_required`** — bỏ `server_default` của `risk_signals.policy_version` (buộc caller luôn truyền tường minh, không dựa vào default ngầm).
8. **`20260827_audit_foundation`** — thêm cột `audit_logs`: `before_state` (JSON), `after_state` (JSON), `change_reason` (Text), `request_id`, `correlation_id`.
9. **`20260828_document_governance`** — migration lớn nhất: thêm 14 cột governance vào `documents` (`scope`, `publication_status`, `source_kind`, `version_group_id`, `provenance_info`, `previous_version_id`, `checksum_sha256`, `validation_info`, `validated_at/by`, `published_at/by`, `archived_at/by`). **Backfill fail-closed**: dựa vào `metadata_info.source` cũ để suy ra `scope` (admin_curriculum/mock/mock_lms → OFFICIAL_CURRICULUM; student_upload → STUDENT_PRIVATE; khác → QUARANTINED — dữ liệu không rõ nguồn gốc bị cách ly, không mặc định coi là an toàn). `published` suy ra từ việc document có ingest job "ingested" hoặc (là verified seed source và có chunk). Sau backfill, `_assert_required_backfill()` raise `RuntimeError` cứng nếu còn row nào có cột governance NULL (migration tự fail thay vì để dữ liệu half-migrated). Tạo FK `previous_version_id/validated_by/published_by/archived_by`, unique constraint `(version_group_id, version)`, và **partial unique index** `uq_documents_one_published_per_version_group` (chỉ áp dụng khi `publication_status='PUBLISHED'` — đây chính là ràng buộc DB-level đảm bảo "1 version_group chỉ có tối đa 1 bản PUBLISHED tại một thời điểm", được service tầng trên dựa vào).
10. **`20260829_single_admin_account`** — preflight kiểm tra hiện tại không có >1 user role=ADMIN (raise nếu vi phạm), sau đó tạo **partial unique index** `uq_users_single_admin_role` trên `users(role)` chỉ khi `role='ADMIN'` — đây là ràng buộc DB-level cho invariant "chỉ 1 Admin", độc lập với logic ở tầng service.
11. **`20260829a_alembic_version_width`** — kỹ thuật, chỉ ảnh hưởng Postgres, mở rộng cột `alembic_version.version_num` từ 32→128 ký tự (do tên revision dài).
12. **`20260831_guardrail_policy_versions`** — tạo `guardrail_policy_versions(version PK, rules_snapshot JSON, source_version, change_reason Text, is_active idx, created_by FK users, created_at)`. Thêm cột `guardrail_rules`: `core_locked` (default False), `current_version` (default "gpv1"), `change_reason` (Text). Đánh dấu `core_locked=True` cho 2 code `PROMPT_INJECTION_OVERRIDE`, `SYSTEM_PROMPT_LEAK`. Seed 1 `guardrail_policy_versions` row "gpv1" snapshot từ trạng thái enable hiện tại.
13. **`20260901_data_request_retention`** — tạo `data_requests(id PK, subject_user_id FK users CASCADE idx, request_type idx, status idx default PENDING, request_note Text, resolution_note, dry_run_summary JSON, result_summary JSON, requested_at, completed_at)`. Tạo `retention_policies(id PK, policy_version idx, category idx, retention_days, action default DELETE, effective_from, is_approved idx default False, updated_by FK users, change_reason Text, updated_at, UNIQUE(policy_version, category))`, seed 4 baseline retention (CHAT/REFLECTION 90 ngày DELETE, PLAN 180 ngày DELETE, SECURITY_METADATA 365 ngày ANONYMIZE) — tất cả `is_approved=False` (chờ duyệt tường minh, không tự động active).
14. **`20260902_admin_access_cases`** — tạo `admin_access_cases` (case_type, status default OPEN, priority default MEDIUM, subject_user_id FK CASCADE, linked_resource_type/id, external_ref, explanation Text, opened_by FK RESTRICT, opened_at, updated_at, resolved_at, closed_at, resolution_summary) + nhiều index composite. Tạo `sensitive_access_sessions` (case_id FK CASCADE, actor_user_id FK CASCADE, subject_user_id FK CASCADE, token_hash unique length=64 CHECK, issued_at, expires_at, last_used_at, revoked_at, mfa_method default "TOTP" CHECK ='TOTP', ip_address, user_agent). Thêm cột `audit_logs`: `actor_kind` (CHECK IN ('USER','OPS','SYSTEM'), default "USER"), `external_actor_ref`, `subject_user_id`, `admin_access_case_id`, `sensitive_access_session_id` (đều FK SET NULL) + nhiều index. **Lưu ý quan trọng**: 2 bảng `admin_access_cases`/`sensitive_access_sessions` được tạo migration này nhưng — theo code hiện tại đọc ở mục 1-3 — **không còn route/service nào ghi dữ liệu vào chúng nữa** (route T2 hiện dùng `SensitiveAccessContext.for_direct_read()` không cần case/session). Đây là schema "còn treo" (xem mục 7 — nhận xét).
15. **`20260903_guardrail_event_retention`** — nới `guardrail_events.message_id` thành `nullable=True` (để retention purge có thể xoá `Message` liên quan mà vẫn giữ lại `GuardrailEvent` — an toàn record, không đánh mất lịch sử blocked/reviewed).

### 4.2 Model liên quan Admin (trích từ `src/db/models.py`)

**Enum:**
```python
class UserRole(enum.Enum):
    STUDENT = "STUDENT"; INSTRUCTOR = "INSTRUCTOR"; ADMIN = "ADMIN"; SERVICE_ACCOUNT = "SERVICE_ACCOUNT"

class DataRequestType(enum.StrEnum):
    ACCESS = "ACCESS"; EXPORT = "EXPORT"; CORRECTION = "CORRECTION"; DELETION = "DELETION"

class DataRequestStatus(enum.StrEnum):
    PENDING = "PENDING"; IN_PROGRESS = "IN_PROGRESS"; COMPLETED = "COMPLETED"; REJECTED = "REJECTED"

class AdminCaseType(enum.StrEnum):  # bảng vẫn tồn tại, không còn dùng bởi route hiện tại
    RISK_ALERT_REVIEW; SAFETY_ESCALATION; DATA_REQUEST_FULFILMENT; STUDENT_SUPPORT; SECURITY_INCIDENT; QUALITY_AUDIT

class AdminCaseStatus(enum.StrEnum): OPEN; IN_REVIEW; RESOLVED; CLOSED; REOPENED
class AdminCasePriority(enum.StrEnum): LOW; MEDIUM; HIGH; CRITICAL
class AuditActorKind(enum.StrEnum): USER; OPS; SYSTEM

class DocumentScope(enum.StrEnum):
    OFFICIAL_CURRICULUM = "OFFICIAL_CURRICULUM"; STUDENT_PRIVATE = "STUDENT_PRIVATE"; QUARANTINED = "QUARANTINED"

class DocumentPublicationStatus(enum.StrEnum):
    DRAFT = "DRAFT"; READY_FOR_REVIEW = "READY_FOR_REVIEW"; PUBLISHED = "PUBLISHED"; ARCHIVED = "ARCHIVED"
```

**User** (`users`): `id PK`, `email unique idx`, `password_hash`, `full_name`, `role (String, lưu giá trị UserRole)`, `is_email_verified bool`, `is_active bool`, `created_at`. `__table_args__` có **partial unique index** `uq_users_single_admin_role` trên `role` `WHERE role='ADMIN'`.

**AuthSession** (`sessions`): `id PK`, `user_id FK CASCADE idx`, `refresh_token_hash unique idx`, `token_family_id idx`, `device_label`, `user_agent_hash`, `ip_address`, `remember_me bool`, `revoked_at`, `revoked_reason`, `expires_at idx`, `absolute_expires_at idx`, `created_at`, `last_used_at`.

**Invitation** (`invitations`): `id PK`, `email idx`, `role`, `token_hash unique idx`, `status default "pending" idx`, `class_ids JSON default list`, `invited_by FK users SET NULL`, `created_at`, `expires_at idx`, `accepted_at`, `delivery_status String(16) default "disabled" idx`, `last_sent_at`, `resend_count int default 0`, `last_delivery_error String(255)`.

**AuditLog** (`audit_logs`): `id PK`, `actor_user_id FK users SET NULL idx`, `actor_kind default "USER" idx` (CHECK IN USER/OPS/SYSTEM), `external_actor_ref`, `subject_user_id FK users SET NULL idx`, `admin_access_case_id FK admin_access_cases SET NULL idx`, `sensitive_access_session_id FK sensitive_access_sessions SET NULL idx`, `event_type idx`, `resource_type`, `resource_id`, `decision`, `ip_address`, `user_agent`, `before_state JSON`, `after_state JSON`, `change_reason Text`, `request_id`, `correlation_id`, `metadata_info JSON default dict`, `created_at idx`.

**Document** (`documents`): `id PK`, `course_id FK courses CASCADE`, `title`, `file_path`, `doc_type`, `version`, `metadata_info JSON`, `scope default QUARANTINED`, `publication_status default DRAFT`, `source_kind default "unknown"`, `version_group_id default = self.id`, `provenance_info JSON default dict`, `previous_version_id FK documents(self) SET NULL`, `checksum_sha256 String(64)`, `validation_info JSON`, `validated_at`, `validated_by FK users SET NULL`, `published_at`, `published_by FK users SET NULL`, `archived_at`, `archived_by FK users SET NULL`. Constraints: `UNIQUE(version_group_id, version)`; **partial unique index** `uq_documents_one_published_per_version_group` trên `version_group_id` `WHERE publication_status='PUBLISHED'`.

**GuardrailRule** (`guardrail_rules`): `code PK`, `enabled bool default True`, `core_locked bool default False`, `current_version default "gpv1"`, `change_reason Text default "Initial guardrail policy"`, `updated_at`, `updated_by FK users SET NULL`.

**GuardrailPolicyVersion** (`guardrail_policy_versions`): `version PK`, `rules_snapshot JSON`, `source_version`, `change_reason Text`, `is_active bool default False idx`, `created_by FK users SET NULL`, `created_at`.

**RiskPolicy** (`risk_policies`): `policy_version PK`, `late_days_threshold int`, `completion_rate_threshold float`, `weight_late float`, `weight_completion float`, `change_reason`, `effective_from`, `is_active bool default False idx`, `created_by FK users SET NULL`, `created_at`.

**AdminSetting** (`admin_settings`): `key PK`, `value`, `updated_by FK users SET NULL`, `updated_at`.

**AdminCourseOverride** (`admin_course_overrides`): `subject_code PK`, `subject_name`, `semester`, `is_added bool default False`, `hidden bool default False`, `updated_at`, `updated_by FK users SET NULL`.

**CourseIngestJob** (`course_ingest_jobs`): `id PK`, `course_code idx`, `document_id FK documents SET NULL idx`, `operation`, `status idx`, `error Text`, `created_at idx`, `completed_at`.

**DataRequest** (`data_requests`): `id PK`, `subject_user_id FK users CASCADE idx`, `request_type idx`, `status default PENDING idx`, `request_note Text`, `resolution_note Text`, `dry_run_summary JSON`, `result_summary JSON`, `requested_at`, `completed_at`.

**RetentionPolicy** (`retention_policies`): `id PK`, `policy_version idx`, `category idx`, `retention_days int`, `action default "DELETE"`, `effective_from`, `is_approved bool default False idx`, `updated_by FK users SET NULL`, `change_reason Text`, `updated_at`.

**AdminAccessCase** (`admin_access_cases`) — schema tồn tại, **hiện không có producer nào ghi vào bảng này** (xem mục 7): `id PK`, `case_type idx`, `status default OPEN idx`, `priority default MEDIUM idx`, `subject_user_id FK users CASCADE idx`, `linked_resource_type/id`, `external_ref`, `explanation Text`, `opened_by FK users RESTRICT`, `opened_at idx`, `updated_at`, `resolved_at`, `closed_at`, `resolution_summary Text`. + composite index (subject_user_id, status, case_type), (linked_resource_type, linked_resource_id), (status, priority, opened_at).

**SensitiveAccessSession** (`sensitive_access_sessions`) — tương tự, không còn producer: `id PK`, `case_id FK admin_access_cases CASCADE idx`, `actor_user_id FK users CASCADE idx`, `subject_user_id FK users CASCADE idx`, `token_hash String(64) unique idx` (CHECK length=64), `issued_at idx`, `expires_at idx`, `last_used_at`, `revoked_at`, `mfa_method default "TOTP"` (CHECK ='TOTP'), `ip_address`, `user_agent`. + composite index (actor_user_id, case_id, subject_user_id), (case_id, revoked_at, expires_at).

**RiskSignal** (`risk_signals`, dùng nhiều bởi Admin risk-policy/observability): `id PK`, `student_id FK users CASCADE`, `section_id FK course_sections CASCADE`, `assignment_id FK assignments SET NULL`, `risk_type` (LATE_SUBMISSION/ABANDONMENT/OVERLOAD/ACADEMIC_DECLINE/WEEKLY_GOAL_FAILURE), `risk_level` (LOW/MEDIUM/HIGH — lưu ý: routes T2 model schema chấp nhận cả "CRITICAL" trong work-queue nhưng cột comment gốc chỉ liệt kê 3 mức; work queue thực tế lọc `("HIGH","CRITICAL")`), `triggered_rules JSON`, `evidence JSON`, `recommended_action Text`, `generated_at`, `resolved_at`, `resolution_type`, `policy_version` (bắt buộc, không default kể từ migration 8).

**InstructorIntervention** (`instructor_interventions`): `id PK`, `risk_signal_id FK risk_signals CASCADE`, `instructor_id FK users`, `action_taken Text`, `status` (PENDING/ACTIVE/COMPLETED), `created_at`.

---

## 5. Cơ chế phân quyền/bảo mật riêng cho Admin

### 5.1 RBAC 2 lớp

```python
# src/security/authorization.py
require_roles(*roles) -> guard: 401 nếu chưa login, 403 nếu role không thuộc roles
require_permission(resource, permission) -> guard: 403 nếu is_allowed(role, resource, permission) == False
```

`is_allowed()` (`src/security/policy.py`): tra `PERMISSION_MATRIX[role][resource]` (frozenset các Permission). Nếu `Permission.MANAGE` nằm trong set đó → coi như có luôn READ/WRITE/DELETE/APPROVE/MANAGE (superset). Ngược lại chỉ permission match chính xác mới pass.

### 5.2 Permission Matrix của `UserRole.ADMIN` (trích `src/security/permissions.py`)

```python
UserRole.ADMIN: {
    Resource.PLAN:             {READ_SENSITIVE},
    Resource.CHAT:              {READ_SENSITIVE},
    Resource.REFLECTION:        {READ_SENSITIVE},
    Resource.SUBMISSION:        {READ_SENSITIVE},
    Resource.STUDENT_DOCUMENT:  {READ_SENSITIVE},
    Resource.RISK:              {READ_SENSITIVE},
    Resource.RISK_CASE:         {READ_SENSITIVE},
    Resource.INTERVENTION:      {READ_SENSITIVE},
    Resource.SESSION:           {READ_SENSITIVE},
    Resource.ASSIGNMENT:        {READ},
    Resource.COURSE:            {READ, WRITE, DELETE},
    Resource.CURRICULUM:        {READ, WRITE, DELETE, APPROVE},
    Resource.KPI:                {READ},
    Resource.AUDIT:              {READ},
    Resource.USER:               {MANAGE},
    Resource.SETTING:            {MANAGE},
    Resource.AI_POLICY:          {READ, WRITE, DELETE, APPROVE},
    Resource.DATA_REQUEST:       {MANAGE},
    Resource.SYSTEM_HEALTH:      {READ},
}
```

Quan sát quan trọng: Admin **không có** `WRITE`/`DELETE` trực tiếp trên các resource "sensitive" (PLAN/CHAT/REFLECTION/...) — chỉ có `READ_SENSITIVE`, tức Admin **chỉ đọc**, không được sửa/xoá dữ liệu học tập của Student/Instructor qua các route quan sát này (đúng với vai trò observability-only).

Enum đầy đủ:
```python
class Permission(StrEnum): READ, READ_SENSITIVE, WRITE, DELETE, APPROVE, MANAGE
class Resource(StrEnum): PLAN, CHAT, REFLECTION, ASSIGNMENT, COURSE, CURRICULUM, KPI, RISK, RISK_CASE,
    INTERVENTION, SESSION, SUBMISSION, STUDENT_DOCUMENT, AUDIT, USER, SETTING, INTEGRATION, AI_POLICY,
    DATA_REQUEST, SYSTEM_HEALTH
```

### 5.3 Audit logging

- `AuditService.log_event(...)` (từ `AuditRepository`) — mọi lời gọi trong Admin backend dùng `commit=False` rồi để handler tự `db.commit()` cùng transaction chính, ĐỂ nếu ghi audit "trong tưởng tượng" thành công nhưng mutation chính rollback thì audit cũng bị rollback theo (atomicity).
- Riêng luồng "sensitive read" (T2, `SensitiveReadExecutor`) và "identified read" (T1, `_audit_identified_read`) có pattern NGƯỢC: **load dữ liệu trước, rồi audit + tự commit riêng ngay trong service, không đợi transaction ngoài** — vì đây là route GET không có mutation gì khác để gộp chung, và fail-closed nghĩa là nếu audit fail thì phải rollback + raise lỗi trước khi handler kịp trả response.
- `_SENSITIVE_KEYS` trong `AuditService` (redaction list rất dài): các key như `password`, `token`, `chat`, `content`, `feedback`, `reflection`, `submission`, `retrievedchunks`, `chunks`, `prompt`, `systemprompt`, `filepath`, `path`... bị thay bằng `REDACTED` khi ghi vào `before_state`/`after_state`/`metadata` — kể cả khi nested nhiều tầng. (Không đọc chi tiết hàm redact, nhưng danh sách key đủ để biết nguyên tắc: mọi audit row PHẢI an toàn để show cho operator khác mà không lộ nội dung học sinh.)
- `CRITICAL_CHANGE_EVENTS` (whitelist hiển thị ở Overview, `admin_observability_repository.py`): `user_status_changed`, `user_access_changed`, `guardrail_rule_updated`, `guardrail_policy_rolled_back`, `risk_policy_published`, `risk_policy_rolled_back`, `admin_settings_updated`, `curriculum_published`, `curriculum_rolled_back`, `curriculum_archived`, `data_request_transitioned`, `data_request_purged`. Có 1 test (`test_every_critical_change_event_is_actually_produced`) đảm bảo danh sách này **khớp thực tế** với các event_type mà code emit — chống "khai báo nhưng không ai emit" hoặc ngược lại.

### 5.4 Org/scope không áp dụng theo nghĩa multi-tenant

Codebase này **không có khái niệm multi-organization** (không có bảng `Organization`) — hệ thống là single-tenant (1 trường học). "Scoping" ở đây là:
- **Class-scope**: Instructor chỉ liên kết với các `CourseSection` họ dạy; Student chỉ liên kết qua `Enrollment`. Admin thao tác đổi role phải tôn trọng scope này (mục 3.1).
- **Subject-scope cho sensitive read**: mọi route T2 đều lọc theo `student_id` ngay trong SQL (JOIN qua chuỗi quan hệ), không bao giờ trust một id lồng trong response để suy luận quyền — ví dụ `study_tasks()` chứng minh ownership qua JOIN `ScheduleBlock→DailyPlan→WeeklyPlan.student_id`, không dựa vào `assignment_id` hay id nào khác truyền từ client.
- **Singleton Admin**: chỉ có đúng 1 tài khoản role=ADMIN toàn hệ thống — ràng buộc kép: DB-level (partial unique index `uq_users_single_admin_role`) + service-level (`AdminAccountService`).

---

## 6. Danh sách file quan trọng kèm mô tả 1 dòng

| File | Mô tả |
|---|---|
| `src/api/admin.py` | Router chính `/admin`: courses, guardrail rules, analytics, curriculum document lifecycle, academic-term |
| `src/api/admin_invitations.py` | Router `/admin/invites`: tạo/revoke/resend/sửa invitation Student-Instructor |
| `src/api/admin_observability.py` | Router quan sát T0/T1/T2: overview, people explorer, 360 view, raw sensitive reads |
| `src/api/admin_observability_schemas.py` | Toàn bộ Pydantic response schema cho observability (allow-list tường minh) |
| `src/api/admin_policy.py` | Router `/admin/risk-policy`: CRUD + preview + rollback chính sách rủi ro |
| `src/api/admin_policy_schemas.py` | Schema risk-policy + admin-settings |
| `src/api/admin_schemas.py` | Schema dùng chung: courses, guardrail rules, documents, users, invitations |
| `src/api/admin_settings.py` | Router `/admin/settings`: auto_risk_alert, default_semester (key-value đơn giản) |
| `src/api/admin_users.py` | Router `/admin/users`: liệt kê, khoá/mở, đổi role+scope |
| `src/api/data_requests.py` | Router DSAR (Student self-service + Admin quản trị `/admin/data-requests/*`) |
| `src/services/admin_account_service.py` | Bootstrap + bất biến "chỉ 1 Admin" |
| `src/services/admin_account_recovery_service.py` | Recovery Admin qua kênh OPS (không qua HTTP) |
| `src/services/admin_data_request_service.py` | Business logic DSAR: transition, preview/confirm xoá dữ liệu |
| `src/services/admin_document_ingest_service.py` | Ingest/replace/delete file curriculum, validate, chunk hoá |
| `src/services/admin_document_lifecycle_service.py` | State machine document: validate→publish→archive→rollback |
| `src/services/admin_document_serializer.py` | Chuẩn hoá 1 Document ORM thành dict trả về client |
| `src/services/admin_ingest_runner.py` | Background worker chạy ingest/replace/delete + cleanup file 2 pha |
| `src/services/admin_observability_read_service.py` | Toàn bộ DTO builder cho T0/T1/T2 (allow-list nghiêm ngặt) |
| `src/services/admin_people_service.py` | Đổi role + class-scope an toàn giao dịch (transfer-safety) |
| `src/services/admin_read_service.py` | Hợp nhất danh sách course từ catalog + override + ingest job |
| `src/services/admin_work_queue_service.py` | Xây Work Queue cho Overview (risk/safety/data-request/ingest) |
| `src/repositories/admin_course_repository.py` | CRUD `AdminCourseOverride` + `CourseIngestJob` |
| `src/repositories/admin_observability_repository.py` | Query T0/T1 (aggregate) + T2 (raw, bounded, phân trang) |
| `src/services/sensitive_read_executor.py` | Cổng duy nhất release dữ liệu T2, audit-before-release, fail-closed |
| `src/security/sensitive_access.py` | Context + exception cho luồng đọc nhạy cảm |
| `src/security/permissions.py` | Enum Permission/Resource + PERMISSION_MATRIX tĩnh |
| `src/security/policy.py` | Hàm quyết định `is_allowed()` |
| `src/security/authorization.py` | FastAPI dependency guard `require_roles`/`require_permission` |
| `src/services/guardrail_rules.py` | 6 nhóm regex guardrail + `GuardrailPolicyService` (publish/restore/rollback) |
| `src/repositories/guardrail_rule_repository.py` | Persist trạng thái enable + versioning snapshot guardrail |
| `src/services/risk_policy_service.py` | `calculate_risk_level()` (2-điều-kiện) + preview + generate_signal |
| `src/repositories/risk_policy_repository.py` | CRUD `RiskPolicy` (không đọc chi tiết, dùng bởi `admin_policy.py`) |
| `src/services/retention_service.py` | Preview/purge dữ liệu cá nhân theo category (CHAT/REFLECTION/PLAN) |
| `migrations/versions/20260828_document_governance.py` | Migration lớn nhất: thêm governance fields + backfill fail-closed cho `documents` |
| `migrations/versions/20260829_single_admin_account.py` | Ràng buộc DB-level "chỉ 1 Admin" |
| `migrations/versions/20260902_admin_access_cases.py` | Tạo schema case/session — hiện KHÔNG có producer dùng (dead schema) |

---

## 7. Nhận xét: điểm mạnh, thiếu sót, so sánh

### 7.1 Điểm mạnh

1. **Tách module rất rõ ràng theo domain** (people/work-queue/document-lifecycle/observability/data-request/ingest-runner/serializer) — mỗi service có đúng 1 trách nhiệm, dễ port từng phần sang nhánh khác độc lập.
2. **Fail-closed nhất quán ở mọi lớp**: catalog curriculum lỗi → 503 thay vì trả dữ liệu rỗng gây hiểu lầm; audit không ghi được → huỷ toàn bộ response đã load (sensitive read); migration backfill thiếu dữ liệu → raise cứng thay vì để NULL âm thầm.
3. **Allow-list tường minh cho mọi DTO nhạy cảm** (T2) — không dùng `from_attributes`/`__dict__`, tránh leak cột mới thêm vào DB một cách "vô tình". Đây là điểm khác biệt lớn so với một Admin implementation thông thường (thường serialize thẳng ORM model).
4. **Ràng buộc bất biến được enforce ở CẢ 2 tầng (DB + service)**: singleton Admin (unique index + service check), 1-published-per-version-group (partial unique index + lifecycle service check) — chống race condition thực sự (đã có xử lý bắt `IntegrityError` cụ thể chứ không chỉ dựa vào application-level check).
5. **Transfer-safety cho đổi role Instructor**: không cho phép 1 thao tác đổi role vô tình khiến 1 Instructor khác mất hết lớp mà không ai biết — kèm audit ghi nhận cả 2 phía của việc chuyển giao. Đây là chi tiết dễ bị bỏ qua ở một implementation Admin "thông thường" (thường chỉ có PATCH role đơn giản, không kiểm tra hệ quả side-effect).
6. **2-pha cleanup file vật lý khi xoá document** (`admin_ingest_runner._run_delete_job`): tách rời transaction DB và filesystem I/O, có cơ chế retry tường minh qua endpoint `retry-cleanup` — xử lý đúng bài toán "distributed transaction giữa DB và disk" mà nhiều hệ thống bỏ qua.
7. **Guardrail rule có core-lock** (2 rule chống prompt-injection/leak không thể bị Admin tắt qua UI) — một lớp bảo vệ chống chính Admin (hoặc tài khoản Admin bị chiếm) tự vô hiệu hoá an toàn hệ thống.
8. **Test coverage rất dày** cho phần Admin: ít nhất 28 file test rải khắp `test_api/`, `test_services/`, `test_repositories/`, `test_migrations/`, `test_frontend/` (contract test), `test_scripts/` — bao gồm cả test đảm bảo router "removed legacy contract" không còn tồn tại (`test_removed_admin_legacy_contract.py`) và test đối soát danh sách `CRITICAL_CHANGE_EVENTS` với producer thực tế.

### 7.2 Điểm cần lưu ý / thiếu sót khi port sang `develop`

1. **Dead schema chưa dọn**: `AdminAccessCase` và `SensitiveAccessSession` (+ 3 cột FK trên `audit_logs` trỏ tới chúng) được tạo bởi migration `20260902_admin_access_cases` nhưng **không có bất kỳ service/route nào trong phạm vi đã đọc ghi dữ liệu vào 2 bảng này nữa** — kiến trúc đã chuyển sang "direct read" (`SensitiveAccessContext.for_direct_read`) không cần case/session/TOTP. Nếu port sang `develop`, cần quyết định: (a) port luôn 2 bảng này dù không dùng (giữ tương thích migration nhưng lãng phí), hoặc (b) bỏ hẳn (rủi ro nếu có phần khác của hệ thống — ví dụ MFA/TOTP flow ở `src/services/mfa_*` không nằm trong phạm vi audit này — vẫn phụ thuộc). **Cần kiểm tra chéo trước khi xoá.**
2. **`data_requests.py` không theo naming convention `admin_*.py`** dù chứa 5/9 route thuộc `/admin/data-requests/*` — nếu người port chỉ tìm file theo pattern `admin_*.py` như đề bài yêu cầu ban đầu sẽ **bỏ sót toàn bộ phần Admin Data Request API**. Đã bổ sung đầy đủ ở mục 2.6 (thực ra 3.10) và 2.6/3.10 phía trên.
3. **RiskPolicy có 2 field "chết"**: `weight_late`/`weight_completion` vẫn bắt buộc trong request (validator tổng=1.0) và vẫn lưu DB, nhưng `calculate_risk_level()` thực tế dùng ma trận 2-điều-kiện (0/1/2 điều kiện kích hoạt → LOW/MEDIUM/HIGH), hoàn toàn không dùng 2 weight này để tính toán. Đây là legacy field giữ lại cho tương thích ngược — nếu port logic mới cần quyết định giữ hay bỏ field.
4. **`AdminSettings.demo_mode` từng tồn tại rồi bị xoá** (comment "ADM-13") — bài học: nhánh `develop` có thể vẫn còn field này nếu chưa đồng bộ, cần audit riêng.
5. **Một số logic dùng `asyncio.run()` lồng trong hàm đồng bộ chạy trong `BackgroundTasks`** (`admin_ingest_runner._log_event`) — cách này hoạt động vì `run_admin_ingest_job` bản thân là hàm sync chạy trong background thread pool của FastAPI, nhưng đây là pattern hơi mong manh (nếu event loop context thay đổi có thể lỗi) — cần giữ nguyên cách gọi khi port, không tự ý đổi sang `await` trực tiếp vì hàm cha không phải coroutine.
6. **Validate lifecycle (`validate()`) tự commit ngay trong service**, khác với hầu hết method khác của cùng class (`publish`/`archive`/`rollback`) cũng tự commit — thực ra khi rà lại, **toàn bộ `AdminDocumentLifecycleService` đều tự commit/rollback nội bộ**, không để handler quyết định. Điều này khác với hầu hết service khác trong Admin backend (đa số để `db.commit()` ở handler). Không phải bug, nhưng là điểm **không nhất quán về convention transaction** giữa các service — cần lưu ý khi viết lại để không vô tình double-commit hoặc quên `db.refresh()`.
7. **So sánh nhanh với một Admin panel "thông thường"**: implementation này **vượt trội** một Admin CRUD tiêu chuẩn ở việc (a) versioned/append-only cho guardrail & risk-policy thay vì update-in-place, (b) audit-before-release cho mọi sensitive read thay vì chỉ audit sau khi trả response (nhiều hệ thống chỉ log fire-and-forget sau response, có thể mất log nếu crash ngay sau đó), (c) DTO allow-list thủ công thay vì serializer tự động. Điểm **yếu hơn** so với một hệ thống multi-tenant chuẩn: **không có khái niệm Organization/tenant** — nếu `develop` cần multi-org, toàn bộ logic scoping ở đây (class-scope, singleton-admin) phải được thiết kế lại từ đầu, không thể port 1-1.
8. **Không tìm thấy TODO/FIXME literal trong các file đã đọc** — codebase khá "sạch" theo nghĩa không để lại nợ kỹ thuật dạng comment; các giới hạn được ghi nhận rõ ràng bằng docstring/comment giải thích lý do thiết kế (ví dụ giải thích tại sao bỏ `generation_metadata`, tại sao `file_path` không xuất hiện) thay vì để TODO mơ hồ.

