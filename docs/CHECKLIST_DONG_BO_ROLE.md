# Checklist đồng bộ 3 role — trạng thái 26/08/2026

> Mọi ô đã kiểm bằng code tại `HEAD = 6428205`, không dựa vào trí nhớ.
> Plan chi tiết kèm code: `docs/superpowers/plans/2026-08-26-dong-bo-3-role.md`
> Ledger thực thi: `.superpowers/sdd/2026-08-26-dong-bo-3-role/progress.md`

**Tiến độ: 5/14 task xong** (4 task + 1 nửa task, cộng 1 đợt sửa ngoài kế hoạch)

---

## Phase 1 — Nối lại mạch đứt · 4/5 xong

- [x] **Task 1 — Gắn `section_id` cho hội thoại** · `d012c40` `e5ad7f6`
  Hội thoại nay gắn vào lớp sinh viên đang học (ENROLLED). Điều kiện bắt buộc của Task 2/3.
  *1 vòng sửa: thiếu bộ lọc `Enrollment.status == ENROLLED`.*
- [x] **Task 2 — Ghi `GuardrailEvent` khi companion chat chặn** · `28ea303`
- [x] **Task 3 — Ghi `GuardrailEvent` khi `/qa` chặn** · `215a8c5`
  Tạo lười hội thoại "Hỏi nhanh" chỉ khi bị chặn; câu hỏi được phép vẫn không lưu gì.
- [x] **Task 4 — Chỉ tài liệu `PUBLISHED` mới vào RAG** · `99a2ade` *(chungnguyenvp làm)*
- [ ] **Task 5 — Ghi nhật ký 3 hành động đang mất dấu**
  Kiểm 26/08: `instructor.py` **2** lần `log_event`, `student.py` **0** lần.
  - [ ] Giảng viên mở chặn guardrail *(hiện trả về field `auditMetadata` nhưng không ghi gì)*
  - [ ] Giảng viên can thiệp lẻ *(chỉ bản hàng loạt được ghi)*
  - [ ] Sinh viên tự xoá dữ liệu cá nhân *(xoá thật, không để lại vết)*

- [x] **Đợt sửa sau review tổng** · `6428205` — ngoài kế hoạch, phát sinh từ review
  - [x] Bản ghi guardrail sống sót khi sinh viên xoá thread *(migration `20260908_guardrail_event_scoping`)*
  - [x] Hàng đợi giảng viên sắp theo `created_at` thay vì UUID
  - [x] Thread "Hỏi nhanh" không còn bị xoá đầu tiên
  - [x] `section_id_for` sắp theo `enrolled_at` mới nhất
  - [x] Bộ test mới không còn làm nhiễm DB dùng chung

---

## Phase 2 — Admin cấp phát lớp học · 0/4 · **gốc của "3 role không đồng bộ"**

- [ ] **Task 6 — Backend quản trị lớp: CRUD `CourseSection` + gán giảng viên**
  Kiểm 26/08: `src/api/admin_sections.py` **chưa tồn tại**.
  > ⚠️ **Chặn:** `CourseSection.instructor_id` là **NOT NULL** (`models.py:316`).
  > Cần thêm migration đổi nó thành nullable — plan chưa nhắc. Làm trước khi bắt đầu Task 6.
- [ ] **Task 7 — Backend danh sách sinh viên trong lớp** *(thêm/bớt enrollment)*
- [ ] **Task 8 — Bỏ `first_instructor_id()`**
  Kiểm 26/08: vẫn ở `semester_repository.py:167`.
  Lớp chưa phân công sẽ **không gán ai** và tự hiện trong Work Queue của Admin.
  > Phụ thuộc migration của Task 6.
- [ ] **Task 9 — Màn hình "Lớp học" + đặt lại mật khẩu người dùng**

---

## Phase 3 — Admin nhìn thấy nhiều hơn · 0/3

- [ ] **Task 10 — Hồ sơ giảng viên 360° đầy đủ**
  Kiểm 26/08: `admin_instructor360.py` vẫn **1 route** duy nhất.
  Thiếu: nhật ký buổi học · quiz đã tạo · duyệt luyện tập · quyết định guardrail
- [ ] **Task 11 — Hồ sơ sinh viên: thêm bộ nhớ AI, quiz, luyện tập**
  Kiểm 26/08: `StudentMemoryEntry` **0** lần xuất hiện trong `admin_student360.py`.
- [ ] **Task 12 — Đường vào cho yêu cầu dữ liệu (DSAR)**
  Kiểm 26/08: **0** nơi tạo `DataRequest`. Tab xử lý có đủ 6 thao tác nhưng vĩnh viễn rỗng.

---

## Phase 4 — Đo chi phí/độ trễ AI · 0/1

- [ ] **Task 13 — Bảng `ai_usage` + ghi token/độ trễ mỗi lần gọi LLM**
  Kiểm 26/08: **0** file nhắc `AIUsage`.
  Vế duy nhất của PLO 5 đang trống. Thư viện đã trả sẵn số token — hiện bị vứt tại chỗ nhận.
  > Không tái dùng `RAGTrace`/`LLMUsageEvent` — ADR-017 đã đóng 2 bảng đó có lý do.

---

## Phase 5 — Dọn dẹp · 1/2

- [x] **Task 14 Step 1-2 — Sửa 4 test đỏ** · `99a2ade` *(chungnguyenvp làm)*
- [ ] **Task 14 Step 3-6 — ba việc nhỏ nhìn thấy được khi demo**
  - [ ] Dịch menu giảng viên — kiểm 26/08: còn **3** chuỗi tiếng Việt cứng trong `App.jsx`
  - [ ] Route cho Admin ghi `AdminAnnouncement` *(panel bên giảng viên đang rỗng vĩnh viễn)*
  - [ ] Lọc `failed_jobs` theo tổ chức *(org A báo đỏ vì job hỏng của org B)*

---

## Kế hoạch tiếp theo — thứ tự đề nghị

| Bước | Việc | Cỡ | Vì sao xếp ở đây |
|---|---|---|---|
| **1** | **Task 5** | nhỏ | Đóng nốt Phase 1. Nhỏ, độc lập, không phụ thuộc gì |
| **2** | **Migration `instructor_id` nullable** | rất nhỏ | Chặn Task 6 và 8 — làm trước, không thì cả hai đứng |
| **3** | **Task 6 + 7** | lớn | Backend quản trị lớp. Làm liền 2 task vì cùng một file service |
| **4** | **Task 8** | nhỏ | Bỏ gán giảng viên bừa. Cần Task 6 xong trước |
| **5** | **Task 9** | vừa | Màn hình Lớp học. Phase 2 xong ở đây → "3 role đồng bộ" thành đúng |
| **6** | **Task 14 Step 3-6** | nhỏ | Ba việc nhỏ, đều nhìn thấy khi demo. Kéo lên trước Phase 3 |
| **7** | **Task 13** | vừa | Chi phí AI. Ưu tiên có dữ liệu trước, giao diện sau |
| **8** | **Task 10 + 11 + 12** | vừa | Hoàn thiện quan sát. Thiếu vẫn bảo vệ được |

**Nếu thời gian hẹp:** làm bước 1 → 5 rồi dừng. Đó là phần trả lời thẳng câu hỏi "3 role đã đồng bộ chưa".

---

## Nợ kỹ thuật đã ghi nhận, cố ý chưa làm

| Việc | Vì sao hoãn |
|---|---|
| `semester_service` cho phép nhiều dòng ENROLLED cùng môn qua các kỳ | Cần thiết kế lại dedup. Task 8 chạm vùng này — cân nhắc gộp vào đó |
| `EnrollmentStatus.DROPPED` không nơi nào gán | Cần chốt với sản phẩm: có luồng huỷ môn không? |
| `companion_service` truyền câu hỏi **đã chuẩn hoá** vào `record_block`, `qa_service` truyền **nguyên văn** | Không ảnh hưởng người dùng (reader đọc `message.content`). Nên thống nhất về nguyên văn |
| `_visible_guardrail_events` `.limit(200)` **trước** khi lọc theo lớp | Đã sửa phần ngẫu nhiên; hình dạng cap-rồi-lọc là thiết kế cũ |
| `build_work_queue` truy vấn User theo từng dòng (N+1, có chặn trên) | Hiệu năng, không phải đúng/sai |
| Cách ly dữ liệu ở tầng DB (RLS) | Cần thao tác Supabase Dashboard, có kế hoạch riêng |
| Báo cho sinh viên biết đã được can thiệp | **Quyết định sản phẩm**, không phải kỹ thuật — cần chốt trước khi code |
| Cho Admin xem ghi chú riêng của giảng viên | Quyết định về quyền riêng tư |

---

## Số liệu

| | |
|---|---|
| HEAD | `6428205` |
| Working tree | sạch |
| Test | **526 passed · 7 skipped · 0 failed** (baseline đầu ngày: 514) |
| Commit của đợt này | `9e2c72c` `d012c40` `e5ad7f6` `28ea303` `215a8c5` `6428205` |
