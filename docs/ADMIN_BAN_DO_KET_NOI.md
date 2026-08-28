# Admin kết nối với Student/Instructor như thế nào — bản đồ đầy đủ

> Dành cho người phụ trách role Admin, chưa nắm code của 2 role kia.
> Mọi ô ✅/❌ đều đã kiểm bằng code trên nhánh `haidang2425`, không suy đoán.
> Ngày kiểm: 26/08/2026.
>
> **Cập nhật 27/08/2026 — mục 0 và mục 4 đã sửa lại cho khớp code:** commit
> `2f3fad1` (26/08) đã tick ✅ cho B1-B6 ở bảng hành động (mục 6) nhưng quên
> sửa phần thân mục 0/4, nên hai chỗ đó vẫn đọc như kiểu CẤP PHÁT ở mức 0%.
> Đã verify lại bằng code thật (`/admin/sections` có 5 route, `first_instructor_id()`
> đã bị xoá khỏi `semester_repository.py`) — kiểu CẤP PHÁT nay **đã có**, không
> còn là gốc của "không đồng bộ" nữa. Còn lại của Admin là 4 việc ở mục 6
> (C1-C3, D3), không liên quan tới kiểu CẤP PHÁT.

---

## 0. Trước hết: Admin nối với role khác bằng 4 kiểu, không phải 1

Đây là điều quan trọng nhất cần nắm. Rất nhiều nhầm lẫn "role có đồng bộ không"
đến từ việc gộp 4 kiểu này làm một.

| Kiểu | Nghĩa là gì | Chiều dữ liệu | Tình trạng hiện tại |
|---|---|---|---|
| **1. ĐỌC** | Admin xem lại thứ role khác đã tạo ra | role khác → Admin | 🟢 Student tốt (15 route) · 🔴 Instructor yếu (1 route) |
| **2. ĐẶT** | Admin chỉnh cấu hình, code của role khác tự đọc và tuân theo | Admin → role khác | 🟢 tốt, đây là phần làm chắc nhất |
| **3. NHẬN VIỆC** | Hoạt động của role khác tự đẩy việc vào hàng đợi Admin | role khác → Admin | 🟡 3/4 nguồn chạy, `DATA_REQUEST` vẫn câm (mục C3) |
| **4. CẤP PHÁT** | Admin tạo ra cái khung mà role khác hoạt động bên trong | Admin → role khác | 🟢 **xong 26/08** (B1-B6, xem mục 4) |

Kiểu 4 từng là gốc của "3 role không đồng bộ" — đã vá xong. Việc còn lại của
Admin (C1-C3, D3) nằm ở kiểu ĐỌC và NHẬN VIỆC, chi tiết ở mục 6.

---

## 1. Kiểu ĐỌC — Student sinh ra gì, Admin đọc được chưa

Tất cả route dưới đây nằm ở `src/api/admin_student360.py`, prefix
`/api/v1/admin/students/{student_id}`, UI ở `AdminStudent360.jsx`.
Mỗi route đều ghi audit **trước khi** trả dữ liệu (`_audited_read`) — pattern này
đã làm đúng, giữ nguyên khi thêm route mới.

### Đã đọc được (13 loại)

| Sinh viên tạo ra | Bảng DB | Route Admin |
|---|---|---|
| Kế hoạch tuần | `WeeklyPlan`, `DailyPlan`, `ScheduleBlock` | `/plans` |
| Việc cần làm | `StudyTask` | `/tasks` |
| Sự kiện tiến độ (bắt đầu/xong/hoãn) | `ProgressEvent` | `/progress-events` |
| Nhắc việc | `Reminder` | `/reminders` |
| Phiên tự học | `SelfStudySession` | `/sessions` |
| Assignment của SV | `Assignment` | `/assignments` |
| Bài đã nộp | `Submission` | `/submissions` |
| Phản tư cuối tuần | `WeeklyReflection` | `/reflections` |
| Hội thoại với AI (danh sách) | `Conversation` | `/conversations` |
| Nội dung 1 hội thoại | `Message` | `/conversations/{id}` |
| Tài liệu SV tự tải lên | `Document` | `/documents` |
| Tín hiệu rủi ro | `RiskSignal` | `/risk` |
| Can thiệp đã nhận | `InstructorIntervention` | `/interventions` |
| Ai đã đọc dữ liệu của SV này | `AuditLog` | `/access-history` |

### Chưa đọc được (7 loại)

| Sinh viên tạo ra | Bảng DB | Vì sao thiếu |
|---|---|---|
| **Câu hỏi bị guardrail chặn** | `GuardrailEvent` | 🔴 bảng **không bao giờ được ghi** — xem mục 3 |
| **Bài quiz đã làm** | `Quiz` + `Submission` | chỉ `quiz_service.py`/`quiz_repository.py` đọc, không service admin nào |
| **Bộ luyện tập AI** | `PracticeSet`, `PracticeItem` | chỉ `practice_set_service.py` |
| **Bộ nhớ cá nhân của AI về SV** | `StudentMemoryEntry`, `StudentMemoryConsent` | chỉ `student_memory_service.py` — **đây là dữ liệu cá nhân nhạy cảm, đáng lẽ Admin phải thấy khi xử lý DSAR** |
| **Học kỳ SV tự khai** | `SemesterSetup`, `SemesterCourse`, `SemesterWeekSlot` | chỉ `semester_service.py` |
| **Lịch cá nhân** | `CalendarEvent` | chỉ `canvas_routes.py` (router này đã tắt) |
| **SV tự xoá dữ liệu cá nhân** | — | `POST /student/personal-data/delete` xoá thật nhưng **không ghi audit** → Admin không biết chuyện đã xảy ra |

---

## 2. Kiểu ĐỌC — Instructor sinh ra gì, Admin đọc được chưa

Đây là phần **yếu nhất**. Toàn bộ `src/api/admin_instructor360.py` chỉ có **1 route**
(`GET /admin/instructors/{id}/summary`) và chỉ chạm 5 bảng.

| Giảng viên tạo ra | Bảng DB | Admin đọc được? |
|---|---|---|
| Lớp đang phụ trách | `CourseSection`, `Enrollment`, `Course` | ✅ Instructor360 |
| Can thiệp rủi ro | `InstructorIntervention` | ✅ Instructor360 (số đếm + tỷ lệ xử lý) |
| **Quyết định "Mở chặn"/"Giữ chặn" guardrail** | `GuardrailEvent.review_status` | ❌ và **cũng không vào audit log** — xem mục 3 |
| **Ghi chú riêng về từng SV** | `InstructorStudentNote` | ❌ chỉ `instructor.py` đọc |
| **Nhật ký buổi học (dạy/huỷ/dạy bù)** | `ClassActivity` | ❌ |
| **Quiz đã tạo / publish** | `Quiz`, `QuizQuestion` | ❌ |
| **Duyệt/từ chối bộ luyện tập** | `PracticeSet` | ❌ |
| **Digest email đã gửi cho ai** | — | ❌ không lưu ở đâu cả |

**Ý nghĩa thực tế:** hiện Admin không trả lời được những câu rất cơ bản như
*"giảng viên X tháng này có dạy đủ buổi không"*, *"ai đã mở chặn câu hỏi nào"*,
*"quiz nào đang publish cho sinh viên"*.

---

## 3. Kiểu NHẬN VIỆC — 2 trong 4 nguồn không bao giờ phát

Work Queue của Admin (`src/services/core/admin_overview_service.py:170`)
nhận 4 loại việc:

| Loại | Nguồn phát | Có chạy không |
|---|---|---|
| `RISK_SIGNAL` | `RiskEngine` khi SV có dấu hiệu tụt lại | ✅ chạy thật |
| `INGEST_JOB` | `CourseIngestJob` khi nạp tài liệu lỗi | ✅ chạy thật |
| `GUARDRAIL_EVENT` | lẽ ra là khi SV bị chặn | ❌ **không ai ghi `GuardrailEvent`** |
| `DATA_REQUEST` | lẽ ra là khi SV/GV xin trích xuất dữ liệu | ❌ **không ai ghi `DataRequest`** |

Kiểm chứng:

```bash
grep -rn "GuardrailEvent(" src/     # → chỉ ra định nghĩa class, không có chỗ tạo
grep -rn "DataRequest(" src/        # → chỉ ra định nghĩa class, không có chỗ tạo
```

Hệ quả dây chuyền cho Admin:
- Ô "GUARDRAIL_EVENT" và "DATA_REQUEST" trong Work Queue **vĩnh viễn bằng 0**
  (trừ khi seed bằng `scripts/provision_demo_personas.py`).
- Tab "Yêu cầu dữ liệu" là một màn hình xử lý hoàn chỉnh nhưng không có đường vào.
- Hàng đợi duyệt guardrail của Giảng viên cũng rỗng theo — cùng một nguyên nhân.

---

## 4. Kiểu CẤP PHÁT — đã có, xong 26/08 (B1-B6)

### Vấn đề đã có (lịch sử, để hiểu vì sao B1-B6 quan trọng)

`CourseSection` (lớp học) và `Enrollment` (SV thuộc lớp nào) là **xương sống**
của cả hệ thống: Giảng viên chỉ thấy SV trong lớp `instructor_id` trỏ về mình,
mọi cảnh báo rủi ro, mọi hàng đợi duyệt đều lọc theo đó.

Trước 26/08, 2 bảng này được tạo ở 6 nơi, **không nơi nào là Admin** — trong đó
khi sinh viên tự khai môn, hệ thống chọn **giảng viên đầu tiên tìm thấy trong
tổ chức** (`first_instructor_id()`, cũ), bất kể GV đó có thật sự dạy SV này hay
không. Hậu quả: GV thấy SV mình không hề dạy trong roster + danh sách cảnh báo
rủi ro, và Admin không có UI/API nào để sửa lại.

### Đã sửa thế nào (B1-B6, commit `24013a0` `8e61490` `7aedc71` `bfd2ff0`)

- `first_instructor_id()` đã bị **xoá hẳn** khỏi `semester_repository.py`.
  `get_or_create_section()` giờ nhận `instructor_id: str | None = None` — SV tự
  khai môn thì lớp được tạo **không gán GV** thay vì gán bừa.
- Lớp chưa có GV tự đẩy vào Work Queue của Admin qua trigger
  `UNASSIGNED_SECTION` (`admin_overview_service.py:301`), Admin gán tay sau.
- Route mới `src/api/admin_sections.py` cho Admin **CRUD lớp + gán/đổi GV +
  quản lý roster** trực tiếp, không phải chỉ chờ SV tự khai.

### Kiểu CẤP PHÁT — bảng hiện trạng (đã verify qua `openapi.json`)

| Việc Admin đáng lẽ phải làm được | Hiện tại |
|---|---|
| Tạo/sửa lớp (`CourseSection`) | ✅ `POST/PATCH /admin/sections`, `GET /admin/sections/courses` |
| Gán giảng viên vào lớp | ✅ cùng route trên; `CreateInviteRequest` cũng có field chọn lớp khi mời GV mới (B5) |
| Quản lý danh sách SV trong lớp (`Enrollment`) | ✅ `GET/POST/DELETE /admin/sections/{id}/roster[/{student_id}]` |
| Reset mật khẩu người dùng | ✅ `POST /admin/users/{id}/reset-password` |
| **Gửi thông báo tới Giảng viên** | ✅ route ghi `AdminAnnouncement` đã thêm vào `src/api/admin.py` (A4); panel bên GV (`instructor.py:54`) đọc được |

Chi tiết từng commit: xem bảng Nhóm B ở mục 6.

---

## 5. Kiểu ĐẶT — phần đã làm tốt, giữ nguyên

Đây là mảng Admin đã nối đúng. Ghi lại để bạn biết cái gì **không cần đụng vào**.

| Admin đặt gì | Role khác tiêu thụ ở đâu | Bằng chứng |
|---|---|---|
| Trọng số/ngưỡng risk | `RiskEngine` → cảnh báo của GV | `risk_engine.py:75 _load_active_policy()` đọc `RiskPolicy` active; có preview → publish → rollback + versioning |
| Bật/tắt guardrail rule | chặn câu hỏi của SV | `guardrail_rule_repository.py`; rule `core_locked` không tắt được kể cả bởi Admin |
| Học kỳ + lịch thi | Wizard học kỳ, lịch học, task "ôn thi" của SV | `AcademicTerm`/`CourseExam` → `semester_service.py`, `lecture_plan_service.py`, `timetable_service.py` |
| Tài liệu môn học | citation trong câu trả lời AI cho SV | `admin_document_ingest_service.py` → `DocumentChunk` → `chunk_repository.list_chunks_for_course` |
| Cấu hình tổ chức | chế độ demo, tự động cảnh báo | `AdminSettings` |
| Đồng bộ EduSync | curriculum + deadline | `MockLmsSyncVersion`, preview/publish/rollback |

⚠️ **Một lỗ trong mảng này:** tài liệu ở trạng thái `DRAFT` đã vào RAG của sinh viên.
Chunk được tạo ngay lúc upload, còn bộ lọc phía đọc (`chunk_repository.py:83`)
chỉ loại `ARCHIVED`. Nghĩa là Admin bấm "Upload" là sinh viên trích dẫn được ngay,
chưa cần bấm "Validate" hay "Publish".

---

## 6. Vậy Admin cần thêm gì — danh sách theo thứ tự nên làm

> **Cập nhật 27/08 — 15/17 mục đã xong, 4 mục còn lại đã đóng phạm vi.**
> Nhóm A: **4/4** · Nhóm B: **6/6** · Nhóm C: **0/4 — 🚫 đã quyết định không làm** · Nhóm D: **3/3**
> Ô nào đã xong được đánh dấu ✅ kèm commit ngay trong bảng bên dưới.
> Ô 🚫 là **đã quyết định không làm**, không phải việc còn treo — lý do ở ADR-021
> và mục Known Limitations trong `README.md`.


### Nhóm A — Sửa mạch đứt (nhỏ, giá trị cao nhất)

| # | Việc | Sửa ở đâu | Vì sao ưu tiên |
|---|---|---|---|
| A1 ✅ `28ea303` `215a8c5` | **Ghi `GuardrailEvent` khi chặn** | `qa_service.py:72` + `companion_service.py:110` | Mở lại cùng lúc: hàng đợi GV, ô Work Queue của Admin, và số liệu "câu hỏi bị chặn" cho báo cáo |
| A2 ✅ `99a2ade` | **Chặn chunk `DRAFT` khỏi RAG** | `chunk_repository.py:83` đổi thành chỉ nhận `PUBLISHED` | 1 dòng; đúng lại cam kết vòng đời tài liệu Admin đang bán |
| A3 ✅ `e306184` | **Audit 3 hành động đang mất dấu** | `instructor.py:709` (mở chặn), `instructor.py:327` (can thiệp lẻ), `student.py:677` (SV tự xoá) | Cả 3 đều đổ vào Audit log mà Admin đọc |
| A4 ✅ `138f1de` | **Route ghi `AdminAnnouncement`** | thêm vào `src/api/admin.py` | Panel bên GV đã có sẵn, chỉ thiếu đầu ghi |

### Nhóm B — Bổ sung kiểu CẤP PHÁT (đây là phần lớn nhất, và là việc của bạn)

| # | Việc | Gợi ý đặt ở đâu |
|---|---|---|
| B1 ✅ `24013a0` | CRUD lớp học: tạo/sửa `CourseSection` | route mới `src/api/admin_sections.py`, nav mục "Lớp học" nhóm Quản trị |
| B2 ✅ `24013a0` | Gán/đổi giảng viên phụ trách lớp | cùng B1 |
| B3 ✅ `8e61490` | Quản lý `Enrollment` (thêm/bớt SV khỏi lớp) | cùng B1 |
| B4 ✅ `7aedc71` | Bỏ `first_instructor_id()` | `semester_repository.py:167` — khi SV khai môn mà lớp chưa được Admin cấp, tạo section **không gán GV** thay vì gán bừa, rồi đẩy 1 item vào Work Queue để Admin gán |
| B5 ✅ | Field chọn lớp khi mời giảng viên | `CreateInviteRequest` trong `src/schemas/admin_schemas.py` |
| B6 ✅ `bfd2ff0` | Reset mật khẩu người dùng | `src/api/admin.py`, cạnh `PATCH /admin/users/{id}/status` |

> B4 là mẹo đáng giá: thay vì xây thêm màn hình mới, tận dụng Work Queue đã có sẵn
> để biến "lớp chưa có giảng viên" thành một việc Admin nhìn thấy và xử lý được.

### Nhóm C — Mở rộng kiểu ĐỌC

| # | Việc | Ghi chú |
|---|---|---|
| C1 🚫 | Instructor 360 thêm: `ClassActivity`, `Quiz`, `PracticeSet`, quyết định guardrail | **Bỏ khỏi phạm vi** — công lớn, không phục vụ F6/F7. Ghi ở Known Limitations |
| C2 🚫 | Student 360 thêm: `StudentMemoryEntry` (+ consent), quiz, practice, `SemesterSetup` | **Bỏ** — Student 360 đã có 15 route. `StudentMemoryEntry` chỉ có ý nghĩa nếu mở DSAR, mà đã quyết định không mở (ADR-021) |
| C3 🚫 | Đường vào DSAR (`POST /me/data-requests` cho SV/GV) | **Đã đóng — tab đã gỡ khỏi điều hướng** (ADR-021). ⚠️ Không đồng nghĩa FR-1.3 đã xong: phạm vi xoá self-service vẫn thiếu so với spec, xem Known Limitations |
| C4 🚫 | `InstructorStudentNote` cho Admin | **Đã quyết định không mở** (ADR-021) — ghi chú riêng tư của GV; có quyền kỹ thuật để đọc không có nghĩa là nên đọc |

### Nhóm D — Đo chi phí/độ trễ AI (PLO 5)

| # | Việc |
|---|---|
| D1 ✅ | Bọc `get_llm()` (`src/services/core/llm.py`) bằng callback ghi `model`/`input_tokens`/`output_tokens`/`latency_ms` |
| D2 ✅ | Bảng `ai_usage` mới — **có `created_at`, có `organization_id`, `message_id` nullable**. Không tái dùng `RAGTrace`/`LLMUsageEvent` (ADR-017 đã đóng 2 bảng đó có lý do: FK `message_id` NOT NULL) |
| D3 ✅ | Màn "Chi phí AI" — `GET /api/v1/admin/ai-usage` (`src/api/admin_ai_usage.py`) + panel `AdminAiUsage.jsx`, nav nhóm Theo dõi, 8 test. Bảng giá `src/services/core/ai_pricing.py` **chưa điền đơn giá** nên cột chi phí báo "chưa có đơn giá" — token/độ trễ/tỷ lệ lỗi là số thật |

---

## 7. Ghi chú: các bảng "chết" khác trong schema

Ngoài `RAGTrace`/`LLMUsageEvent`, các bảng sau **không được đọc/ghi ở bất kỳ đâu**
trong `src/api`, `src/services`, `src/repositories`:

`ResourceAccessEvent` · `ReplanProposal` · `LearningGoal` · `ReminderDelivery` · `Rubric`

Không phải việc gấp, nhưng nếu ai đó bảo bạn "dữ liệu đó có sẵn trong DB rồi" thì
nên kiểm lại trước khi tin — có bảng không đồng nghĩa với có dữ liệu.

---

## 8. Nếu chỉ làm được 5 việc

1. **A1** — ghi `GuardrailEvent` (mở lại cả 1 vòng HITL)
2. **A2** — chặn DRAFT khỏi RAG (1 dòng)
3. **B1+B2** — CRUD lớp + gán giảng viên (gốc của "không đồng bộ")
4. **A3** — audit 3 hành động
5. ~~**D1+D2** — bắt đầu ghi số liệu chi phí AI~~ ✅ **xong 26/08** — cả 5 việc tối thiểu đã đủ
