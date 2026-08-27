# Đợt push 26/08/2026 — Đồng bộ 3 role + hoàn thiện Admin

> Dành cho thành viên team đọc trước/sau khi pull. Mô tả **20 commit** đưa nhánh
> `haidang2425` từ trạng thái cũ trên GitHub lên trạng thái hiện tại.
>
> **Baseline:** `origin/haidang2425` (trước push) → `7022167` (sau push)
> **Quy mô:** 50 file thay đổi, +3813 / −160 dòng
> **Test:** 548 passed, 7 skipped, 0 failed · thêm 34 test function mới

---

## ⚠️ Đọc mục này trước khi làm gì khác

### 1. Bắt buộc chạy migration sau khi pull

Đợt này có **2 migration**. Không chạy thì backend sẽ crash hoặc trả 500.

```bash
./.venv/Scripts/python.exe -m alembic upgrade head
```

Head sau khi chạy: `20260909_instructor_nullable`

| Migration | Làm gì |
|---|---|
| `20260908_guardrail_event_scoping` | `guardrail_events` có thêm `student_id` + `section_id` riêng; `message_id` thành nullable + `SET NULL` |
| `20260909_section_instructor_nullable` | `course_sections.instructor_id` cho phép NULL (để Admin tạo lớp trước, gán giảng viên sau) |

### 2. `.env.bak` đã bị bỏ khỏi git

File này từng bị commit kèm **giá trị secret thật** và đã lên GitHub ở commit `0f9c24f`.
Commit `cf523b7` bỏ track nó và thêm vào `.gitignore` (dòng `.env.bak-*` cũ chỉ khớp
`.env.bak-develop`, không khớp `.env.bak`).

File vẫn còn trên máy mỗi người — chỉ thôi track, không bị xoá.

**Việc này chỉ chặn lộ về sau.** Commit `0f9c24f` trong lịch sử vẫn chứa file, nên
`LANGCHAIN_API_KEY` — key duy nhất còn trùng với `.env` đang dùng — **cần được rotate
trên LangSmith**. Repo đang private nên phạm vi lộ giới hạn trong org, nhưng vẫn phải đổi.

### 3. Dữ liệu demo: lớp `SE1801` có id mới

Trong lúc kiểm tra đường xoá lớp, lớp demo `SE1801` bị xoá rồi dựng lại.
Id mới là `sec_adm_e3ed68a01fe2`. Nếu script/bookmark nào hard-code id cũ thì phải sửa.

---

## Trước push — vấn đề đang tồn tại trên GitHub

Đây là những gì bản cũ trên `origin` đang bị, để hiểu vì sao đợt này cần thiết:

| # | Vấn đề | Hậu quả thực tế |
|---|---|---|
| 1 | Hội thoại không mang `section_id` | Bộ lọc theo lớp của giảng viên không hoạt động — không biết câu hỏi thuộc lớp nào |
| 2 | Companion chat chặn câu hỏi nhưng **không ghi lại gì** | Giảng viên không hề biết sinh viên bị chặn cái gì |
| 3 | `POST /qa` chặn câu hỏi cũng **không ghi lại gì** | Cùng lỗ hổng, ở đường thứ hai |
| 4 | 3 hành động nhạy cảm không vào Audit log | Giảng viên mở chặn guardrail, can thiệp lẻ, sinh viên tự xoá dữ liệu — đều mất dấu |
| 5 | Admin **không có** màn quản trị lớp học | Không tạo lớp, không gán giảng viên, không quản lý danh sách sinh viên |
| 6 | `first_instructor_id()` gán lớp cho **một giảng viên bất kỳ** | Wizard học kỳ tự chọn giảng viên ngẫu nhiên thay vì để Admin quyết |
| 7 | Admin không reset được mật khẩu thành viên | Sinh viên/giảng viên mất mật khẩu là tắc |
| 8 | Cổng truy cập quiz thiếu lọc `ENROLLED` | Sinh viên đã bỏ lớp vẫn vào được quiz |
| 9 | Mock LMS phải chạy tay | Không nằm trong `docker compose`, mỗi người dựng một kiểu |

---

## Sau push — đã làm gì

### A. Nối lại mạch dữ liệu bị đứt (Task 1–5)

**Hội thoại gắn đúng lớp** — `d012c40`, `e5ad7f6`

`ConversationRepository.section_id_for()` tra ra lớp mà sinh viên đang học môn đó.
Ba chi tiết quan trọng: lọc `Enrollment.status == ENROLLED` (bỏ lớp đã drop),
có `ORDER BY` (sinh viên **học lại** một môn có 2+ dòng ENROLLED — không sắp xếp
thì có thể gắn vào lớp kỳ trước, tức gửi câu hỏi tới giảng viên cũ), và
`upper()` cả hai vế vì catalog thật có mã môn đuôi thường (`ENW493c`, `SWE202c`).

**Ghi lại mọi câu hỏi bị guardrail chặn** — `28ea303`, `215a8c5`, `6428205`

Cả 2 đường (`companion_service.py` và `qa_service.py`) cùng gọi một hàm
`guardrail_event_recorder.record_block()` — không nhân bản logic.

Commit `6428205` vá một lỗ bảo mật mà review tổng phát hiện: `guardrail_events.message_id`
cascade từ `messages`, vốn cascade từ `conversations` — **sinh viên xoá thread là xoá
được bằng chứng của chính mình**. Nay `GuardrailEvent` mang `student_id` + `section_id`
của riêng nó, `message_id` nullable + `SET NULL`, nên bản ghi sống độc lập với thread.

**Bổ sung Audit cho 3 hành động đang mất dấu** — `e306184`

Thêm `GUARDRAIL_REVIEW_DECIDED`, `SUBMIT_INTERVENTION`, `SELF_SERVICE_DATA_DELETE`,
và đưa cả 3 vào `CRITICAL_CHANGE_EVENTS` để hiện trên Admin Overview.

### B. Admin cấp phát lớp học (Task 6–9)

**Backend mới** — `src/api/admin_sections.py` + `src/services/core/admin_section_service.py`

9 endpoint mới:

| Method | Đường dẫn | Việc |
|---|---|---|
| GET | `/admin/sections` | Danh sách lớp (kèm sĩ số, tên giảng viên) |
| GET | `/admin/sections/courses` | Catalog môn cho dropdown form tạo lớp |
| POST | `/admin/sections` | Tạo lớp (giảng viên để trống được) |
| PATCH | `/admin/sections/{id}` | Sửa mã lớp / học kỳ / gán giảng viên |
| DELETE | `/admin/sections/{id}` | Xoá lớp — **409** nếu còn sinh viên đang học |
| GET | `/admin/sections/{id}/roster` | Danh sách sinh viên trong lớp |
| POST | `/admin/sections/{id}/roster` | Thêm sinh viên |
| DELETE | `/admin/sections/{id}/roster/{student_id}` | Bỏ sinh viên (xoá mềm → `DROPPED`, giữ điểm) |
| POST | `/admin/users/{id}/reset-password` | Phát link đặt lại mật khẩu |

Về reset mật khẩu: Admin **không** đặt mật khẩu thay người dùng. Nó dùng lại đúng
`PasswordResetService` của luồng "Quên mật khẩu", chỉ phát token — người dùng tự chọn
mật khẩu mới. Không tồn tại 2 cơ chế token song song.

**Bỏ `first_instructor_id()`** — `24eb678`, `7aedc71`

Wizard học kỳ thôi tự chọn giảng viên bất kỳ. Lớp chưa có giảng viên giờ thành
**việc trong Work Queue** của Admin (`UNASSIGNED_SECTION`), bấm vào là nhảy thẳng
sang màn Lớp học.

**Màn hình "Lớp học"** — `frontend/src/components/admin/AdminSections.jsx` (638 dòng)

Đường dẫn `/admin/governance/sections`. Bảng Môn · Mã lớp · Học kỳ · Giảng viên ·
Sĩ số · Hành động. Lớp chưa gán giảng viên hiện badge cảnh báo. Có modal tạo lớp,
panel quản lý danh sách sinh viên, và xác nhận trước khi xoá. Toàn bộ chuỗi đi qua
`t()` — **VI/EN đủ cặp**, không hardcode.

### C. Sửa lỗi phát hiện khi kiểm tra thật

**Cổng quiz thiếu lọc `ENROLLED`** — `8e61490`
Sinh viên đã bỏ lớp vẫn vào được quiz. Đã thêm bộ lọc.

**Xoá lớp trả 500** — `bfd2ff0`, `7022167`

Lỗi đáng chú ý nhất, phát hiện khi bấm thử trên trình duyệt chứ không test nào bắt được.

`enrollments.section_id`, `modules.section_id`, `lessons.module_id` đều `NOT NULL`
kèm `ondelete="CASCADE"` ở tầng DB — nhưng relationship phía ORM **không** khai báo
delete cascade. Mặc định SQLAlchemy sẽ *set NULL* cho khoá ngoại của con khi xoá cha,
tức làm ngược lại chính schema. Kết quả `UPDATE ... SET section_id=NULL` → vi phạm
NOT NULL → 500. Và vì 500 lọt ra ngoài CORS middleware, frontend chỉ thấy
"không kết nối được tới máy chủ" — che mất nguyên nhân thật.

Đường đi tới lỗi: `remove_from_roster` xoá mềm (giữ lại dòng với `status=DROPPED`)
nhưng hàng rào 409 của `delete_section` chỉ đếm `ENROLLED` → lọt qua rồi sập.

Test 409 sẵn có vẫn xanh vì lớp trong test đó chưa từng có dòng `enrollments` nào.
Đã thêm cascade cho cả 3 tầng + 3 test cho các đường xoá.

Lưu ý phạm vi: xoá lớp mang theo cấu trúc tuần/bài của **chính lớp đó**.
Học liệu cấp môn **không bị ảnh hưởng** — `documents.course_id` trỏ vào `courses`,
không trỏ vào section.

### D. Hạ tầng

**Mock LMS vào Docker Compose** — `ea1aadd`
Thêm `mock-lms/Dockerfile`, entrypoint, và `ensure_oauth_client.py`. Chạy bằng
`docker compose` như mọi service khác, không dựng tay nữa.

---

## Bản đồ file thay đổi

### Backend (`src/`) — 18 file, +949 / −75

| File | Dòng | Việc |
|---|---|---|
| `api/admin_sections.py` | +238 | **mới** — 8 route quản trị lớp |
| `services/core/admin_section_service.py` | +226 | **mới** — nghiệp vụ lớp/roster |
| `services/core/guardrail_event_recorder.py` | +58 | **mới** — dùng chung cho 2 đường chặn |
| `api/instructor.py` | +63/−21 | audit mở chặn guardrail + can thiệp lẻ |
| `services/core/admin_overview_service.py` | +65 | Work Queue `UNASSIGNED_SECTION` |
| `db/models.py` | +55 | `instructor_id` nullable, `GuardrailEvent` scoping, 3 cascade |
| `services/ai/qa_service.py` | +52 | ghi guardrail event |
| `repositories/ownership_repository.py` | +46 | phân quyền lớp |
| `schemas/admin_schemas.py` | +41 | `SectionOut`, `SectionCreateRequest`, ... |
| `api/admin.py` | +48 | route reset mật khẩu |
| `repositories/conversation_repository.py` | +31 | `section_id_for` |
| `repositories/semester_repository.py` | −25 | bỏ `first_instructor_id` |
| `api/student.py` | +18 | audit tự xoá dữ liệu |
| `services/ai/companion_service.py` | +13 | ghi guardrail event |
| `repositories/quiz_repository.py` | +9 | lọc `ENROLLED` |
| `services/academic/semester_service.py` | +7 | thôi gán giảng viên bừa |
| `repositories/chunk_repository.py` | +6 | chỉ `PUBLISHED` vào RAG |
| `main.py` | +2 | đăng ký router mới |

### Frontend — 10 file, +859 / −7

| File | Dòng |
|---|---|
| `components/admin/AdminSections.jsx` | +638 (**mới**) |
| `lib/api.js` | +64 |
| `locales/vi.js` / `locales/en.js` | +50/−1 mỗi bên (đủ cặp) |
| `components/admin/AdminUsers.jsx` | +41 (nút reset mật khẩu) |
| `components/admin/adminDisplay.js` | +8/−1 |
| `AdminConsole.jsx`, `adminRoutes.js`, `adminNavigationConfig.js`, `adminWorkQueueLinks.js` | +12 tổng (nối route/nav) |

### Test — 7 file mới, 34 test function

`test_admin_sections.py` · `test_admin_section_roster.py` · `test_admin_password_reset.py`
`test_audit_coverage.py` · `test_guardrail_event_recording.py` · `test_unassigned_section_queue.py`
`test_repositories/test_conversation_section_binding.py`

---

## Cách kiểm tra sau khi pull

```bash
./.venv/Scripts/python.exe -m alembic upgrade head
./.venv/Scripts/python.exe -m pytest tests/ -q
```

Kỳ vọng: `548 passed, 7 skipped`.

Frontend:

```bash
npm --prefix frontend run build
```

Thử tay trên trình duyệt — đây là vòng đã được kiểm chứng:

1. Vào `/admin/governance/sections` → bấm **Thêm lớp**, để trống giảng viên
2. Sang `/admin/overview` → lớp đó xuất hiện trong Work Queue
3. Bấm **Open** → nhảy về màn Lớp học
4. Gán giảng viên → tải lại Overview, việc biến khỏi Work Queue
5. Mở **Danh sách sinh viên** → thêm 1 sinh viên → bấm **Xoá** lớp → phải hiện
   **409** với thông báo "lớp vẫn còn sinh viên"
6. Bỏ sinh viên khỏi lớp → **Xoá** lại → thành công (204)
7. Đổi VI ⇄ EN → không còn chuỗi sót ở cả hai chiều

---

## Còn tồn đọng

| Việc | Trạng thái |
|---|---|
| Rotate `LANGCHAIN_API_KEY` | **chưa làm** — cần người có quyền LangSmith |
| Task 10–14 của plan | chưa làm. Theo thứ tự đề nghị, việc kế tiếp là **Task 14 từ Step 3** (Step 1–2 đã xong ở `99a2ade`) |
| 26 oxlint warning | nợ cũ, không phải của đợt này (import không dùng, `exhaustive-deps`). File của đợt này sạch |
| Xoá `.env.bak` khỏi lịch sử git | chưa làm, và **là quyết định của cả team** — cần `git filter-repo` + force-push, mọi người phải clone lại |

---

*Tài liệu này viết trước khi push, dựa trên `git diff origin/haidang2425..7022167`.*
