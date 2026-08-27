# Audit trạng thái dự án Cursus — 26/08/2026

> Bản này kiểm bằng **code thật + chạy test thật**, không dựa vào `docs/PROJECT_CONTEXT.md`.
> Mọi kết luận đều có đường dẫn file/dòng để tự kiểm chứng lại.
> Nhánh: `haidang2425` · commit `ce93373` (26/08 00:34).

---

## 1. Dự án đang ở đâu

| Hạng mục | Trạng thái thật hôm nay |
|---|---|
| Test suite | **4 failed · 522 passed · 7 skipped** (4 phút 14) |
| Docs đang ghi | 483 passed · 0 failed (24/08) → **đã lệch, docs cũ hơn code** |
| Working tree | **40 file sửa chưa commit**, ~2.100 dòng thêm / 1.168 dòng xoá |
| File chưa track | 12 file curriculum mới + 8 thư mục `.pytest-tmp-*` rác |
| 20 commit gần nhất | ~18 commit là **Mock LMS (EduSync)** UI/hero/SSO |
| P0#3 RLS | **vẫn 0%** — xác nhận bằng code, không phải bằng docs |

### 1.1. Ba ngày qua làm gì

Toàn bộ trọng tâm nằm ở Mock LMS: redesign hero, wordmark serif, video ngày/đêm,
dark mode, EN/VI, SSO. Core sản phẩm (Student / Lecturer / Admin) **không có commit nào**
trong giai đoạn này.

### 1.2. Đợt Admin đang dở, chưa commit

Working tree đang giữ một đợt rebuild Admin khá lớn chưa được commit:

```
src/api/admin.py                                   +361
src/services/rag/admin_document_ingest_service.py  +183
frontend/src/components/admin/AdminConsole.jsx     -662  (đập tab → route)
frontend/src/components/admin/AdminGuardrailRules.jsx  +233
frontend/src/components/admin/AdminCourseDocuments.jsx +234
src/schemas/admin_schemas.py                        +98
+ 6 file test admin
```

Route mới thêm (chưa commit): `/analytics/summary`,
`/guardrail-rules/{code}/preview`, `/guardrail-rules/versions/{v}/rollback`,
`/courses/{code}/documents/{id}/content`, `.../versions`, `.../rollback`,
`/invites/{id}/resend`.

**Rủi ro:** 2.100 dòng chưa commit = mất trắng nếu checkout nhầm nhánh.

### 1.3. Nguyên nhân 4 test đỏ

12 file `docs/planning/v2/data/chunks_*.json` mới được thêm (EXE101, PEN,
PHE_COMx1-3, SE_COMx1-4, SE_GRA_ELE, SWT301, TMI_ELE) dùng **schema khác**:

```
34 file cũ:  { "meta": {...}, "chunks": [...] }
12 file mới: { "subject_code": ..., "subject_name": ..., "chunks": [...] }   ← thiếu "meta"
```

Hệ quả:

```
test_discovers_the_expected_34_new_real_courses  →  AssertionError: 39 == 34
test_every_real_course_file_parses...            →  AssertionError: EXE101, meta = {}
test_every_real_course_answers_in_scope[PEN]     →  fail
test_every_real_course_answers_in_scope[SE_GRA_ELE] → fail
```

### 1.4. RLS — xác nhận lại bằng code

`src/db/tenant_scope.py` tồn tại nhưng **không được import ở bất kỳ đâu trong `src/`**.
Chính docstring của file tự khai:

> *"written and unit-testable, but **not yet wired into any route** — every endpoint
> still depends on the plain `get_db`"*

Policy RLS trong migration (`20260812`, `20260821`, `20260822`) dùng
`current_setting('app.current_org_id')` — biến session này **không nơi nào set**,
nên policy đang là inert. Cách ly tổ chức hiện **100% dựa vào filter Python**.

---

## 2. Các role có đồng bộ với nhau không?

### 2.1. Phần đồng bộ tốt — nền RBAC

Có **một nguồn sự thật duy nhất**: `src/security/permissions.py` —
4 role × 17 resource × 6 permission trong `PERMISSION_MATRIX`, thực thi qua
`require_roles` + `require_permission` + **11 ownership guard**
(`src/security/ownership.py`).

Điểm làm tốt: `READ_SENSITIVE` được tách riêng khỏi `READ`, chỉ Admin có,
và dùng cho đúng 14 route đọc dữ liệu gốc của sinh viên — nên một role chỉ có
`READ` thông thường không bao giờ "vô tình" thoả mãn được.

### 2.2. Điểm lệch nghiêm trọng nhất — không role nào sở hữu "lớp học"

`CourseSection` và `Enrollment` được tạo ở 7 nơi:

```
src/repositories/semester_repository.py:192   ← Wizard học kỳ của SINH VIÊN
src/services/academic/timetable_service.py:276
src/services/mock/gate2_demo.py:620
src/services/mock/student_mock_data_service.py:409
scripts/provision_demo_personas.py:113
scripts/seed_extra_users.py:157
```

**Không có route Admin nào.** Và khi sinh viên tự khai môn trong Wizard,
hệ thống gán lớp cho giảng viên bằng:

```python
# src/repositories/semester_repository.py:167
def first_instructor_id(self, organization_id):
    instructor = self._db.query(models.User).filter(
        models.User.role.in_(["INSTRUCTOR", ...]),
        models.User.organization_id == organization_id,
    ).first()          # ← giảng viên ĐẦU TIÊN tìm thấy, bất kỳ ai
```

Chuỗi hệ quả: SV tự khai môn → hệ thống gán 1 GV bất kỳ trong tổ chức →
**GV đó thấy SV này trong roster + danh sách cảnh báo rủi ro** dù không hề dạy
môn đó → Admin **không có cách nào sửa** vì không có UI/API quản trị lớp.

Đây là chỗ 3 role lệch nhau nặng nhất trong toàn hệ thống.

### 2.3. Lỗi nhỏ nhưng thấy ngay — sidebar Giảng viên không dịch

`frontend/src/App.jsx:250-300` — 6/7 nhãn là chuỗi tiếng Việt cứng:

```jsx
<span>Rủi ro & Cảnh báo</span>     <span>Hoạt động lớp</span>
<span>Quản lý Quiz</span>          <span>Bài tập nộp</span>
<span>Digest</span>                <span>Xét duyệt Guardrail</span>
```

Chỉ `nav.instructorHome` dùng `t()`. Đây đúng là loại bug đã từng được vá ở
commit `6f33d9d` (23/08) — **đã tái phát** khi thêm các mục nav mới.
Sidebar Student và Admin (`AdminNavigation.jsx`) thì i18n đầy đủ.

---

## 3. Chức năng các role có liên kết với nhau không?

### 3.1. Sáu mạch chạy thật (đã kiểm bằng code)

| # | Mạch | Bằng chứng |
|---|---|---|
| 1 | **Admin đặt học kỳ/lịch thi → kế hoạch của SV** | `AcademicTerm`/`CourseExam` → `semester_service.py`, `lecture_plan_service.py`, `timetable_service.py` → task "ôn thi" tự sinh |
| 2 | **Admin chỉnh Risk Policy → cảnh báo của GV** | `risk_engine.py:75 _load_active_policy()` đọc `RiskPolicy` active → `self._weights[...]` dùng ở 5 rule. Có preview / publish / rollback / versioning |
| 3 | **Admin nạp tài liệu → citation của SV** | `admin_document_ingest_service.py` → `DocumentChunk` → `chunk_repository.list_chunks_for_course` → RAG (⚠️ có 1 lỗ, xem 3.2.4) |
| 4 | **SV xin bộ luyện tập → GV duyệt → SV nhận** | `practice.py` `student_router.post("/request")` (202) → `instructor_router.post("/{id}/review")` |
| 5 | **SV bật chia sẻ phản tư → GV đọc được** | `share_reflection_summary` → `instructor.py:853` (mặc định `False`, đúng nguyên tắc consent) |
| 6 | **Admin quan sát SV/GV** | Student 360 (14 route, audit-trước-trả-sau) + Instructor 360 + People Explorer + Work Queue |

### 3.2. Bốn mạch bị ĐỨT

#### 3.2.1. 🔴 SV bị chặn → hàng đợi duyệt của GV: không có gì chảy qua

`GuardrailEvent` **không được tạo ở bất kỳ đâu trong `src/`**:

```
grep "GuardrailEvent(" src/  →  chỉ có 1 hit: định nghĩa class ở models.py:704
```

- `QaService.ask()` khi bị chặn: chỉ `logger.info("qa_blocked ...")` rồi `return`
  (`src/services/ai/qa_service.py:72-91`) — không ghi `Message`, không ghi `GuardrailEvent`.
- `companion_service.send_message()` khi bị chặn: lưu message với
  `metadata={"mode": "blocked"}` nhưng **không** tạo `GuardrailEvent`
  (`src/services/ai/companion_service.py:110-145`).

Trong khi đó `GET /instructor/guardrail-reviews` query đúng
`GuardrailEvent.classification == "BLOCKED"` (`instructor.py:665`).

**Hệ quả:** hàng đợi duyệt của GV và ô `GUARDRAIL_EVENT` trong Work Queue của Admin
**chỉ có dữ liệu khi seed** (`scripts/provision_demo_personas.py`) hoặc test fixture.
Trong runtime thật, sinh viên bị chặn bao nhiêu lần cũng không ai biết.

Đây là F5 HITL — chạm trực tiếp **2 trong 6 ràng buộc bắt buộc của BTC**
(#1 chống lạm dụng "làm hộ bài", #4 HITL cho giảng viên).

#### 3.2.2. 🔴 GV "Đánh dấu đã can thiệp" → SV không nhận được gì

`InstructorIntervention` chỉ được đọc ở đúng 1 nơi: `src/services/mock/gate2_demo.py:764`.
Không route nào phía sinh viên đọc bảng này. Không notification, không message,
không hiển thị. Vòng lặp HITL đóng lại **bên trong UI của giảng viên**, sinh viên
hoàn toàn không biết mình vừa được can thiệp.

#### 3.2.3. 🔴 DSAR: có màn hình xử lý, không có đường vào

`DataRequest` **không được tạo ở bất kỳ đâu** (`grep "DataRequest(" src/` → chỉ có class).
6 route Admin (`list` / `process` / `reject` / `complete` / `delete-preview` /
`delete-confirm`) đều là bên tiêu thụ.

SV có kênh riêng `POST /student/personal-data/delete` nhưng nó **xoá thẳng**,
không sinh `DataRequest`, và **không ghi audit log**.

**Hệ quả:** tab "Yêu cầu dữ liệu" chỉ chạy được nếu insert tay vào DB.
Và khi SV tự xoá dữ liệu, Admin không có bất kỳ dấu vết nào.

#### 3.2.4. 🟠 Tài liệu DRAFT đã lọt vào RAG của sinh viên

`admin_document_ingest_service.py` tạo chunk **ngay lúc upload**, với
`publication_status="DRAFT"` (dòng 183 + `self._chunk(...)` dòng 193).

Nhưng bộ lọc phía đọc chỉ loại `ARCHIVED`:

```python
# src/repositories/chunk_repository.py:83
if source == "admin_curriculum" and document.publication_status == "ARCHIVED":
    continue
```

→ Một tài liệu vừa upload, **chưa validate, chưa publish**, đã có thể được trích dẫn
cho sinh viên. Trái với cam kết trong `PROJECT_CONTEXT.md` mục 6.5:
*"Chỉ tài liệu Published mới vào RAG"*. Không có test nào chặn điều này.

---

## 4. Admin nắm được hết hoạt động chưa?

### 4.1. Nắm được (đã kiểm)

- **Nhịp trường** (`build_overview`, org-scoped, mỗi metric kèm `method_note` nên
  không bịa số): active students/instructors, courses, sections,
  SV có risk HIGH chưa xử lý, tỷ lệ kích hoạt lời mời.
- **Work Queue 4 loại**: `RISK_SIGNAL`, `GUARDRAIL_EVENT`, `DATA_REQUEST`, `INGEST_JOB`
  — có `workQueueHref()` điều hướng đúng tới nơi xử lý.
- **Student 360** — 14 route, mỗi route ghi audit **trước khi** trả dữ liệu:
  plans · tasks · progress-events · reminders · sessions · assignments ·
  submissions · reflections · conversations (+ chi tiết) · documents · risk ·
  interventions · access-history.
- **Instructor 360** — sections, interventions, tỷ lệ xử lý risk.
- **Quản trị**: curriculum + document lifecycle 6 bước · guardrail rules (có
  `core_locked` chống chính Admin tắt nhầm) · risk policy versioning + rollback ·
  users lock/unlock · invites · academic term/exam · EduSync sync
  (preview/publish/rollback) · audit log (đã org-scoped) · analytics.

### 4.2. KHÔNG nắm được — 8 điểm mù

| # | Điểm mù | Bằng chứng | Mức |
|---|---|---|---|
| 1 | **Chi phí AI = 0 số liệu; độ trễ chỉ có ở tầng HTTP** | Xem mục 4.3 bên dưới — đây là hạng mục đã được đính chính so với bản đầu | 🟠 PLO 5 thiếu 1/3 vế |
| 2 | **GV "Mở chặn" guardrail không vào audit log** | `decide_guardrail_review` (`instructor.py:709`) trả về field `auditMetadata` trong response nhưng **không gọi `log_event`** — nhìn như có audit mà không có | 🔴 |
| 3 | **Can thiệp lẻ của GV không audit** | Chỉ `BULK_UPDATE_RISKS` được ghi (`instructor.py:418`). `POST /risks/{id}/intervention` (dòng 327) thì không | 🔴 |
| 4 | **SV tự xoá dữ liệu cá nhân không để lại dấu vết** | `POST /student/personal-data/delete` xoá reflections + conversations + messages, **không `log_event`** | 🔴 |
| 5 | **Admin không quản trị được lớp học** | Không route tạo/sửa `CourseSection`, không gán GV vào lớp, không quản lý enrollment. `adminNavigationConfig.js` không có mục nào | 🔴 |
| 6 | **Hoạt động GV thiếu ở Instructor 360** | Không thấy: ghi chú riêng về SV · quiz đã tạo/publish · nhật ký buổi học · digest email đã gửi · quyết định guardrail | 🟠 |
| 7 | **Hoạt động SV thiếu ở Student 360** | Không thấy: quiz submission · practice set · self-study session · student memory · semester setup | 🟠 |
| 8 | **Không reset được mật khẩu người dùng** | `PROJECT_CONTEXT.md` 6.5 mục 6 ghi *"hỗ trợ reset mật khẩu an toàn"* — không có route, không có UI | 🟠 |

### 4.3. Đính chính + làm rõ hạng mục "chi phí / độ trễ AI"

> Bản đầu của báo cáo này ghi *"`RAGTrace` (có cột `prompt_tokens`, `cost`)"* và xếp
> mức 🔴 "chạm ràng buộc BTC #6". **Cả hai đều cần đính chính** — nội dung dưới đây
> là bản đã kiểm lại.

**Sai ở đâu:** `RAGTrace` **không** có cột chi phí nào. Nguyên văn `src/db/models.py:688-701`:

```python
class RAGTrace(Base):            # id, message_id, retrieved_chunks(JSON), generation_metadata(JSON)
class LLMUsageEvent(Base):       # id, message_id, model, prompt_tokens, completion_tokens, cost
                                 # ← không có cột thời gian nào
```

**Điều vẫn đúng:** cả hai bảng chưa từng được ghi, chưa từng được đọc.
`grep -rn "RAGTrace\|LLMUsageEvent" src/` cho đúng 3 dòng: 2 định nghĩa class +
1 docstring ở `qa_answer_service.py:84` giải thích *tại sao không dùng*. Bảng vẫn
được tạo trong DB (`migrations/versions/20260808_baseline_schema.py:42, 67`) →
có bảng rỗng nằm sẵn trong Postgres.

**Đây là quyết định có chủ đích, không phải quên.** `docs/PENDING_DECISIONS.md` #1
(✅ RESOLVED 22/08) + ADR-017: `message_id` là FK NOT NULL, mà `plan_builder`/
`reflection_engine` không sinh `Message` nào để gắn vào. Nguyên văn:
*"permanently dead schema for this purpose — this is a decided outcome, not an oversight"*.
Cái đã ship thay thế (Option B) là trace **chất lượng** (`llm_attempted`/`llm_success`/
`fallback_used`/`retrieval_empty`), không phải trace **chi phí**.

**Đề bài yêu cầu ở 3 chỗ:**

| Nguồn | Nguyên văn |
|---|---|
| `PROJECT_CONTEXT.md:130` — ràng buộc bắt buộc #6 (EDU-01) | "Kiểm soát chi phí/độ trễ token cho quy mô 1.000 sinh viên dùng đồng thời" |
| `PROJECT_CONTEXT.md:151` — Quy định chung mục 4, áp dụng **mọi** đề tài | "…theo dõi tối thiểu **độ trễ/lỗi/chi phí**…" |
| `PROJECT_CONTEXT.md:162` — **PLO 5**, 1 trong 8 năng lực bị chấm | "Deploy thật, **giám sát cơ bản (độ trễ/lỗi/chi phí)**, tích hợp hệ thống ngoài khi cần" |

**Mức độ thật — tách 3 vế của PLO 5:**

| Vế | Trạng thái | Bằng chứng |
|---|---|---|
| lỗi | ✅ khá ổn | structured logging, ingest job status + error, cờ `degraded`, 4 field trace Option B |
| độ trễ | 🟠 một phần | chỉ `src/security/middleware.py:31-41` — đo mỗi HTTP request, ghi log, không tách phần LLM, không lưu |
| chi phí | ❌ không có | `src/services/core/llm.py` là factory 30 dòng, không callback, không đọc `usage_metadata`, không bấm giờ |

**Hai lưu ý về docs:**
- Mục 2.7 (bảng team tự đối chiếu 13 dòng yêu cầu BTC) **không có dòng nào** về giám sát
  chi phí/độ trễ → không phải bị loại khỏi phạm vi có chủ đích, mà là chưa từng được theo dõi.
- Mục 12 có loại "Observability 3 lớp đầy đủ (SLO/SLI)" — nhưng đó là bản đầy đủ, không phải
  "giám sát cơ bản" mà PLO 5 hỏi. Và câu *"hiện chỉ có Sentry"* trong mục đó **không đúng**:
  `grep -rn "sentry" src/ requirements.txt .env.example` → 0 kết quả.
- Load test cũng không bù được: `loadtest/README.md` chạy với `GOOGLE_API_KEY=test-key`
  → 1.000 user nhưng **không gọi LLM thật lần nào**, chỉ đo FastAPI + Postgres.
  `docs/evidence/` không có thư mục kết quả load test nào.

**Việc cần làm nhỏ hơn tưởng:** `ChatGoogleGenerativeAI` đã trả sẵn `usage_metadata`
trên mỗi response. Chỉ cần (1) bọc `get_llm()` bằng callback ghi
`model / input_tokens / output_tokens / latency_ms` + `perf_counter` quanh lời gọi,
(2) bảng `ai_usage` mới — **có `created_at`, có `organization_id`, `message_id` nullable**
(đúng 3 điểm khiến `LLMUsageEvent` cũ không dùng được, đừng lặp lại). Có dữ liệu rồi thì
kể cả chưa kịp dựng UI, một truy vấn SQL cũng đủ trả lời khi bảo vệ.

---

Thêm 1 lỗi nhỏ: `failed_jobs` trong `build_overview` **không lọc theo tổ chức**
(`CourseIngestJob` không có org filter) → `system_status` của tổ chức A bị "DEGRADED"
vì job hỏng của tổ chức B.

---

## 5. Nên làm gì tiếp — xếp theo giá trị/công sức

### P0 — chạm trực tiếp vào ràng buộc bắt buộc của đề bài

1. **Ghi `GuardrailEvent` khi chặn** — thêm vào `qa_service.ask()` và
   `companion_service.send_message()`. Nối lại F5 HITL. Việc nhỏ (~1 chỗ mỗi service),
   giá trị lớn nhất trong danh sách này.
2. **Chặn chunk DRAFT khỏi RAG** — sửa điều kiện ở `chunk_repository.py:83` thành
   *"chỉ nhận `PUBLISHED`"* + 1 test hồi quy.
3. **Audit hoá 3 hành động đang mất dấu**: GV mở chặn guardrail, GV can thiệp lẻ,
   SV tự xoá dữ liệu.
4. **Sửa 4 test đỏ** — chuẩn hoá 12 file `chunks_*.json` mới về schema có `meta`,
   hoặc cập nhật parser + con số 34 → 39.
5. **Commit đợt Admin đang dở** (2.100 dòng) trước khi làm gì khác.

### P1 — đóng các điểm mù của Admin

6. **Admin quản trị lớp**: tạo section, gán GV, quản lý enrollment
   → thay `first_instructor_id()` bằng lựa chọn có chủ đích.
7. **Đo chi phí/độ trễ LLM** (xem mục 4.3): bảng `ai_usage` mới — **không** tái dùng
   `RAGTrace`/`LLMUsageEvent`, hai bảng đó đã bị ADR-017 đóng có lý do. Ưu tiên có
   *dữ liệu* trước, màn hình Admin sau — thiếu UI vẫn trả lời được bằng SQL.
8. **Đường vào DSAR** (`POST /me/data-requests` cho SV/GV) — hoặc gỡ tab nếu không kịp,
   để không có màn hình rỗng khi demo.
9. **Phản hồi can thiệp về phía SV** — ít nhất 1 thông báo "giảng viên đã liên hệ".
10. **i18n sidebar Giảng viên** — 6 chuỗi, việc 5 phút.

### P2

11. **RLS đa tổ chức** — plan đã sẵn (`docs/decisions/rls-migration-plan.md`),
    cần thao tác trên Supabase Dashboard.
12. Dọn 8 thư mục `.pytest-tmp-*` + `.env.bak-develop` khỏi repo root.

---

## Phụ lục — lệnh tự kiểm chứng

```bash
./.venv/Scripts/python.exe -m pytest tests/ -q --no-header
```

```bash
grep -rn "GuardrailEvent(" src/
```

```bash
grep -rn "DataRequest(" src/
```

```bash
grep -rn "tenant_scope" src/
```
