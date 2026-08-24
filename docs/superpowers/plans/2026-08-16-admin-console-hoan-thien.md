# Admin Console — Hoàn thiện đủ 7 khu vực (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa Admin Console từ 2 tab dùng mock data lên đủ 7 khu vực chạy bằng API thật, đúng đặc tả `docs/PROJECT_CONTEXT.md` mục 6.5.

**Architecture:** Backend đã có sẵn Curriculum, KPI, Guardrail rules, Audit log và Academic Term với 74 test liên quan đang pass. Các vertical slice đầu nối frontend vào API có sẵn; Người dùng, Lời mời, Risk Policy và Cấu hình xây backend trước rồi mới nối UI. Mọi thao tác ghi của Admin phải sinh Audit log trong cùng transaction. Bản thiết kế đã duyệt nằm tại `docs/superpowers/specs/2026-08-16-admin-console-complete-design.md` và thắng mọi đoạn cũ mâu thuẫn trong plan này.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (`Mapped`/`mapped_column`) + Alembic · React 19 + Vite + Tailwind v4 (không TypeScript) · pytest + pytest-asyncio · Gemini qua `src/services/llm.py`

---

## Global Constraints

Mọi task đều ngầm bao gồm các ràng buộc dưới đây.

- **Python 3.11+**, dòng tối đa **120 ký tự** (`ruff.toml`), quote kép, indent bằng space.
- **Chạy test bằng `.venv/Scripts/python.exe -m pytest`** — `python -m pytest` KHÔNG chạy được, môi trường global không có pytest.
- **Baseline test trước khi bắt đầu: `7 failed, 246 passed, 5 skipped`.** 7 fail này (4× `test_self_study`, `test_lecture_plan`, `test_ownership_module`, `test_plans`) có sẵn trên `origin/develop`, KHÔNG phải do plan này gây ra. Sau mỗi task, số `failed` phải vẫn là 7 — tăng lên là do bạn.
- **Alembic head hiện tại: `20260821_self_study_sessions`.** Migration đầu tiên bạn tạo phải đặt `down_revision = "20260821_self_study_sessions"`; migration thứ hai trỏ vào migration thứ nhất, không cùng trỏ vào head (tránh nhánh song song).
- **Mọi route admin đã được bọc role guard ở cấp router** (`src/api/admin.py:43-47`, `dependencies=[Depends(require_roles(UserRole.ADMIN))]`). Route mới thêm vào router này **không cần** lặp lại `require_roles`, nhưng route ghi dữ liệu **phải** thêm `require_permission(...)` riêng theo đúng pattern của `update_guardrail_rule`.
- **Không tự đăng ký được role cao:** `src/api/auth_schemas.py:5` khoá `RegisterableRole = Literal["STUDENT"]`. Không được nới lỏng dòng này vì bất kỳ lý do gì.
- **Không sửa** `frontend/src/index.css`, `frontend/src/components/shared/`, `frontend/src/context/` — design system dùng chung, phải báo trưởng nhóm (Đăng) trước. Task 2 có bỏ *việc dùng* `INITIAL_COURSES` nhưng **không xoá** nó khỏi `CursusContext.jsx` (role khác vẫn đang dùng).
- **Chuỗi hiển thị phải qua i18n**, thêm key vào **cả hai** `frontend/src/locales/vi.js` và `frontend/src/locales/en.js`, dùng qua `const { t } = useLanguage()`. Không hardcode tiếng Việt trong JSX.
- **Không có test runner cho frontend** (`frontend/package.json` chỉ có `dev`/`build`/`lint`/`preview`). Task frontend vì vậy dùng **contract test ở backend** (pytest, khẳng định shape JSON mà UI dựa vào) làm bước "test đỏ", cộng kiểm chứng bằng trình duyệt ở bước cuối. Không thêm vitest — ngoài phạm vi và tốn thời gian của 7 ngày còn lại.
- **`method_note` là bắt buộc với mọi số liệu KPI** — mọi con số hiển thị cho người dùng phải kèm ghi chú phương pháp đo. Đây là ràng buộc uy tín, không phải trang trí.
- **Đúng 7 khu vực top-level:** `curriculum`, `users`, `invites`, `analytics`, `ai-policy`, `audit`, `settings`. `AdminAcademicCalendar` nằm trong `settings`, không tạo tab thứ 8.
- **KPI tổng luôn hiện phía trên thanh tab**, không chỉ hiện khi mở Analytics.
- **Route lời mời chuẩn là `/api/v1/admin/invites`** theo SRS. Token thô chỉ xuất hiện một lần ở `data.activation_token`, không nằm trong `invitation` và không xuất hiện ở GET list.
- **Guardrail mutation bắt buộc có `change_reason`**; Risk Policy bắt buộc preview, version history, rollback, lưu `policy_version` trên risk signal và audit lý do.
- **Nguồn UI fallback:** file `08-Cursus-UI-UX-Master-Spec.md` bị thiếu trên nhánh này; dùng `docs/frontend/00_AI_CONTEXT_PACK.md` và token thật trong `frontend/src/index.css`. Không tạo palette/layout system mới.
- **Trước khi đặt revision migration**, kiểm tra/đổi số để không trùng migration RLS `20260822` ở nhánh `haidang2425`.

---

## Task 0: Khoá hợp đồng thiết kế đã duyệt

**Files:**
- Read: `docs/superpowers/specs/2026-08-16-admin-console-complete-design.md`
- Modify: `docs/superpowers/plans/2026-08-16-admin-console-hoan-thien.md`

**Interfaces:**
- Produces: một nguồn quyết định duy nhất cho tab, route invite, KPI persistent, policy governance và migration ordering.

- [ ] **Step 1: Kiểm tra không còn quyết định mơ hồ trong plan**

```powershell
Get-Content docs/superpowers/plans/2026-08-16-admin-console-hoan-thien.md |
  Select-Object -Skip 60 |
  rg "admin/invitations|id: 'term'|setGuardrailRule\(code, enabled\)|TBD|TODO"
```

Kỳ vọng: không có route `/admin/invitations`, không có tab top-level `term`, không có guardrail mutation thiếu `changeReason`, không có placeholder.

- [ ] **Step 2: Kiểm tra đúng 7 khu vực trong spec**

```powershell
rg -n "Curriculum|Người dùng|Lời mời|Analytics|Chính sách AI|Audit log|Cấu hình" docs/superpowers/specs/2026-08-16-admin-console-complete-design.md
```

- [ ] **Step 3: Commit plan đã hợp nhất**

```bash
git add docs/superpowers/plans/2026-08-16-admin-console-hoan-thien.md
git commit -m "docs(admin): hop nhat plan voi spec da duyet"
```

---

## File Structure

**Sửa (đã tồn tại):**

| File | Trách nhiệm sau khi sửa |
|---|---|
| `frontend/src/lib/api.js` | Thêm ~15 hàm client admin, nối tiếp khối `academic-term` ở cuối file (dòng 704-724). Đặt ở đây thay vì file mới vì `request()` không được export và các hàm admin sẵn có đã nằm đây. |
| `frontend/src/components/admin/AdminConsole.jsx` | Từ 2 tab → đúng 7 tab; KPI API luôn hiện phía trên tab; bỏ `KPI` hardcode và `INITIAL_COURSES`. |
| `frontend/src/locales/vi.js`, `en.js` | Key i18n cho 5 tab mới. |
| `src/api/admin.py` | Thêm route Cấu hình (Task 12). Các nhóm route lớn tách file riêng. |
| `src/db/models.py` | Model `Invitation`, `RiskPolicy`, `AdminSetting`; thêm `RiskSignal.policy_version`. |

**Tạo mới:**

| File | Trách nhiệm |
|---|---|
| `frontend/src/components/admin/AdminAuditLog.jsx` | Bảng audit log + lọc theo `event_type`. |
| `frontend/src/components/admin/AdminGuardrailRules.jsx` | Bật/tắt rule + ngưỡng risk score. |
| `frontend/src/components/admin/AdminUsers.jsx` | Danh sách tài khoản + khoá/mở. |
| `frontend/src/components/admin/AdminInvitations.jsx` | Gửi/thu hồi lời mời. |
| `frontend/src/components/admin/AdminAnalytics.jsx` | KPI + số liệu tổng hợp. |
| `src/api/admin_users.py` | Route `/admin/users/*`. Tách khỏi `admin.py` (đã 567 dòng). |
| `src/api/admin_invitations.py` | Route `/admin/invites/*`; gửi qua email abstraction hiện có. |
| `src/api/admin_policy.py` | Route `/admin/risk-policy/*`. |
| `src/repositories/invitation_repository.py` | Truy vấn bảng `invitations`. |
| `src/repositories/risk_policy_repository.py` | Truy vấn bảng `risk_policies`, versioning. |
| `migrations/versions/20260822_admin_invitations.py` | Bảng `invitations`. |
| `migrations/versions/20260823_admin_risk_policy.py` | Bảng `risk_policies` + `admin_settings` + `risk_signals.policy_version`; revision ID được đổi nếu RLS đã chiếm số. |
| `tests/test_api/test_admin_users.py`, `test_admin_invitations.py`, `test_admin_policy.py`, `test_admin_contracts.py` | Test cho từng nhóm. |

---

## Task 1: API client admin + contract test

Bước nền — 4 task sau đều gọi các hàm định nghĩa ở đây. Contract test khoá shape JSON để UI không vỡ ngầm khi backend đổi.

**Files:**
- Modify: `frontend/src/lib/api.js` (thêm vào cuối, sau dòng 724)
- Test: `tests/test_api/test_admin_contracts.py` (tạo mới)

**Interfaces:**
- Produces: `listAdminCourses()`, `createAdminCourse({subject_code, subject_name, semester})`, `deleteAdminCourse(code)`, `restoreAdminCourse(code)`, `listCourseDocuments(code)`, `getAdminKpi()`, `listGuardrailRules()`, `setGuardrailRule(code, enabled, changeReason)`, `restoreGuardrailDefaults(changeReason)`, `listAuditEvents({eventType, limit})` — tất cả trả Promise của body JSON đã parse.

- [ ] **Step 1: Viết contract test (đỏ)**

Tạo `tests/test_api/test_admin_contracts.py`:

```python
"""Khoá shape JSON mà Admin Console dựa vào. Vỡ test này = vỡ UI."""

import pytest


@pytest.mark.asyncio
async def test_admin_kpi_shape(client, admin_token):
    response = await client.get(
        "/api/v1/admin/kpi",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert set(data) == {"with_cursus_overall", "baseline_overall", "method_note"}
    assert 0 <= data["with_cursus_overall"] <= 1
    assert 0 <= data["baseline_overall"] <= 1
    assert data["method_note"].strip()


@pytest.mark.asyncio
async def test_guardrail_rules_shape(client, admin_token):
    response = await client.get(
        "/api/v1/admin/guardrail-rules",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data["any_disabled"], bool)
    assert data["rules"], "phải có ít nhất 1 rule sau khi seed"
    rule = data["rules"][0]
    for field in ("code", "name", "description", "enabled", "pattern_count", "updated_at"):
        assert field in rule, f"thiếu field {field}"


@pytest.mark.asyncio
async def test_audit_events_shape(client, admin_token):
    response = await client.get(
        "/api/v1/audit/events?limit=5",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    if events:
        for field in ("id", "event_type", "decision", "metadata", "created_at"):
            assert field in events[0], f"thiếu field {field}"


@pytest.mark.asyncio
async def test_audit_events_denied_for_non_admin(client, student_token):
    response = await client.get(
        "/api/v1/audit/events",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 403
```

Nếu `tests/conftest.py` chưa có fixture `admin_token`/`student_token`, tra cách các test admin sẵn có lấy token (`tests/test_api/test_admin.py`) và dùng đúng cách đó — không tự phát minh cơ chế auth mới.

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_contracts.py -v
```

Kỳ vọng: FAIL vì thiếu fixture, hoặc PASS ngay nếu backend đã đúng shape. **Nếu pass ngay thì tốt** — nghĩa là hợp đồng đã đúng, giữ test lại làm lưới an toàn cho các task sau.

- [ ] **Step 3: Thêm hàm client vào `frontend/src/lib/api.js`**

Nối tiếp sau `deleteCourseExam` (dòng 724):

```javascript
// ---- Admin Console ----------------------------------------------------------

export function listAdminCourses() {
  return request('/admin/courses');
}

export function createAdminCourse({ subject_code, subject_name, semester }) {
  return request('/admin/courses', {
    method: 'POST',
    body: { subject_code, subject_name, semester },
  });
}

export function deleteAdminCourse(code) {
  return request(`/admin/courses/${encodeURIComponent(code)}`, { method: 'DELETE' });
}

export function restoreAdminCourse(code) {
  return request(`/admin/courses/${encodeURIComponent(code)}/restore`, { method: 'POST' });
}

export function listCourseDocuments(code) {
  return request(`/admin/courses/${encodeURIComponent(code)}/documents`);
}

export function getAdminKpi() {
  return request('/admin/kpi');
}

export function listGuardrailRules() {
  return request('/admin/guardrail-rules');
}

export function setGuardrailRule(code, enabled, changeReason) {
  return request(`/admin/guardrail-rules/${encodeURIComponent(code)}`, {
    method: 'PATCH',
    body: { enabled, change_reason: changeReason },
  });
}

export function restoreGuardrailDefaults(changeReason) {
  return request('/admin/guardrail-rules/restore-defaults', {
    method: 'POST',
    body: { change_reason: changeReason },
  });
}

export function listAuditEvents({ eventType, limit = 100 } = {}) {
  const params = new URLSearchParams();
  if (eventType) params.set('event_type', eventType);
  params.set('limit', String(limit));
  return request(`/audit/events?${params.toString()}`);
}
```

- [ ] **Step 4: Chạy lint frontend + test backend**

```bash
cd frontend && npm run lint
```

Kỳ vọng: không có lỗi mới.

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
```

Kỳ vọng: `7 failed, 250 passed` (246 + 4 test contract mới).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.js tests/test_api/test_admin_contracts.py
git commit -m "feat(admin): api client + contract test cho Admin Console"
```

---

## Task 2: Curriculum tab dùng API thật

Bỏ mock. Đây là khu vực 1 trong 7 khu vực của `PROJECT_CONTEXT` mục 6.5.

**Files:**
- Modify: `frontend/src/components/admin/AdminConsole.jsx:3` (bỏ import `INITIAL_COURSES`), `:37-39` (bỏ `useEffect` seed mock), `:41-50` (handler add/delete gọi API)
- Test: `tests/test_api/test_admin_contracts.py` (thêm 1 test)

**Interfaces:**
- Consumes: `listAdminCourses`, `createAdminCourse`, `deleteAdminCourse` từ Task 1.
- Produces: state `courses` trong `AdminConsole` giờ là mảng object có `subject_code`, `subject_name`, `ingest_status`, `chunk_count` — các tab sau đọc lại shape này.

- [ ] **Step 1: Viết test khoá shape danh sách môn (đỏ)**

Thêm vào `tests/test_api/test_admin_contracts.py`:

```python
@pytest.mark.asyncio
async def test_admin_courses_shape(client, admin_token):
    response = await client.get(
        "/api/v1/admin/courses",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    courses = body["data"]["courses"]
    assert isinstance(courses, list)
    if courses:
        course = courses[0]
        for field in ("subject_code", "subject_name", "ingest_status"):
            assert field in course, f"thiếu field {field}"
        assert course["ingest_status"] in {
            "ingested",
            "processing",
            "not_ingested",
            "failed",
        }
```

Lưu ý: 4 giá trị `ingest_status` trên phải khớp đúng khoá của `STATUS_CFG` ở `AdminConsole.jsx:14-19`. Nếu backend trả giá trị khác, sửa `STATUS_CFG` chứ đừng sửa test cho vừa.

- [ ] **Step 2: Chạy test**

```bash
.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_contracts.py::test_admin_courses_shape -v
```

Nếu FAIL vì tên field lệch: đọc `src/api/admin_schemas.py` lấy tên thật, sửa test cho đúng thực tế rồi tiếp.

- [ ] **Step 3: Sửa `AdminConsole.jsx` gọi API**

Thay dòng 3:

```javascript
import { useLanguage } from '../../context/LanguageContext';
import { listAdminCourses, createAdminCourse, deleteAdminCourse } from '../../lib/api';
```

(Bỏ hẳn dòng `import { INITIAL_COURSES, useCursus } ...`. **Không** xoá `INITIAL_COURSES` khỏi `CursusContext.jsx` — file đó thuộc `context/`, đang bị khoá, và role khác vẫn dùng.)

Thay state + effect (dòng 31-39):

```javascript
const [courses, setCourses] = useState([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);

const reloadCourses = useCallback(async () => {
  setLoading(true);
  setError(null);
  try {
    const body = await listAdminCourses();
    setCourses(body.data.courses);
  } catch (err) {
    setError(err.message || t('admin.loadFailed'));
  } finally {
    setLoading(false);
  }
}, [t]);

useEffect(() => { reloadCourses(); }, [reloadCourses]);
```

Nhớ thêm `useCallback` vào import React ở dòng 1.

Thay `handleAdd` (dòng 41-46):

```javascript
async function handleAdd() {
  if (!form.subject_code.trim() || !form.subject_name.trim()) return;
  try {
    await createAdminCourse(form);
    setForm({ subject_code: '', subject_name: '', semester: 'Fall 2026' });
    setShowAdd(false);
    await reloadCourses();
  } catch (err) {
    setError(err.message || t('admin.createFailed'));
  }
}
```

Thêm handler xoá đầy đủ:

```javascript
async function handleDelete(code) {
  setError(null);
  try {
    await deleteAdminCourse(code);
    await reloadCourses();
  } catch (err) {
    setError(err.message || t('admin.deleteFailed'));
  }
}
```

- [ ] **Step 4: Thêm key i18n**

Vào cả `frontend/src/locales/vi.js` và `en.js`, trong object `admin`:

```javascript
// vi.js
loadFailed: 'Không tải được danh sách môn học.',
createFailed: 'Không thêm được môn học.',
deleteFailed: 'Không xoá được môn học.',
loading: 'Đang tải…',
```

```javascript
// en.js
loadFailed: 'Could not load the course list.',
createFailed: 'Could not add the course.',
deleteFailed: 'Could not delete the course.',
loading: 'Loading…',
```

- [ ] **Step 5: Kiểm chứng trên trình duyệt**

Khởi động backend + frontend, đăng nhập bằng tài khoản admin demo (`admin.demo@example.test` / `AdminPassword123`, xem `frontend/src/lib/api.js:372`), mở `/admin`.

Xác nhận **bằng mắt**: bảng môn học hiện dữ liệu từ DB (không phải 3 dòng mock cũ), thêm 1 môn thấy nó xuất hiện sau reload, tắt backend thì hiện thông báo lỗi chứ không phải bảng trống im lặng.

- [ ] **Step 6: Chạy lint + test, rồi commit**

```bash
cd frontend && npm run lint
```

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
```

Kỳ vọng: vẫn `7 failed`, passed tăng 1.

```bash
git add frontend/src/components/admin/AdminConsole.jsx frontend/src/locales/ tests/test_api/test_admin_contracts.py
git commit -m "feat(admin): bang curriculum doc tu /admin/courses thay vi mock"
```

---

## Task 2B: Tải tài liệu môn học lên

Đây là **năng lực số 5 trong mục 11** của `PROJECT_CONTEXT` ("Phòng đào tạo tải tài liệu môn học thật lên hệ thống, không chỉ nhập tên môn") và là dòng 🔜 của khu vực Curriculum ở mục 6.5. Backend đã xong hoàn toàn — `POST /admin/courses/{code}/documents` nhận multipart, trả `202` kèm ingest job, chạy nền qua `BackgroundTasks`.

**Files:**
- Modify: `frontend/src/lib/api.js` (upload cần `FormData`, không dùng được `request()` thường), `frontend/src/components/admin/AdminConsole.jsx`
- Test: `tests/test_api/test_admin_contracts.py`

**Interfaces:**
- Consumes: `POST /admin/courses/{code}/documents` — multipart, field tên **`file`** (xem `src/api/admin.py:371`), trả `202` + ingest job.
- Produces: `uploadCourseDocument(code, file)`, `deleteCourseDocument(code, documentId)`.

- [ ] **Step 1: Viết test khoá hợp đồng upload (đỏ)**

```python
@pytest.mark.asyncio
async def test_upload_document_returns_ingest_job(client, admin_token, seeded_course_code):
    response = await client.post(
        f"/api/v1/admin/courses/{seeded_course_code}/documents",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("syllabus.txt", b"Tuan 1: gioi thieu mon hoc.", "text/plain")},
    )
    assert response.status_code == 202, "upload phải trả 202 vì ingest chạy nền"
    body = response.json()
    assert body["success"] is True


@pytest.mark.asyncio
async def test_student_cannot_upload_document(client, student_token, seeded_course_code):
    response = await client.post(
        f"/api/v1/admin/courses/{seeded_course_code}/documents",
        headers={"Authorization": f"Bearer {student_token}"},
        files={"file": ("x.txt", b"noi dung", "text/plain")},
    )
    assert response.status_code == 403
```

Fixture `seeded_course_code` trả mã một môn có sẵn trong demo dataset — lấy từ `listAdminCourses` hoặc tra `tests/conftest.py` xem dataset seed môn nào.

- [ ] **Step 2: Chạy test**

```bash
.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_contracts.py -k upload -v
```

- [ ] **Step 3: Thêm hàm upload vào `frontend/src/lib/api.js`**

`request()` gắn `Content-Type: application/json` nên **không dùng được cho multipart** — trình duyệt phải tự đặt boundary. Đọc `rawFetch` trong `api.js` để lấy đúng cách gắn base URL và cookie, rồi viết:

```javascript
export async function uploadCourseDocument(code, file) {
  const form = new FormData();
  form.append('file', file);
  const response = await fetch(
    `${API_BASE}/admin/courses/${encodeURIComponent(code)}/documents`,
    { method: 'POST', body: form, credentials: 'include' },
  );
  if (!response.ok) {
    throw new ApiError('Tải tài liệu thất bại.', 'UPLOAD_FAILED', response.status);
  }
  return response.json();
}

export function deleteCourseDocument(code, documentId) {
  return request(
    `/admin/courses/${encodeURIComponent(code)}/documents/${encodeURIComponent(documentId)}`,
    { method: 'DELETE' },
  );
}
```

**Không** đặt header `Content-Type` thủ công. Kiểm tra tên biến base URL thật trong `api.js` trước khi dùng `API_BASE` — nếu tên khác thì sửa theo file.

- [ ] **Step 4: Thêm nút tải lên vào bảng curriculum**

Mỗi dòng môn học thêm 1 nút mở `<input type="file" hidden />`. Sau khi upload trả `202`, hiện trạng thái `processing` và **poll lại `listAdminCourses()` mỗi 3 giây, tối đa 10 lần**, dừng khi `ingest_status` chuyển sang `ingested` hoặc `failed`. Không poll vô hạn — ingest lỗi thì vòng lặp không bao giờ dừng.

Hiện `chunk_count` bên cạnh trạng thái để chứng minh tài liệu đã thật sự vào vector store.

- [ ] **Step 5: Kiểm chứng + commit**

Tải lên một file `.txt` thật, xem trạng thái đi từ `processing` → `ingested` và `chunk_count` tăng từ 0. Sau đó sang khu vực Q&A của sinh viên hỏi một câu về nội dung file vừa tải — câu trả lời phải trích được nguồn từ đó. Đây là bằng chứng end-to-end mạnh nhất cho phần demo.

```bash
git add frontend/src/ tests/test_api/test_admin_contracts.py
git commit -m "feat(admin): tai tai lieu mon hoc len + theo doi trang thai ingest"
```

---

## Task 3: KPI persistent + Analytics tab từ dữ liệu thật

Khu vực 4 trong mục 6.5. Đây là chỗ `progress/CHUNG.md` đang tick `[x]` cho "KPI hardcode đã bị xoá" trong khi code vẫn hardcode — task này làm cho lời tick đó thành sự thật.

**Files:**
- Create: `frontend/src/components/admin/AdminAnalytics.jsx`
- Modify: `frontend/src/components/admin/AdminConsole.jsx:7-12` (xoá hằng `KPI`), khối render KPI (dòng ~96-135)
- Test: `tests/test_api/test_admin_contracts.py` (đã có `test_admin_kpi_shape` từ Task 1)

**Interfaces:**
- Consumes: `getAdminKpi()` trả `{success: true, data: {with_cursus_overall, baseline_overall, method_note}}`.
- Produces: `<AdminKpiSummary />` luôn render phía trên tabs và `<AdminAnalytics />` render chi tiết trong tab `analytics`; cả hai chỉ dùng dữ liệu API.

- [ ] **Step 1: Xác nhận test KPI vẫn xanh**

```bash
.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_contracts.py::test_admin_kpi_shape -v
```

Kỳ vọng: PASS. Đây là hợp đồng UI sắp dựa vào.

- [ ] **Step 2: Tạo `AdminAnalytics.jsx`**

```javascript
import React, { useEffect, useState } from 'react';
import { TrendingUp, AlertCircle } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getAdminKpi } from '../../lib/api';

export default function AdminAnalytics() {
  const { t } = useLanguage();
  const [kpi, setKpi] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getAdminKpi()
      .then((body) => { if (!cancelled) setKpi(body.data); })
      .catch((err) => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; };
  }, []);

  if (error) {
    return (
      <div className="flex items-center gap-2 text-xs text-danger">
        <AlertCircle size={14} /> {error}
      </div>
    );
  }
  if (!kpi) return <p className="text-xs text-fg-secondary">{t('admin.loading')}</p>;

  const delta = kpi.with_cursus_overall - kpi.baseline_overall;

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2">
        <TrendingUp size={15} className="text-slate-500" />
        <h2 className="text-sm font-bold">{t('admin.kpiTotalTitle')}</h2>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <Stat label={t('admin.kpiWithCursus')} value={pct(kpi.with_cursus_overall)} />
        <Stat label={t('admin.kpiBaseline')} value={pct(kpi.baseline_overall)} />
        <Stat label={t('admin.kpiDelta')} value={`${delta >= 0 ? '+' : ''}${pct(delta)}`} />
      </div>
      <p className="text-[11px] leading-relaxed text-fg-secondary">
        <strong>{t('admin.methodNoteLabel')}:</strong> {kpi.method_note}
      </p>
    </section>
  );
}

function pct(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function Stat({ label, value }) {
  return (
    <div className="rounded-lg border border-line p-3">
      <p className="text-[11px] text-fg-secondary">{label}</p>
      <p className="text-lg font-bold">{value}</p>
    </div>
  );
}
```

`method_note` hiển thị **luôn luôn**, không giấu sau nút "xem thêm" — đây là ràng buộc uy tín ở Global Constraints. Tách phần KPI trong ví dụ thành `AdminKpiSummary.jsx`, render component này trong `AdminConsole.jsx` trước thanh tabs. `AdminAnalytics.jsx` không được là nơi duy nhất hiển thị KPI.

- [ ] **Step 3: Xoá hardcode khỏi `AdminConsole.jsx`**

Xoá hẳn hằng `KPI` (dòng 7-12). Import `AdminAnalytics` và render nó ở tab `analytics`. Nếu chỗ nào còn đọc `KPI.with_cursus` / `KPI.method_note` / `KPI.method_note_en`, thay bằng `<AdminAnalytics />`.

Xác nhận không còn sót:

```bash
grep -n "KPI\b\|0.78\|0.45" frontend/src/components/admin/AdminConsole.jsx
```

Kỳ vọng: không ra dòng nào.

- [ ] **Step 4: Thêm key i18n**

`vi.js`: `kpiWithCursus: 'Có dùng Cursus'`, `kpiBaseline: 'Không dùng'`, `kpiDelta: 'Chênh lệch'`, `methodNoteLabel: 'Cách đo'`.
`en.js`: `kpiWithCursus: 'With Cursus'`, `kpiBaseline: 'Without'`, `kpiDelta: 'Difference'`, `methodNoteLabel: 'Method'`.

- [ ] **Step 5: Thêm endpoint số liệu tổng hợp**

`GET /admin/kpi` chỉ trả 2 tỷ lệ. Mục 6.5 còn đòi Analytics hiện **số môn đã nạp, tổng tài liệu đã nạp, số sinh viên có nguy cơ toàn hệ thống**. Hai số đầu tính được từ `listAdminCourses()` ngay ở frontend (đếm `ingest_status === 'ingested'`, cộng `chunk_count`) — không cần backend. Số thứ ba thì cần endpoint mới.

Viết test trước, vào `tests/test_api/test_admin_contracts.py`:

```python
@pytest.mark.asyncio
async def test_analytics_summary_shape(client, admin_token):
    response = await client.get(
        "/api/v1/admin/analytics/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["at_risk_students"] >= 0
    assert data["ingested_courses"] >= 0
    assert data["total_chunks"] >= 0
    assert isinstance(data["weekly_comparison"], list)
    assert data["weekly_comparison"], "phải có chuỗi tuần từ seed hiện hành"
    for point in data["weekly_comparison"]:
        assert set(point) == {"week", "with_cursus", "baseline", "sample_size"}
    assert data["method_note"].strip(), "mọi số liệu phải kèm cách đo"
```

Thêm schema vào `src/api/admin_schemas.py`:

```python
class AdminWeeklyComparisonPoint(BaseModel):
    week: int = Field(ge=1)
    with_cursus: float = Field(ge=0.0, le=1.0)
    baseline: float = Field(ge=0.0, le=1.0)
    sample_size: int = Field(ge=1)


class AdminAnalyticsSummaryData(BaseModel):
    at_risk_students: int = Field(ge=0)
    ingested_courses: int = Field(ge=0)
    total_courses: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    weekly_comparison: list[AdminWeeklyComparisonPoint]
    method_note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AdminAnalyticsSummaryResponse(BaseModel):
    success: Literal[True]
    data: AdminAnalyticsSummaryData
```

Rồi thêm route vào `src/api/admin.py` (nhớ bổ sung import `from sqlalchemy import func, select` và `RiskSignal` từ `src.db.models` — kiểm tra dòng import đầu file trước, đừng thêm trùng):

```python
@router.get("/analytics/summary", response_model=AdminAnalyticsSummaryResponse)
async def analytics_summary(
    read_service: AdminReadService = Depends(get_admin_read_service),
    db: Session = Depends(get_db),
) -> AdminAnalyticsSummaryResponse:
    courses = read_service.list_courses()["courses"]
    at_risk = db.execute(
        select(func.count(func.distinct(RiskSignal.student_id))).where(
            RiskSignal.resolved_at.is_(None),
            RiskSignal.risk_level.in_(("MEDIUM", "HIGH")),
        )
    ).scalar_one()

    return AdminAnalyticsSummaryResponse(
        success=True,
        data={
            "at_risk_students": int(at_risk),
            "ingested_courses": sum(1 for c in courses if c["ingest_status"] == "ingested"),
            "total_courses": len(courses),
            "total_chunks": sum(c.get("chunk_count") or 0 for c in courses),
            "weekly_comparison": read_service.get_weekly_comparison(),
            "method_note": (
                "Sinh viên nguy cơ = số student_id riêng biệt có risk_signal mức MEDIUM/HIGH "
                "chưa xử lý tại thời điểm gọi. Chuỗi tuần đọc từ hai kịch bản mô phỏng độc lập "
                "trong seed SSA101, n=12; đây là liên hệ mô phỏng, không phải bằng chứng nhân quả."
            ),
        },
    )
```

Thêm `AdminReadService.get_weekly_comparison()` đọc `with_cursus_avg_by_week`, `baseline_no_cursus_avg_by_week` và `class_summary.class_size` từ snapshot hiện hành; validate hai mảng cùng độ dài, ratio nằm trong `[0, 1]`, và trả danh sách `{week, with_cursus, baseline, sample_size}`. Thiếu/sai dữ liệu phải raise `AdminDataUnavailable`, không tự điền số.

`method_note` ở đây nêu rõ tử số/mẫu số/thời điểm — đúng quy tắc metric trong bản brief B2B mục 6. Đừng rút gọn nó thành một câu chung chung.

Chạy:

```bash
.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_contracts.py -k analytics -v
```

- [ ] **Step 6: Hiện số liệu tổng hợp trong `AdminAnalytics.jsx`**

Thêm hàng 3 ô số dưới khối KPI: số môn đã nạp (dạng `7/48`), tổng số chunk tài liệu, số sinh viên nguy cơ. Mỗi ô có tooltip hoặc dòng nhỏ ghi `method_note` tương ứng.

Hiện biểu đồ/bảng xu hướng theo tuần từ `weekly_comparison` của endpoint. Dữ liệu phải đọc từ seed/dataset xác định mà KPI đang dùng; không sinh random. Mỗi điểm hiện `sample_size`, và `method_note` nói rõ dữ liệu mô phỏng, không tuyên bố quan hệ nhân quả.

- [ ] **Step 7: Kiểm chứng trên trình duyệt + commit**

Mở tab Analytics, xác nhận số hiện ra **khác** 78.0% / 45.0% nếu DB có dữ liệu khác — nếu vẫn đúng 2 số cũ, kiểm tra lại xem có thật sự gọi API không (mở tab Network).

```bash
git add frontend/src/components/admin/ frontend/src/locales/ src/api/ tests/
git commit -m "feat(admin): tab Analytics doc KPI + so lieu tong hop tu API"
```

---

## Task 4: Audit Log UI

Khu vực 6. Backend `GET /audit/events` đã xong và đã có role guard (`src/api/audit.py:12-19`), chỉ thiếu UI.

**Files:**
- Create: `frontend/src/components/admin/AdminAuditLog.jsx`
- Modify: `frontend/src/components/admin/AdminConsole.jsx` (thêm tab)
- Test: đã có `test_audit_events_shape` + `test_audit_events_denied_for_non_admin` từ Task 1

**Interfaces:**
- Consumes: `listAuditEvents({eventType, limit})` trả **mảng phẳng** (không bọc `{success, data}` — khác các endpoint admin khác, đừng nhầm).

- [ ] **Step 1: Xác nhận 2 test audit vẫn xanh**

```bash
.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_contracts.py -k audit -v
```

Kỳ vọng: 2 PASS.

- [ ] **Step 2: Tạo `AdminAuditLog.jsx`**

```javascript
import React, { useCallback, useEffect, useState } from 'react';
import { ScrollText, AlertCircle } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { listAuditEvents } from '../../lib/api';

const EVENT_FILTERS = ['', 'guardrail_rule_updated', 'course_created', 'course_deleted'];

export default function AdminAuditLog() {
  const { t } = useLanguage();
  const [events, setEvents] = useState([]);
  const [eventType, setEventType] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setEvents(await listAuditEvents({ eventType, limit: 100 }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [eventType]);

  useEffect(() => { load(); }, [load]);

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ScrollText size={15} className="text-slate-500" />
          <h2 className="text-sm font-bold">{t('admin.auditLogTitle')}</h2>
        </div>
        <select
          value={eventType}
          onChange={(e) => setEventType(e.target.value)}
          className="rounded border border-line px-2 py-1 text-xs"
        >
          {EVENT_FILTERS.map((value) => (
            <option key={value || 'all'} value={value}>
              {value || t('admin.auditAllEvents')}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <p className="flex items-center gap-2 text-xs text-danger">
          <AlertCircle size={14} /> {error}
        </p>
      )}
      {loading && <p className="text-xs text-fg-secondary">{t('admin.loading')}</p>}
      {!loading && !error && events.length === 0 && (
        <p className="text-xs text-fg-secondary">{t('admin.auditEmpty')}</p>
      )}

      {events.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-line text-fg-secondary">
                <th className="py-2 pr-3">{t('admin.auditTime')}</th>
                <th className="py-2 pr-3">{t('admin.auditEvent')}</th>
                <th className="py-2 pr-3">{t('admin.auditActor')}</th>
                <th className="py-2 pr-3">{t('admin.auditDecision')}</th>
                <th className="py-2">{t('admin.auditResource')}</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id} className="border-b border-line/50">
                  <td className="py-2 pr-3 whitespace-nowrap">
                    {new Date(event.created_at).toLocaleString()}
                  </td>
                  <td className="py-2 pr-3 font-mono">{event.event_type}</td>
                  <td className="py-2 pr-3">{event.actor_user_id || '—'}</td>
                  <td className="py-2 pr-3">{event.decision}</td>
                  <td className="py-2">
                    {event.resource_type ? `${event.resource_type}:${event.resource_id ?? ''}` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
```

Bảng nằm trong `overflow-x-auto` — bắt buộc, thang điểm BTC có mục responsive (tối thiểu 7đ).

- [ ] **Step 3: Thêm tab vào `AdminConsole.jsx`**

`AdminConsole.jsx` hiện dùng 2 nút cứng cho tab. Đổi sang mảng để 7 tab không phải copy-paste 7 lần:

```javascript
const TABS = [
  { id: 'curriculum', labelKey: 'admin.tabCurriculum' },
  { id: 'users',      labelKey: 'admin.tabUsers' },
  { id: 'invites',    labelKey: 'admin.tabInvites' },
  { id: 'analytics',  labelKey: 'admin.tabAnalytics' },
  { id: 'ai-policy',  labelKey: 'admin.tabGuardrail' },
  { id: 'audit',      labelKey: 'admin.tabAudit' },
  { id: 'settings',   labelKey: 'admin.tabSettings' },
];
```

Render bằng `TABS.map(...)`, giữ nguyên class active/inactive đang có ở dòng 75-89. `AdminAcademicCalendar` được chuyển vào panel `settings`; không giữ tab `term`. Tab chưa có component (users/invites/settings ở task sau) tạm render `t('admin.comingSoon')`, không render trang trắng.

- [ ] **Step 4: Thêm key i18n**

`vi.js`: `tabAnalytics: 'Phân tích'`, `tabGuardrail: 'Chính sách AI'`, `tabAudit: 'Nhật ký'`, `tabUsers: 'Người dùng'`, `tabInvites: 'Lời mời'`, `auditAllEvents: 'Tất cả sự kiện'`, `auditEmpty: 'Chưa có sự kiện nào.'`, `auditTime: 'Thời điểm'`, `auditEvent: 'Sự kiện'`, `auditActor: 'Người thực hiện'`, `auditDecision: 'Kết quả'`, `auditResource: 'Đối tượng'`, `comingSoon: 'Đang xây dựng.'`
`en.js`: `tabAnalytics: 'Analytics'`, `tabGuardrail: 'AI policy'`, `tabAudit: 'Audit log'`, `tabUsers: 'Users'`, `tabInvites: 'Invitations'`, `auditAllEvents: 'All events'`, `auditEmpty: 'No events yet.'`, `auditTime: 'Time'`, `auditEvent: 'Event'`, `auditActor: 'Actor'`, `auditDecision: 'Decision'`, `auditResource: 'Resource'`, `comingSoon: 'Under construction.'`.

- [ ] **Step 5: Kiểm chứng + commit**

Mở tab Nhật ký. Trước đó vào tab Chính sách AI bật/tắt 1 rule để sinh sự kiện `guardrail_rule_updated`, rồi quay lại xem nó có xuất hiện không. Đăng nhập bằng tài khoản sinh viên rồi gọi thẳng `/api/v1/audit/events` — phải nhận 403.

```bash
git add frontend/src/components/admin/ frontend/src/locales/
git commit -m "feat(admin): them UI Audit Log doc /audit/events"
```

---

## Task 5: Guardrail Rules UI

Khu vực 5a. Backend `GET`/`PATCH`/`restore-defaults` đã xong với 11 test.

**Files:**
- Create: `frontend/src/components/admin/AdminGuardrailRules.jsx`
- Modify: `AdminConsole.jsx` (nối tab `guardrail`)

**Interfaces:**
- Consumes: `listGuardrailRules()` → `{data: {rules: [...], any_disabled: bool}}`; `setGuardrailRule(code, enabled, changeReason)` → `{data: {rule, any_disabled}}`; `restoreGuardrailDefaults(changeReason)`.

- [ ] **Step 1: Viết test khẳng định tắt rule có ghi audit (đỏ)**

Thêm vào `tests/test_api/test_admin_contracts.py`:

```python
@pytest.mark.asyncio
async def test_disabling_rule_writes_audit_event(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    rules = (await client.get("/api/v1/admin/guardrail-rules", headers=headers)).json()
    code = rules["data"]["rules"][0]["code"]

    patch = await client.patch(
        f"/api/v1/admin/guardrail-rules/{code}",
        headers=headers,
        json={"enabled": False, "change_reason": "Kiểm tra rule trước buổi demo"},
    )
    assert patch.status_code == 200
    assert patch.json()["data"]["any_disabled"] is True

    events = (
        await client.get(
            "/api/v1/audit/events?event_type=guardrail_rule_updated&limit=5",
            headers=headers,
        )
    ).json()
    assert any(e["resource_id"] == code for e in events), "tắt rule phải ghi audit"
    assert events[0]["metadata"]["change_reason"] == "Kiểm tra rule trước buổi demo"


@pytest.mark.asyncio
async def test_guardrail_change_reason_is_required(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    rules = (await client.get("/api/v1/admin/guardrail-rules", headers=headers)).json()
    code = rules["data"]["rules"][0]["code"]
    response = await client.patch(
        f"/api/v1/admin/guardrail-rules/{code}",
        headers=headers,
        json={"enabled": False},
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Chạy test**

```bash
.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_contracts.py::test_disabling_rule_writes_audit_event -v
```

Kỳ vọng: PASS (backend đã ghi audit ở `src/api/admin.py:203-211`). Nếu FAIL, sửa backend chứ đừng bỏ test — audit cho thao tác admin là bắt buộc theo mục 6.5.

- [ ] **Step 3: Tạo `AdminGuardrailRules.jsx`**

```javascript
import React, { useCallback, useEffect, useState } from 'react';
import { ShieldCheck, AlertTriangle, RotateCcw } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { listGuardrailRules, setGuardrailRule, restoreGuardrailDefaults } from '../../lib/api';

export default function AdminGuardrailRules() {
  const { t } = useLanguage();
  const [rules, setRules] = useState([]);
  const [anyDisabled, setAnyDisabled] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(null);
  const [changeReason, setChangeReason] = useState('');

  const load = useCallback(async () => {
    try {
      const body = await listGuardrailRules();
      setRules(body.data.rules);
      setAnyDisabled(body.data.any_disabled);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function toggle(code, enabled) {
    setBusy(code);
    setError(null);
    try {
      const body = await setGuardrailRule(code, enabled, changeReason);
      setAnyDisabled(body.data.any_disabled);
      setChangeReason('');
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2">
        <ShieldCheck size={15} className="text-slate-500" />
        <h2 className="text-sm font-bold">{t('admin.guardrailTitle')}</h2>
      </div>

      <p className="text-[11px] text-fg-secondary">{t('admin.guardrailPatternNote')}</p>

      {anyDisabled && (
        <p className="flex items-center gap-2 rounded border border-warning/40 bg-warning/10 p-2 text-xs">
          <AlertTriangle size={14} /> {t('admin.guardrailDisabledWarning')}
        </p>
      )}
      {error && <p className="text-xs text-danger">{error}</p>}

      <label className="block text-xs font-semibold">
        {t('admin.guardrailChangeReason')}
        <textarea
          value={changeReason}
          onChange={(event) => setChangeReason(event.target.value)}
          className="mt-1 w-full rounded border border-line p-2 text-xs"
        />
      </label>

      <ul className="space-y-2">
        {rules.map((rule) => (
          <li key={rule.code} className="flex items-start justify-between gap-3 rounded-lg border border-line p-3">
            <div className="min-w-0">
              <p className="text-xs font-bold">{rule.name}</p>
              <p className="text-[11px] text-fg-secondary">{rule.description}</p>
              <p className="mt-1 text-[11px] text-fg-secondary">
                {t('admin.guardrailPatternCount', { count: rule.pattern_count })}
              </p>
            </div>
            <button
              type="button"
              disabled={busy === rule.code || changeReason.trim().length < 5}
              onClick={() => toggle(rule.code, !rule.enabled)}
              className={`shrink-0 rounded px-3 py-1 text-xs font-bold ${
                rule.enabled ? 'bg-accent text-white' : 'border border-line text-fg-secondary'
              }`}
            >
              {rule.enabled ? t('admin.guardrailOn') : t('admin.guardrailOff')}
            </button>
          </li>
        ))}
      </ul>

      <button
        type="button"
        disabled={changeReason.trim().length < 5}
        onClick={async () => {
          await restoreGuardrailDefaults(changeReason);
          setChangeReason('');
          await load();
        }}
        className="flex items-center gap-2 text-xs text-fg-secondary underline"
      >
        <RotateCcw size={13} /> {t('admin.guardrailRestore')}
      </button>
    </section>
  );
}
```

Dòng `guardrailPatternNote` là **bắt buộc** — mục 6.5 ghi rõ "không sửa được nội dung pattern/regex ở đây". UI phải nói thẳng điều đó để không ai tưởng sửa được.

Nếu hàm `t()` của dự án không nhận tham số thứ hai, thay `t('admin.guardrailPatternCount', {count})` bằng `` `${rule.pattern_count} ${t('admin.guardrailPatternsWord')}` ``. Kiểm tra chữ ký `t` trong `frontend/src/context/LanguageContext.jsx` trước khi viết.

- [ ] **Step 4: Thêm key i18n**

`vi.js`: `guardrailTitle: 'Chính sách AI — luật chặn'`, `guardrailPatternNote: 'Bật/tắt được từng luật ở đây. Nội dung pattern/regex chỉ sửa được qua code.'`, `guardrailDisabledWarning: 'Đang có luật bị tắt — liêm chính học thuật giảm.'`, `guardrailOn: 'Đang bật'`, `guardrailOff: 'Đang tắt'`, `guardrailRestore: 'Khôi phục mặc định'`, `guardrailPatternsWord: 'pattern'`, `guardrailChangeReason: 'Lý do thay đổi'`.
`en.js`: `guardrailTitle: 'AI policy — blocking rules'`, `guardrailPatternNote: 'Rules can be enabled or disabled here. Pattern/regex content is changed in code.'`, `guardrailDisabledWarning: 'One or more rules are disabled — academic-integrity protection is reduced.'`, `guardrailOn: 'Enabled'`, `guardrailOff: 'Disabled'`, `guardrailRestore: 'Restore defaults'`, `guardrailPatternsWord: 'patterns'`, `guardrailChangeReason: 'Reason for change'`.

- [ ] **Step 5: Kiểm chứng + commit**

Bật/tắt 1 rule, F5 lại trang — trạng thái phải giữ nguyên (nghĩa là đã ghi DB thật, không phải state React). Sang tab Nhật ký xem sự kiện tương ứng.

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
```

```bash
git add frontend/src/components/admin/ frontend/src/locales/ tests/test_api/test_admin_contracts.py
git commit -m "feat(admin): UI bat/tat guardrail rule"
```

---

## Task 6: Backend quản lý người dùng

Khu vực 2 — **chưa có gì**, xây từ đầu. Model `User` đã có `is_active` (`src/db/models.py:56`) nên không cần migration.

**Files:**
- Create: `src/api/admin_users.py`
- Modify: `src/main.py` (include router), `src/api/admin_schemas.py` (schema)
- Test: `tests/test_api/test_admin_users.py`

**Interfaces:**
- Produces: `GET /api/v1/admin/users` → `{success, data: {users: [{id, email, full_name, role, is_active, created_at, last_active_at}]}}`; `PATCH /api/v1/admin/users/{user_id}` body `{is_active: bool}` → `{success, data: {user}}`.

- [ ] **Step 1: Viết test (đỏ)**

Tạo `tests/test_api/test_admin_users.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_list_users_returns_roles_and_status(client, admin_token):
    response = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    users = response.json()["data"]["users"]
    assert users, "phải có ít nhất tài khoản admin đang gọi"
    user = users[0]
    for field in ("id", "email", "full_name", "role", "is_active", "created_at"):
        assert field in user
    assert "password_hash" not in user, "không được lộ hash mật khẩu"


@pytest.mark.asyncio
async def test_lock_and_unlock_user(client, admin_token, student_user_id):
    headers = {"Authorization": f"Bearer {admin_token}"}

    locked = await client.patch(
        f"/api/v1/admin/users/{student_user_id}",
        headers=headers,
        json={"is_active": False},
    )
    assert locked.status_code == 200
    assert locked.json()["data"]["user"]["is_active"] is False

    unlocked = await client.patch(
        f"/api/v1/admin/users/{student_user_id}",
        headers=headers,
        json={"is_active": True},
    )
    assert unlocked.json()["data"]["user"]["is_active"] is True


@pytest.mark.asyncio
async def test_admin_cannot_lock_self(client, admin_token, admin_user_id):
    response = await client.patch(
        f"/api/v1/admin/users/{admin_user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert response.status_code == 400, "tự khoá mình sẽ tự nhốt ngoài hệ thống"


@pytest.mark.asyncio
async def test_lock_writes_audit_event(client, admin_token, student_user_id):
    headers = {"Authorization": f"Bearer {admin_token}"}
    await client.patch(
        f"/api/v1/admin/users/{student_user_id}",
        headers=headers,
        json={"is_active": False},
    )
    events = (
        await client.get(
            "/api/v1/audit/events?event_type=user_status_changed&limit=10",
            headers=headers,
        )
    ).json()
    assert any(e["resource_id"] == student_user_id for e in events)


@pytest.mark.asyncio
async def test_student_cannot_list_users(client, student_token):
    response = await client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 403
```

Fixture `student_user_id` / `admin_user_id` nếu chưa có thì thêm vào `tests/conftest.py`, lấy id từ chính user mà fixture token đã tạo.

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_users.py -v
```

Kỳ vọng: FAIL toàn bộ với 404 (route chưa tồn tại).

- [ ] **Step 3: Thêm schema vào `src/api/admin_schemas.py`**

```python
class AdminUserItem(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str
    last_active_at: str | None = None


class AdminUserListData(BaseModel):
    users: list[AdminUserItem]


class AdminUserListResponse(BaseModel):
    success: Literal[True]
    data: AdminUserListData


class AdminUserStatusRequest(BaseModel):
    is_active: bool


class AdminUserData(BaseModel):
    user: AdminUserItem


class AdminUserResponse(BaseModel):
    success: Literal[True]
    data: AdminUserData
```

- [ ] **Step 4: Tạo `src/api/admin_users.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.admin_schemas import (
    AdminUserItem,
    AdminUserResponse,
    AdminUserListResponse,
    AdminUserStatusRequest,
)
from src.db.connection import get_db
from src.db.models import AuthSession, User, UserRole
from src.repositories.audit_repository import AuditRepository
from src.security.dependencies import (
    get_current_user_from_token,
    require_permission,
    require_roles,
)
from src.security.permissions import Permission, Resource
from src.services.audit_service import AuditService

router = APIRouter(
    prefix="/admin/users",
    tags=["admin-users"],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)


def _serialize(user: User, last_active_at: str | None) -> AdminUserItem:
    role = user.role if isinstance(user.role, str) else user.role.value
    return AdminUserItem(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        last_active_at=last_active_at,
    )


@router.get("", response_model=AdminUserListResponse)
async def list_users(
    role: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> AdminUserListResponse:
    stmt = select(User).order_by(User.created_at.desc())
    if role:
        stmt = stmt.where(User.role == role)
    users = db.execute(stmt).scalars().all()

    items = []
    for user in users:
        latest = db.execute(
            select(AuthSession.created_at)
            .where(AuthSession.user_id == user.id)
            .order_by(AuthSession.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        items.append(_serialize(user, latest.isoformat() if latest else None))

    return AdminUserListResponse(success=True, data={"users": items})


@router.patch(
    "/{user_id}",
    response_model=AdminUserResponse,
    dependencies=[Depends(require_permission(Resource.USER, Permission.MANAGE))],
)
async def set_user_status(
    user_id: str,
    payload: AdminUserStatusRequest,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
) -> AdminUserResponse:
    if user_id == current_user.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tự khoá tài khoản của chính mình.",
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")

    try:
        user.is_active = payload.is_active
        await AuditService(AuditRepository(db)).log_event(
            event_type="user_status_changed",
            decision="ALLOW",
            actor_user_id=current_user.id,
            resource_type="USER",
            resource_id=user_id,
            metadata={"is_active": payload.is_active},
            commit=False,
        )
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise

    return AdminUserResponse(success=True, data={"user": _serialize(user, None)})
```

Nếu `Resource.USER` chưa tồn tại trong `src/security/permissions.py`, thêm vào enum đó. Kiểm tra tên thật của enum trước khi viết — đọc file, đừng đoán.

- [ ] **Step 5: Đăng ký router ở `src/main.py`**

Thêm import và `app.include_router(admin_users_router, prefix="/api/v1")` ngay sau dòng 65 (`admin_router`).

- [ ] **Step 6: Chạy test, xác nhận xanh**

```bash
.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_users.py -v
```

Kỳ vọng: 5 PASS.

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
```

Kỳ vọng: vẫn `7 failed`, passed tăng 5.

- [ ] **Step 7: Commit**

```bash
git add src/api/admin_users.py src/api/admin_schemas.py src/main.py tests/test_api/test_admin_users.py tests/conftest.py
git commit -m "feat(admin): API danh sach + khoa/mo tai khoan nguoi dung"
```

---

## Task 7: UI quản lý người dùng

**Files:**
- Create: `frontend/src/components/admin/AdminUsers.jsx`
- Modify: `frontend/src/lib/api.js` (2 hàm), `AdminConsole.jsx` (nối tab `users`)

**Interfaces:**
- Consumes: `listAdminUsers({role})`, `setUserActive(userId, isActive)` từ Task 6.

- [ ] **Step 1: Thêm hàm client**

Vào `frontend/src/lib/api.js`, khối Admin Console:

```javascript
export function listAdminUsers({ role } = {}) {
  const query = role ? `?role=${encodeURIComponent(role)}` : '';
  return request(`/admin/users${query}`);
}

export function setUserActive(userId, isActive) {
  return request(`/admin/users/${encodeURIComponent(userId)}`, {
    method: 'PATCH',
    body: { is_active: isActive },
  });
}
```

- [ ] **Step 2: Tạo `AdminUsers.jsx`**

```javascript
import React, { useCallback, useEffect, useState } from 'react';
import { Users, Lock, Unlock } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { listAdminUsers, setUserActive } from '../../lib/api';

const ROLE_FILTERS = ['', 'STUDENT', 'INSTRUCTOR', 'ADMIN'];

export default function AdminUsers() {
  const { t } = useLanguage();
  const [users, setUsers] = useState([]);
  const [role, setRole] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const body = await listAdminUsers({ role: role || undefined });
      setUsers(body.data.users);
    } catch (err) {
      setError(err.message);
    }
  }, [role]);

  useEffect(() => { load(); }, [load]);

  async function toggle(user) {
    setBusy(user.id);
    setError(null);
    try {
      await setUserActive(user.id, !user.is_active);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users size={15} className="text-slate-500" />
          <h2 className="text-sm font-bold">{t('admin.usersTitle')}</h2>
        </div>
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="rounded border border-line px-2 py-1 text-xs"
        >
          {ROLE_FILTERS.map((value) => (
            <option key={value || 'all'} value={value}>
              {value || t('admin.usersAllRoles')}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="text-xs text-danger">{error}</p>}

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-line text-fg-secondary">
              <th className="py-2 pr-3">{t('admin.usersName')}</th>
              <th className="py-2 pr-3">{t('admin.usersEmail')}</th>
              <th className="py-2 pr-3">{t('admin.usersRole')}</th>
              <th className="py-2 pr-3">{t('admin.usersLastActive')}</th>
              <th className="py-2">{t('admin.usersStatus')}</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-b border-line/50">
                <td className="py-2 pr-3">{user.full_name}</td>
                <td className="py-2 pr-3">{user.email}</td>
                <td className="py-2 pr-3 font-mono">{user.role}</td>
                <td className="py-2 pr-3 whitespace-nowrap">
                  {user.last_active_at ? new Date(user.last_active_at).toLocaleDateString() : '—'}
                </td>
                <td className="py-2">
                  <button
                    type="button"
                    disabled={busy === user.id}
                    onClick={() => toggle(user)}
                    className="flex items-center gap-1 rounded border border-line px-2 py-1"
                  >
                    {user.is_active ? <Lock size={12} /> : <Unlock size={12} />}
                    {user.is_active ? t('admin.usersLock') : t('admin.usersUnlock')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Thêm key i18n + nối tab**

`vi.js`: `usersTitle: 'Người dùng'`, `usersAllRoles: 'Tất cả vai trò'`, `usersName: 'Họ tên'`, `usersEmail: 'Email'`, `usersRole: 'Vai trò'`, `usersLastActive: 'Hoạt động gần nhất'`, `usersStatus: 'Trạng thái'`, `usersLock: 'Khoá'`, `usersUnlock: 'Mở khoá'`.
`en.js`: `usersTitle: 'Users'`, `usersAllRoles: 'All roles'`, `usersName: 'Full name'`, `usersEmail: 'Email'`, `usersRole: 'Role'`, `usersLastActive: 'Last active'`, `usersStatus: 'Status'`, `usersLock: 'Lock'`, `usersUnlock: 'Unlock'`.

Trong `AdminConsole.jsx`, tab `users` render `<AdminUsers />`.

- [ ] **Step 4: Kiểm chứng + commit**

Khoá 1 tài khoản sinh viên, đăng nhập bằng chính tài khoản đó — phải bị từ chối. Thử bấm khoá chính tài khoản admin đang dùng — phải hiện lỗi, không được khoá.

```bash
cd frontend && npm run lint
```

```bash
git add frontend/src/
git commit -m "feat(admin): UI quan ly nguoi dung + khoa/mo tai khoan"
```

---

## Task 8: Backend lời mời

Khu vực 3 — chưa có gì. Theo mục 6.1: **chỉ Admin gửi được lời mời**, kể cả mời giảng viên; lời mời giảng viên phải gán sẵn lớp.

**Files:**
- Create: `migrations/versions/20260822_admin_invitations.py`, `src/repositories/invitation_repository.py`, `src/api/admin_invitations.py`
- Modify: `src/db/models.py` (model `Invitation`), `src/main.py`
- Test: `tests/test_api/test_admin_invitations.py`

**Interfaces:**
- Produces: `POST /api/v1/admin/invites` body `{email, role, class_ids?}` → `{success, data: {invitation, activation_token, delivery_status}}`; `GET /api/v1/admin/invites` → `{success, data: {invitations: [...]}}`; `POST /api/v1/admin/invites/{id}/revoke`. Trường `invitation`: `{id, email, role, status, class_ids, created_at, expires_at}`, `status ∈ {pending, accepted, revoked, expired}`. `activation_token` chỉ có ở response tạo mới; `delivery_status ∈ {sent, disabled, failed}`.

- [ ] **Step 1: Viết test (đỏ)**

Tạo `tests/test_api/test_admin_invitations.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_create_student_invitation(client, admin_token):
    response = await client.post(
        "/api/v1/admin/invites",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "moi.sv@example.test", "role": "STUDENT"},
    )
    assert response.status_code == 201
    invitation = response.json()["data"]["invitation"]
    assert invitation["status"] == "pending"
    assert invitation["role"] == "STUDENT"
    assert "token" not in invitation, "token lời mời không được trả về trong danh sách"
    assert response.json()["data"]["activation_token"]
    assert response.json()["data"]["delivery_status"] in {"sent", "disabled", "failed"}


@pytest.mark.asyncio
async def test_instructor_invitation_requires_class_ids(client, admin_token):
    response = await client.post(
        "/api/v1/admin/invites",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "moi.gv@example.test", "role": "INSTRUCTOR"},
    )
    assert response.status_code == 400, "mời giảng viên bắt buộc gán lớp (mục 6.1)"


@pytest.mark.asyncio
async def test_cannot_invite_admin_role(client, admin_token):
    response = await client.post(
        "/api/v1/admin/invites",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "moi.admin@example.test", "role": "ADMIN"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_revoke_invitation(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    created = await client.post(
        "/api/v1/admin/invites",
        headers=headers,
        json={"email": "thu.hoi@example.test", "role": "STUDENT"},
    )
    invitation_id = created.json()["data"]["invitation"]["id"]

    revoked = await client.post(
        f"/api/v1/admin/invites/{invitation_id}/revoke",
        headers=headers,
    )
    assert revoked.status_code == 200
    assert revoked.json()["data"]["invitation"]["status"] == "revoked"


@pytest.mark.asyncio
async def test_student_cannot_create_invitation(client, student_token):
    response = await client.post(
        "/api/v1/admin/invites",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"email": "x@example.test", "role": "STUDENT"},
    )
    assert response.status_code == 403
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_invitations.py -v
```

Kỳ vọng: FAIL toàn bộ với 404.

- [ ] **Step 3: Thêm model vào `src/db/models.py`**

```python
class Invitation(Base):
    __tablename__ = "invitations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String)
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    class_ids: Mapped[str | None] = mapped_column(String, nullable=True)
    invited_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

`class_ids` lưu chuỗi CSV để tránh phụ thuộc kiểu JSON của từng backend DB (test dùng SQLite, production dùng Postgres). Serialize/deserialize trong repository, không rải logic đó khắp route.

Chỉ lưu `token_hash`, **không bao giờ** lưu token thô — cùng nguyên tắc `AuthSession.refresh_token_hash` đang dùng.

- [ ] **Step 4: Tạo migration**

Tạo `migrations/versions/20260822_admin_invitations.py`:

```python
"""admin invitations

Revision ID: 20260822_admin_invitations
Revises: 20260821_self_study_sessions
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_admin_invitations"
down_revision: str | Sequence[str] | None = "20260821_self_study_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invitations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, index=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("class_ids", sa.String(), nullable=True),
        sa.Column("invited_by", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_invitations_status", "invitations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_invitations_status", table_name="invitations")
    op.drop_table("invitations")
```

- [ ] **Step 5: Chạy migration, xác nhận lên được và xuống được**

```bash
.venv/Scripts/python.exe -m alembic upgrade head
```

```bash
.venv/Scripts/python.exe -m alembic downgrade -1
```

```bash
.venv/Scripts/python.exe -m alembic upgrade head
```

Cả 3 lệnh phải chạy sạch. Migration không rollback được là migration hỏng.

- [ ] **Step 6: Viết repository + route**

`src/repositories/invitation_repository.py` — các hàm `create(email, role, class_ids, invited_by, token_hash, expires_at)`, `list_all()`, `get(invitation_id)`, `revoke(invitation_id)`. Xử lý CSV `class_ids` ở đây: `",".join(ids)` khi ghi, `value.split(",") if value else []` khi đọc.

`src/api/admin_invitations.py` — router `prefix="/admin/invites"`, `dependencies=[Depends(require_roles(UserRole.ADMIN))]`, cùng pattern như `admin_users.py` ở Task 6. Route POST/revoke thêm `require_permission(Resource.USER, Permission.MANAGE)`. Bốn quy tắc bắt buộc:

1. `role == "ADMIN"` → HTTP 400. Admin không mời admin (mục 6.1 chỉ cho phép mời sinh viên/giảng viên).
2. `role == "INSTRUCTOR"` mà `class_ids` rỗng → HTTP 400.
3. Sinh token bằng `secrets.token_urlsafe(32)`, lưu `hashlib.sha256(token.encode()).hexdigest()`, trả token thô **đúng một lần** trong response tạo mới (để gắn vào link email), không bao giờ trả lại ở `GET`.
4. Gọi email abstraction hiện có. `EMAIL_PROVIDER=smtp` trả `delivery_status="sent"`; nếu SMTP lỗi sau khi transaction đã commit thì trả `delivery_status="failed"` cùng activation link một lần để Admin gửi thủ công; provider `none` trả `delivery_status="disabled"` và UI chỉ nói link demo đã sẵn sàng, không nói email đã gửi.

Mọi thao tác tạo/thu hồi ghi audit `event_type="invitation_created"` / `"invitation_revoked"`.

- [ ] **Step 7: Đăng ký router + chạy test**

Thêm `app.include_router(admin_invitations_router, prefix="/api/v1")` vào `src/main.py`.

```bash
.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_invitations.py -v
```

Kỳ vọng: 5 PASS.

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
```

Kỳ vọng: vẫn `7 failed`.

- [ ] **Step 8: Commit**

```bash
git add src/ migrations/ tests/test_api/test_admin_invitations.py
git commit -m "feat(admin): API loi moi tai khoan (chi admin, gv bat buoc gan lop)"
```

---

## Task 9: UI lời mời

**Files:**
- Create: `frontend/src/components/admin/AdminInvitations.jsx`
- Modify: `frontend/src/lib/api.js`, `AdminConsole.jsx`

- [ ] **Step 1: Thêm hàm client**

```javascript
export function listInvitations() {
  return request('/admin/invites');
}

export function createInvitation({ email, role, class_ids }) {
  return request('/admin/invites', {
    method: 'POST',
    body: { email, role, class_ids },
  });
}

export function revokeInvitation(invitationId) {
  return request(`/admin/invites/${encodeURIComponent(invitationId)}/revoke`, {
    method: 'POST',
  });
}
```

- [ ] **Step 2: Tạo `AdminInvitations.jsx`**

Form gửi lời mời: input email, select vai trò (chỉ `STUDENT` và `INSTRUCTOR` — **không** có `ADMIN` trong danh sách), và khi chọn `INSTRUCTOR` thì hiện thêm ô chọn lớp (bắt buộc, nút gửi disabled nếu chưa chọn). Bảng bên dưới liệt kê lời mời: email, vai trò, trạng thái (badge), ngày gửi, hạn dùng, nút "Thu hồi" chỉ hiện khi `status === 'pending'`.

Dùng lại đúng class Tailwind của `AdminUsers.jsx` (`overflow-x-auto`, `border-line`, `text-xs`) cho đồng bộ. Sau khi gửi thành công, hiện token/link kích hoạt **một lần** kèm nút copy và ghi chú "chỉ hiện một lần, lưu lại trước khi đóng".

- [ ] **Step 3: Thêm key i18n + nối tab `invites`**

`vi.js`: `invitesTitle: 'Lời mời'`, `invitesEmail: 'Email'`, `invitesRole: 'Vai trò'`, `invitesClasses: 'Lớp được gán'`, `invitesSend: 'Gửi lời mời'`, `invitesRevoke: 'Thu hồi'`, `invitesPending: 'Chờ kích hoạt'`, `invitesAccepted: 'Đã dùng'`, `invitesRevoked: 'Đã thu hồi'`, `invitesExpired: 'Đã hết hạn'`, `invitesOneTimeLink: 'Link này chỉ hiện một lần. Hãy lưu lại trước khi đóng.'`, `invitesDeliveryDisabled: 'Email đang tắt trong môi trường này; hãy dùng link kích hoạt bên dưới.'`.

`en.js`: `invitesTitle: 'Invitations'`, `invitesEmail: 'Email'`, `invitesRole: 'Role'`, `invitesClasses: 'Assigned classes'`, `invitesSend: 'Send invitation'`, `invitesRevoke: 'Revoke'`, `invitesPending: 'Pending'`, `invitesAccepted: 'Accepted'`, `invitesRevoked: 'Revoked'`, `invitesExpired: 'Expired'`, `invitesOneTimeLink: 'This link is shown once. Save it before closing.'`, `invitesDeliveryDisabled: 'Email delivery is disabled in this environment; use the activation link below.'`.

Trong `AdminConsole.jsx`, tab `invites` render `<AdminInvitations />`.

- [ ] **Step 4: Kiểm chứng + commit**

Thử chọn vai trò Giảng viên mà không chọn lớp — nút gửi phải bị khoá. Gửi lời mời sinh viên, xem nó xuất hiện với trạng thái "chờ", bấm thu hồi, trạng thái đổi thành "đã thu hồi".

```bash
git add frontend/src/
git commit -m "feat(admin): UI gui va thu hoi loi moi"
```

---

## Task 10: Backend ngưỡng risk score + versioning

Khu vực 5b, và là mục P0 #7 trong `docs/PROJECT_CONTEXT.md` mục 9. Yêu cầu bắt buộc từ mục đó: `policy_version`, `effective_from`, alert lưu version lúc tính, không ghi đè lịch sử, có min/max, bắt buộc ghi lý do đổi, rollback được.

**Files:**
- Create: `migrations/versions/20260823_admin_risk_policy.py`, `src/repositories/risk_policy_repository.py`, `src/api/admin_policy.py`
- Create: `src/services/risk_policy_service.py`
- Modify: `src/db/models.py`, `src/main.py`
- Test: `tests/test_api/test_admin_policy.py`

**Interfaces:**
- Produces: `GET /api/v1/admin/risk-policy` → chính sách đang hiệu lực; `GET /api/v1/admin/risk-policy/history` → toàn bộ version; `POST /api/v1/admin/risk-policy/preview` → `{affected_students, evaluated_students, changes}` mà không ghi DB; `POST /api/v1/admin/risk-policy` body `{late_days_threshold, completion_rate_threshold, weight_late, weight_completion, change_reason}` → tạo version **mới**; `POST /api/v1/admin/risk-policy/{version}/rollback` body `{change_reason}` → tạo version mới sao chép policy cũ.

- [ ] **Step 1: Viết test (đỏ)**

```python
import pytest


@pytest.mark.asyncio
async def test_publishing_policy_creates_new_version_not_overwrite(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    before = (await client.get("/api/v1/admin/risk-policy", headers=headers)).json()
    old_version = before["data"]["policy"]["policy_version"]

    created = await client.post(
        "/api/v1/admin/risk-policy",
        headers=headers,
        json={
            "late_days_threshold": 5,
            "completion_rate_threshold": 0.4,
            "weight_late": 0.6,
            "weight_completion": 0.4,
            "change_reason": "Siết ngưỡng sau tuần 3",
        },
    )
    assert created.status_code == 201
    new_version = created.json()["data"]["policy"]["policy_version"]
    assert new_version != old_version

    history = (await client.get("/api/v1/admin/risk-policy/history", headers=headers)).json()
    versions = [item["policy_version"] for item in history["data"]["policies"]]
    assert old_version in versions, "version cũ phải còn trong lịch sử, không bị ghi đè"


@pytest.mark.asyncio
async def test_change_reason_is_required(client, admin_token):
    response = await client.post(
        "/api/v1/admin/risk-policy",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "late_days_threshold": 5,
            "completion_rate_threshold": 0.4,
            "weight_late": 0.6,
            "weight_completion": 0.4,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"late_days_threshold": 0},
        {"late_days_threshold": 400},
        {"completion_rate_threshold": 1.5},
        {"completion_rate_threshold": -0.1},
    ],
)
async def test_thresholds_are_bounded(client, admin_token, payload):
    body = {
        "late_days_threshold": 5,
        "completion_rate_threshold": 0.4,
        "weight_late": 0.6,
        "weight_completion": 0.4,
        "change_reason": "test biên",
        **payload,
    }
    response = await client.post(
        "/api/v1/admin/risk-policy",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=body,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_weights_must_sum_to_one(client, admin_token):
    response = await client.post(
        "/api/v1/admin/risk-policy",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "late_days_threshold": 5,
            "completion_rate_threshold": 0.4,
            "weight_late": 0.9,
            "weight_completion": 0.4,
            "change_reason": "tổng trọng số sai",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_policy_change_writes_audit_event(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    await client.post(
        "/api/v1/admin/risk-policy",
        headers=headers,
        json={
            "late_days_threshold": 6,
            "completion_rate_threshold": 0.35,
            "weight_late": 0.5,
            "weight_completion": 0.5,
            "change_reason": "Kiểm tra audit",
        },
    )
    events = (
        await client.get(
            "/api/v1/audit/events?event_type=risk_policy_published&limit=5",
            headers=headers,
        )
    ).json()
    assert events, "publish policy phải ghi audit (mục 6.5)"
    assert events[0]["metadata"].get("change_reason") == "Kiểm tra audit"


@pytest.mark.asyncio
async def test_preview_does_not_publish_policy(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    before = (await client.get("/api/v1/admin/risk-policy", headers=headers)).json()["data"]["policy"]
    preview = await client.post(
        "/api/v1/admin/risk-policy/preview",
        headers=headers,
        json={
            "late_days_threshold": 5,
            "completion_rate_threshold": 0.4,
            "weight_late": 0.6,
            "weight_completion": 0.4,
            "change_reason": "Xem trước tác động policy",
        },
    )
    assert preview.status_code == 200
    data = preview.json()["data"]
    assert data["affected_students"] >= 0
    assert data["evaluated_students"] >= data["affected_students"]
    after = (await client.get("/api/v1/admin/risk-policy", headers=headers)).json()["data"]["policy"]
    assert after["policy_version"] == before["policy_version"]


@pytest.mark.asyncio
async def test_rollback_creates_new_version(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    original = (await client.get("/api/v1/admin/risk-policy", headers=headers)).json()["data"]["policy"]
    rolled = await client.post(
        f"/api/v1/admin/risk-policy/{original['policy_version']}/rollback",
        headers=headers,
        json={"change_reason": "Khôi phục policy ổn định trước đó"},
    )
    assert rolled.status_code == 201
    assert rolled.json()["data"]["policy"]["policy_version"] != original["policy_version"]


@pytest.mark.asyncio
async def test_existing_risk_signals_expose_policy_version(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    preview = await client.post(
        "/api/v1/admin/risk-policy/preview",
        headers=headers,
        json={
            "late_days_threshold": 5,
            "completion_rate_threshold": 0.4,
            "weight_late": 0.6,
            "weight_completion": 0.4,
            "change_reason": "Kiểm tra version của alert",
        },
    )
    assert all(change["policy_version"] for change in preview.json()["data"]["changes"])
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_policy.py -v
```

- [ ] **Step 3: Model + migration**

Model `RiskPolicy`: `policy_version` (string, unique), `late_days_threshold` (int), `completion_rate_threshold` (float), `weight_late` (float), `weight_completion` (float), `change_reason` (string), `effective_from` (datetime), `is_active` (bool), `created_by` (FK users.id), `created_at`.

Thêm `RiskSignal.policy_version` non-null, server default `"v1"`, backfill toàn bộ alert cũ thành `v1`. Mọi chỗ tạo `RiskSignal` sau này phải nhận version đang active qua `RiskPolicyRepository.get_active()`; không suy version từ thời điểm đọc.

Model `AdminSetting` (dùng cho Task 12, tạo luôn ở migration này để đỡ thêm 1 migration nữa): `key` (string PK), `value` (string), `updated_by`, `updated_at`.

Migration `20260823_admin_risk_policy.py` với `down_revision = "20260822_admin_invitations"` — **không** trỏ về `20260821_self_study_sessions`, nếu không sẽ tạo 2 nhánh song song và `alembic upgrade head` sẽ báo lỗi multiple heads.

Seed 1 policy mặc định `v1` trong `upgrade()` để `GET /admin/risk-policy` không trả 404 khi DB mới.

- [ ] **Step 4: Schema Pydantic có ràng buộc biên**

```python
class RiskPolicyPublishRequest(BaseModel):
    late_days_threshold: int = Field(ge=1, le=90)
    completion_rate_threshold: float = Field(ge=0.0, le=1.0)
    weight_late: float = Field(ge=0.0, le=1.0)
    weight_completion: float = Field(ge=0.0, le=1.0)
    change_reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5)]

    @model_validator(mode="after")
    def weights_sum_to_one(self):
        total = self.weight_late + self.weight_completion
        if abs(total - 1.0) > 1e-6:
            raise ValueError("weight_late + weight_completion phải bằng 1.0")
        return self
```

`Field(ge=..., le=...)` là chỗ 4 test biên ở Step 1 dựa vào — Pydantic tự trả 422, không cần viết `if` trong route.

- [ ] **Step 5: Route + chạy migration + test**

`RiskPolicyService.preview(payload)` đọc các `RiskSignal` chưa resolve, tính lại level từ evidence hiện có, trả số student riêng biệt đổi level và danh sách thay đổi; không commit. Nếu signal thiếu evidence để tính, giữ trong `evaluated_students` chỉ khi tính được và không tự bịa dữ liệu.

`POST` tạo bản ghi mới với `policy_version` tăng dần (`v1` → `v2`…), set `is_active=False` cho bản cũ, `is_active=True` cho bản mới. Ghi audit `risk_policy_published` với `metadata={"change_reason": ..., "policy_version": ...}`.

`rollback` = tạo **version mới** sao chép giá trị của version cũ (không bật lại bản ghi cũ) — giữ đúng nguyên tắc "không ghi đè lịch sử".

Sau publish/rollback, chạy bộ test rule synthetic hiện có; chỉ khi test pass mới coi policy ổn định trong checklist bàn giao. Không gọi kết quả demo là precision/recall thật.

```bash
.venv/Scripts/python.exe -m alembic upgrade head
```

```bash
.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_policy.py -v
```

Kỳ vọng: 8 PASS (4 test biên tính parametrize).

- [ ] **Step 6: Commit**

```bash
git add src/ migrations/ tests/test_api/test_admin_policy.py
git commit -m "feat(admin): risk policy co versioning, bien va ly do doi bat buoc"
```

---

## Task 11: UI ngưỡng risk score

Gộp vào tab "Chính sách AI" cùng guardrail rules — mục 6.5 xếp cả hai vào một khu vực.

**Files:**
- Modify: `frontend/src/components/admin/AdminGuardrailRules.jsx` (thêm khối ngưỡng), `frontend/src/lib/api.js`

- [ ] **Step 1: Thêm hàm client**

```javascript
export function getRiskPolicy() {
  return request('/admin/risk-policy');
}

export function getRiskPolicyHistory() {
  return request('/admin/risk-policy/history');
}

export function previewRiskPolicy(payload) {
  return request('/admin/risk-policy/preview', { method: 'POST', body: payload });
}

export function publishRiskPolicy(payload) {
  return request('/admin/risk-policy', { method: 'POST', body: payload });
}

export function rollbackRiskPolicy(version, changeReason) {
  return request(`/admin/risk-policy/${encodeURIComponent(version)}/rollback`, {
    method: 'POST',
    body: { change_reason: changeReason },
  });
}
```

- [ ] **Step 2: Thêm khối ngưỡng vào `AdminGuardrailRules.jsx`**

Dưới danh sách rule, thêm một `<section>` gồm: 4 input số (ngưỡng ngày trễ, ngưỡng tỷ lệ hoàn thành, trọng số trễ, trọng số hoàn thành), 1 textarea **bắt buộc** cho lý do đổi, nút "Xem trước tác động", panel kết quả preview, và nút "Công bố phiên bản mới" chỉ mở sau preview thành công cho đúng payload hiện tại.

Bốn ràng buộc UI phải có:
1. Nút công bố disabled khi `change_reason.trim().length < 5`.
2. Hiện cảnh báo đỏ ngay dưới 2 ô trọng số nếu tổng ≠ 1.0, và disable nút.
3. Hiện `policy_version` đang hiệu lực ở đầu khối.
4. Danh sách lịch sử version bên dưới (version, ngày, người đổi, lý do) — chứng minh "không ghi đè lịch sử" bằng mắt thường khi demo.
5. Mỗi version lịch sử có nút rollback; bấm rollback yêu cầu lý do và xác nhận, response tạo version mới rồi reload current/history.
6. Khi thay đổi bất kỳ input sau preview, xoá kết quả preview và disable Publish cho tới khi preview lại.

- [ ] **Step 3: Thêm key i18n**

`vi.js`: `policyTitle: 'Ngưỡng risk score'`, `policyCurrentVersion: 'Phiên bản đang hiệu lực'`, `policyLateDays: 'Ngưỡng số ngày trễ'`, `policyCompletionRate: 'Ngưỡng tỷ lệ hoàn thành'`, `policyWeightLate: 'Trọng số trễ hạn'`, `policyWeightCompletion: 'Trọng số hoàn thành'`, `policyReason: 'Lý do thay đổi'`, `policyPreview: 'Xem trước tác động'`, `policyAffected: 'Sinh viên đổi mức nguy cơ'`, `policyPublish: 'Công bố phiên bản mới'`, `policyHistory: 'Lịch sử phiên bản'`, `policyRollback: 'Khôi phục thành phiên bản mới'`, `policyWeightsInvalid: 'Tổng hai trọng số phải bằng 1,0.'`.

`en.js`: `policyTitle: 'Risk-score thresholds'`, `policyCurrentVersion: 'Active version'`, `policyLateDays: 'Late-days threshold'`, `policyCompletionRate: 'Completion-rate threshold'`, `policyWeightLate: 'Late weight'`, `policyWeightCompletion: 'Completion weight'`, `policyReason: 'Reason for change'`, `policyPreview: 'Preview impact'`, `policyAffected: 'Students changing risk level'`, `policyPublish: 'Publish new version'`, `policyHistory: 'Version history'`, `policyRollback: 'Restore as a new version'`, `policyWeightsInvalid: 'The two weights must add up to 1.0.'`.

- [ ] **Step 4: Kiểm chứng + commit**

Đổi ngưỡng, preview số sinh viên bị ảnh hưởng, công bố, xác nhận version tăng và version cũ vẫn nằm trong lịch sử. Rollback một version và xác nhận hệ thống tạo version mới. Thử để trống lý do — nút phải khoá. Thử đặt trọng số 0.9 + 0.4 — phải hiện cảnh báo.

```bash
git add frontend/src/
git commit -m "feat(admin): UI nguong risk score + lich su phien ban"
```

---

## Task 12: Khu vực Cấu hình

Khu vực 7. Mục 6.5 yêu cầu: bật/tắt chế độ demo, bật/tắt tự động cảnh báo nguy cơ, học kỳ mặc định. Bảng `admin_settings` đã tạo ở migration Task 10.

**Files:**
- Create: `frontend/src/components/admin/AdminSettings.jsx`
- Modify: `src/api/admin.py` (2 route), `frontend/src/components/admin/AdminConsole.jsx`
- Test: `tests/test_api/test_admin_settings.py`

**Interfaces:**
- Produces: `GET /api/v1/admin/settings` → `{success, data: {settings: {demo_mode: bool, auto_risk_alert: bool, default_semester: str}}}`; `PUT /api/v1/admin/settings` nhận cùng shape.

- [ ] **Step 1: Viết test (đỏ)**

```python
import pytest


@pytest.mark.asyncio
async def test_settings_have_defaults(client, admin_token):
    response = await client.get(
        "/api/v1/admin/settings",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    settings = response.json()["data"]["settings"]
    assert isinstance(settings["demo_mode"], bool)
    assert isinstance(settings["auto_risk_alert"], bool)
    assert settings["default_semester"]


@pytest.mark.asyncio
async def test_update_settings_persists_and_audits(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    await client.put(
        "/api/v1/admin/settings",
        headers=headers,
        json={"demo_mode": False, "auto_risk_alert": True, "default_semester": "Spring 2027"},
    )
    settings = (await client.get("/api/v1/admin/settings", headers=headers)).json()["data"]["settings"]
    assert settings["default_semester"] == "Spring 2027"
    assert settings["demo_mode"] is False

    events = (
        await client.get(
            "/api/v1/audit/events?event_type=admin_settings_updated&limit=5",
            headers=headers,
        )
    ).json()
    assert events


@pytest.mark.asyncio
async def test_student_cannot_read_settings(client, student_token):
    response = await client.get(
        "/api/v1/admin/settings",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 403
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_settings.py -v
```

- [ ] **Step 3: Viết route trong `src/api/admin.py`**

Lưu vào bảng `admin_settings` dạng key-value chuỗi; ép kiểu bool bằng `value == "true"` khi đọc. Giá trị mặc định khi thiếu key: `demo_mode=True`, `auto_risk_alert=True`, `default_semester="Fall 2026"`. Ghi audit `admin_settings_updated` kèm metadata là các key đã đổi.

- [ ] **Step 4: Thêm panel Cấu hình vào UI**

Tạo `AdminSettings.jsx` với 3 toggle/input, nút Lưu và thông báo thành công. Copy giải thích `auto_risk_alert`: điều khiển việc sinh cảnh báo, không tự gửi tin hay tự can thiệp. Render `<AdminAcademicCalendar />` phía dưới cùng panel này. `AdminConsole.jsx` render panel ở tab `settings`; không còn tab `term` top-level.

`vi.js`: `tabSettings: 'Cấu hình'`, `settingsTitle: 'Cấu hình hệ thống'`, `settingsDemoMode: 'Chế độ demo'`, `settingsAutoRisk: 'Tự động sinh cảnh báo nguy cơ'`, `settingsAutoRiskHelp: 'Chỉ điều khiển việc sinh cảnh báo; hệ thống không tự nhắn tin hoặc tự can thiệp.'`, `settingsDefaultSemester: 'Học kỳ mặc định'`, `settingsSave: 'Lưu cấu hình'`, `settingsSaved: 'Đã lưu cấu hình.'`.

`en.js`: `tabSettings: 'Settings'`, `settingsTitle: 'System settings'`, `settingsDemoMode: 'Demo mode'`, `settingsAutoRisk: 'Automatically generate risk alerts'`, `settingsAutoRiskHelp: 'This only controls alert generation; the system never messages or intervenes automatically.'`, `settingsDefaultSemester: 'Default semester'`, `settingsSave: 'Save settings'`, `settingsSaved: 'Settings saved.'`.

- [ ] **Step 5: Chạy toàn bộ test + commit**

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
```

Kỳ vọng: vẫn đúng `7 failed`. Tổng passed ≈ 246 + 27.

```bash
git add src/ frontend/src/ tests/
git commit -m "feat(admin): khu vuc Cau hinh (demo mode, canh bao, hoc ky)"
```

---

## Task 13: Đối chiếu lần cuối + sửa docs cho trung thực

Task này tồn tại vì `docs/archive/planning-v2/progress/CHUNG.md` đang tick `[x]` cho những việc code chưa làm — chính bản brief B2B của bạn (mục 3.3) đã chỉ ra. Sau 12 task trên, phần lớn tick đó thành đúng; task này đối chiếu và sửa phần còn lệch.

**Files:**
- Modify: `docs/archive/planning-v2/progress/CHUNG.md`, `docs/PROJECT_CONTEXT.md` (mục 9)

- [ ] **Step 1: Chạy full test, ghi lại con số thật**

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
```

Ghi lại chính xác dòng cuối. Con số này là bằng chứng, không được làm tròn hay nói giảm.

- [ ] **Step 2: Xác nhận không còn mock/hardcode trong khu vực admin**

```bash
grep -rn "INITIAL_COURSES\|0\.78\|0\.45" frontend/src/components/admin/
```

Kỳ vọng: không ra dòng nào. Nếu còn, quay lại Task 2/3.

- [ ] **Step 3: Đối chiếu 7 khu vực bằng trình duyệt**

Mở `/admin`, bấm lần lượt 7 tab. Với mỗi tab, mở tab Network của trình duyệt xác nhận **có request thật** tới `/api/v1/...`. Tab nào không phát request nghĩa là còn dữ liệu tĩnh.

- [ ] **Step 4: Sửa tick trong `progress/CHUNG.md`**

Chỉ tick `[x]` cho mục đã tự tay kiểm ở Step 3. Mục nào chưa xong để `[ ]`. Việc tự sửa trước tốt hơn nhiều so với bị phát hiện lúc `make progress` chạy trong buổi họp.

- [ ] **Step 5: Cập nhật `docs/PROJECT_CONTEXT.md` mục 9**

Hai chỗ đã lỗi thời cần sửa:
- **P0 #1** ("khoá lỗ hổng đăng ký tự do được role giảng viên/admin") — thực tế đã đóng từ trước: `src/api/auth_schemas.py:5` khoá `RegisterableRole = Literal["STUDENT"]`, có test `test_register_rejects_instructor_role` phủ. Đánh dấu đã xong kèm đường dẫn bằng chứng.
- **P0 #7** (risk policy versioning) — hoàn thành ở Task 10.

- [ ] **Step 6: Commit**

```bash
git add docs/
git commit -m "docs: cap nhat trang thai that cua role Admin sau khi hoan thien"
```

---

## Phụ lục: 3 việc nằm ngoài plan này nhưng liên quan

Ghi lại để không ai tưởng plan này đã phủ hết:

1. **File chuẩn bị RLS bị thiếu.** `docs/decisions/rls-migration-plan.md` (lấy từ nhánh `haidang2425` ngày 16/08) tham chiếu `scripts/sql/create_restricted_db_role.sql`, `migrations/versions/20260822_rls_academic_terms.py`, `src/db/tenant_scope.py` — **cả ba không tồn tại trên nhánh này**, chúng chỉ có trên `haidang2425`. P0 #3 trong mục 9 vì vậy không thể bắt đầu cho tới khi lấy 3 file đó về. Lưu ý migration RLS bên đó cũng đánh số `20260822`, trùng với migration lời mời ở Task 8 — khi lấy về phải đổi số một trong hai.
2. **`loadtest/locustfile.py` cũng thiếu** (P1 #9 tham chiếu tới), cùng lý do trên.
3. **`docs/PROJECT_CONTEXT.md` bị lặp nội dung.** Mục 1–22 xuất hiện hai lần (dòng 1–868 và 869–1489), hai bản có chỗ khác nhau — ví dụ mục 5 bản đầu tên là "Ba authorization role, bốn persona" còn bản sau là "Ba vai trò dùng sản phẩm". Người đọc hoặc AI đọc file này dễ vớ nhầm bản cũ. Nên dọn, nhưng là việc riêng, không thuộc plan Admin.
