# Bàn giao vai Admin — từ `haidang2425` tới hiện trạng `chung`

> **Viết:** 28/08/2026 · **Mốc so sánh:** `origin/haidang2425` (e4f4641) ↔ `origin/chung` (a07b451)
> **Mục đích:** đủ để một người (hoặc một AI) đứng ở `haidang2425` dựng lại hoặc mở rộng
> vai Admin, chỉ cần file này + ảnh chụp màn hình.

---

## 0. Đọc mục này trước — đừng vibe-code lại 123 commit

Đo thật bằng git:

```
chung có mà haidang2425 chưa có:  123 commit
haidang2425 có mà chung chưa có:   36 commit  (toàn của Đăng, đều ngày 27/08)
```

Hai nhánh **phân kỳ hai chiều**, không phải một bên đi trước.

Nhưng con số `+9,849 / −8,440` dòng là **ảo**. Lý do: `chung` đã đổi cấu trúc thư mục
(`src/` → `backend/src/`, `tests/` → `backend/tests/`) khi gộp `develop`, còn `haidang2425`
vẫn ở cấu trúc cũ. Git đếm mọi file là "đổi" dù nội dung y hệt.

**Nội dung thật sự khác nhau ít hơn nhiều.** Về vai Admin cụ thể:

| | `haidang2425` | `chung` |
|---|---|---|
| Component admin (frontend) | **31** | 32 |
| File API admin (backend) | thiếu 2 | đủ |

Tức là **`haidang2425` đã có gần trọn vai Admin rồi**. Thiếu đúng:

- `AdminAiUsage.jsx` + `admin_ai_usage.py` — màn Chi phí AI *(việc của Chung, 27/08)*
- `admin_crisis_escalations.py` — hàng đợi khủng hoảng *(việc của Hải Anh, qua develop)*

### → Kết luận: cách đúng là `git merge`, không phải viết lại

Viết lại 123 commit bằng AI vừa tốn thời gian vừa chắc chắn lệch. Đường đúng ở **mục 4**.

Tài liệu này phục vụ hai việc:
1. **Bản đồ** để hiểu vai Admin gồm những gì (mục 1–2)
2. **Đặc tả phần mới** để dựng lại nếu merge không khả thi (mục 3)

---

## 1. Bản đồ bề mặt Admin

### Điều hướng — 12 mục, 2 nhóm

Nguyên tắc thiết kế: **quan sát trước, quản trị sau** (`adminNavigationConfig.js`).

```
THEO DÕI
  Tổng quan          /admin/overview              tín hiệu vận hành toàn trường
  Người dùng         /admin/people                tra cứu người dùng
  Phân tích          /admin/analytics             số đếm học liệu + rủi ro
  Chi phí AI         /admin/ai-usage              ← MỚI (mục 3)

QUẢN TRỊ
  Chương trình học   /admin/governance/curriculum   môn học + tài liệu + ingest
  Lớp học            /admin/governance/sections     CRUD lớp, gán GV, danh sách SV
  Học kỳ & lịch thi  /admin/governance/academic     kỳ học, lịch thi
  Chính sách AI      /admin/governance/ai-policy    bật/tắt nhóm luật guardrail
  EduSync            /admin/governance/edusync      đồng bộ với LMS ngoài
  Tài khoản          /admin/governance/access       mời, khoá, đặt lại mật khẩu
  Cấu hình           /admin/governance/settings     cấu hình tổ chức
  Nhật ký hệ thống   /admin/governance/logs         audit log
```

> **Đã gỡ có chủ đích:** mục "Yêu cầu dữ liệu" (`/admin/data-requests`). 6 route backend và
> bảng `DataRequest` **vẫn còn trong code**, chỉ không có đường vào từ UI. Lý do: không có
> endpoint nào cho SV/GV tạo yêu cầu nên bảng luôn rỗng, và nhánh `DELETE` xoá cả
> `Enrollment` + `Submission` — rộng hơn spec FR-1.3 cho phép. Xem **ADR-021**.

### API — 87 route dưới `/api/v1/admin`

| Nhóm | Số route | Nội dung |
|---|---|---|
| `admin` | 50 | curriculum, tài liệu, KPI, người dùng, mời, guardrail rules, cấu hình |
| `admin-student-360` | 13 | hồ sơ 360° của một sinh viên |
| `admin-sections` | 8 | CRUD lớp, gán GV, thêm/bớt SV |
| `admin-data-requests` | 6 | *(còn code, đã gỡ khỏi UI)* |
| `admin-crisis-escalations` | 3 | hàng đợi khủng hoảng |
| `admin-overview` | 2 | tổng quan + work queue |
| `class-activities` | 2 | |
| `admin-ai-usage` | 1 | ← **mới** |
| `admin-instructor-360` | 1 | chỉ mức tổng hợp — **cố ý không mở rộng**, xem Known Limitations |
| `admin-people` | 1 | |

---

## 2. Bốn kiểu kết nối Admin ↔ role khác

Đây là khung tư duy để hiểu vì sao vai Admin được xây như vậy (chi tiết:
`docs/ADMIN_BAN_DO_KET_NOI.md`).

| Kiểu | Nghĩa | Trạng thái |
|---|---|---|
| **ĐỌC** | Admin xem lại thứ role khác tạo ra | Student 360: 13 route · Instructor 360: 1 route *(đóng phạm vi)* |
| **NHẬN VIỆC** | Hoạt động role khác tự đẩy việc vào hàng đợi Admin | Work Queue — nguồn `UNASSIGNED_SECTION`, guardrail, ingest lỗi |
| **CẤP PHÁT** | Admin tạo cái khung role khác hoạt động bên trong | Lớp học, gán GV, enrollment, mời, đặt lại mật khẩu |
| **ĐẶT** | Admin đặt luật | Chính sách AI, ngưỡng rủi ro, cấu hình tổ chức |

Một mẹo thiết kế đáng học lại: khi sinh viên tự khai môn mà lớp chưa được Admin cấp,
hệ thống **tạo lớp không gán giảng viên** rồi đẩy một item `UNASSIGNED_SECTION` vào Work
Queue — thay vì gán bừa giảng viên đầu tiên tìm thấy (hành vi cũ, đã bỏ). Tận dụng hàng
đợi có sẵn thay vì xây màn hình mới.

---

## 3. Phần thật sự mới: màn "Chi phí AI"

**Đặc tả đầy đủ nằm ở [`docs/FEATURE_ADMIN_AI_USAGE.md`](FEATURE_ADMIN_AI_USAGE.md)** —
11 mục, có sơ đồ luồng, hợp đồng API kèm response thật, toàn bộ file frontend phải đụng,
toán vẽ biểu đồ SVG, 16 khoá i18n, và 12 test kèm ý nghĩa từng cái.

Tóm tắt ở đây để định hướng:

### Nó giải quyết gì

BTC yêu cầu *"theo dõi tối thiểu độ trễ, lỗi và chi phí"*. Độ trễ và lỗi đã có từ trước.
Dữ liệu chi phí cũng đã được ghi (bảng `ai_usage`, từ 26/08) — **thiếu đường đọc**.

### Kiến trúc 4 tầng

```
11 service gọi LLM
   → ai_engine (2 chỗ gọi chat.completions.create)
   → record_llm_call()            ghi 1 hàng ai_usage
   → build_ai_usage_report()      gom theo (feature, model) rồi (ngày, model)
   → GET /admin/ai-usage?days=    7 / 30 / 90
   → AdminAiUsage.jsx             hàng tổng + biểu đồ cột + bảng theo tính năng
```

### Sáu quy tắc bất biến — sai một cái là hỏng cả tính năng

1. **Model không có trong bảng giá thì KHÔNG đoán giá** → trả `None`, UI hiện "chưa có đơn giá"
2. **`None` khác `0.0`** — `0.0` là "đã tính, ra 0"; `None` là "không đủ dữ kiện"
3. **Tỷ lệ trên mẫu số 0 trả `None`**, không phải `0.0` — không có mẫu số thì không có tỷ lệ
4. **Gom theo `(feature, model)`**, không chỉ `feature` — đơn giá phụ thuộc model
5. **Chuỗi ngày giữ cả ngày rỗng** — bỏ đi thì khoảng lặng 3 ngày trông như 3 ngày bận
6. **Dòng `organization_id = NULL`** không gộp vào bảng của tổ chức (rò dữ liệu chéo) nhưng
   phải đếm riêng (`unattributed_calls`), nếu không tổng thiếu mà không ai biết

### Ba lỗi đã sửa cùng đợt — quan trọng cho `haidang2425`

**a) `OPENAI_BASE_URL` để trống làm hỏng mọi lời gọi.**
`config.py` gọi `load_dotenv()` nên mọi dòng `.env` thành biến môi trường, kể cả dòng trống.
SDK OpenAI nhận `base_url=None` sẽ đọc `os.environ`, thấy `""`, dùng luôn làm địa chỉ →
`APIConnectionError` trông y như mất mạng. **Đây chính là cấu hình `.env.example` hướng dẫn
cho người dùng OpenAI thật** — nên đường đi mặc định trong tài liệu là đường hỏng.
Sửa ở `ai_engine/client.py`: giải địa chỉ ở một chỗ, không đưa `None` cho SDK tự suy.

**b) `GuardrailEvent` không còn ai ghi.**
`develop` xoá tính năng chat cũ, kéo theo `record_block()`. Vế đọc trong `instructor.py`
không đổi → hàng đợi duyệt của giảng viên rỗng vĩnh viễn, **không lỗi, không test đỏ**.
Sửa ở `cursus_chat.py`: ghi lại `GuardrailEvent` trong nhánh `if decision.blocked:`.

**c) Chuỗi alembic rẽ hai nhánh.**
Nối lại bằng cách trỏ `20260911_invite_section.down_revision` → `20260912_crisis_escalations`.
Quy trình sửa DB đã lỡ chạy chuỗi cũ ở **mục 4**.

---

## 4. Đường merge — cách đúng để `haidang2425` bắt kịp

### Bước 1 — merge

```bash
git checkout haidang2425
git merge origin/chung
```

**Xung đột dự kiến ~26, chia 3 loại, hầu như không phải chọn bên:**

| Loại | Xử lý |
|---|---|
| Vị trí file *(`src/` → `backend/src/`)* | Lấy cấu trúc `backend/`, git đã tự di chuyển phần lớn |
| Nội dung | Lấy bản `chung` — thay đổi phía kia thường chỉ là nhãn `feature=` cho `get_llm()`, hàm đã bị gỡ |
| modify/delete | Theo `chung`: xoá. Đó là các service của chat cũ |

**Ngoại lệ duy nhất — `main.py`:** hai bên cùng thêm import router ở cùng chỗ. **Giữ cả hai.**

### Bước 2 — dependency

```bash
pip install -r backend/requirements.txt          # thêm apscheduler, python-docx
npm install --prefix frontend                    # thêm react-markdown, remark-gfm
```

Thiếu 2 gói frontend là **trang trắng**, không báo lỗi rõ ràng.

### Bước 3 — DB đã chạy chuỗi alembic cũ

Triệu chứng: `alembic current` báo đã ở head, nhưng app lỗi `relation "chat_conversations"
does not exist`. Vì DB chạy theo chuỗi cũ, chưa từng chạy 3 migration của develop.

```bash
alembic stamp 20260910_announcement_org        # lùi về điểm rẽ nhánh
alembic upgrade 20260912_crisis_escalations    # chạy 3 migration của develop
alembic stamp head                             # đánh dấu 2 migration của chung đã chạy
```

⚠️ **Cảnh báo:** `20260910_remove_chatbot_feature` **xoá 3 bảng** — `conversations`,
`messages`, `student_memory_entries`. Sao lưu DB trước. Sau khi chạy, **code cũ chưa merge
sẽ lỗi 500** vì vẫn đi tìm 3 bảng đó.

### Bước 4 — `.env`

Hệ thống cần **hai** khoá, không phải một:

```
GOOGLE_API_KEY=...      # embedding (models/gemini-embedding-001) — bỏ trống thì
                        # retrieval âm thầm tụt về chỉ chấm điểm từ khoá
OPENAI_API_KEY=...      # sinh nội dung qua ai_engine
```

Và **tên model phải khớp đường gọi**:

```
Dùng OpenAI thật  →  OPENAI_BASE_URL trống
                     OPENAI_STRONG_MODEL=gpt-5.6-terra   (hoặc gpt-5.6-luna cho rẻ)
                     OPENAI_LIGHT_MODEL=gpt-5-nano

Dùng gateway      →  OPENAI_BASE_URL=<url>
                     OPENAI_STRONG_MODEL=pro/gpt-5.6-terra
                     OPENAI_LIGHT_MODEL=pro/gpt-5.6-luna
```

Sai cặp → `model_not_found` → **rơi lặng lẽ về nhánh dự phòng tất định, không test nào đỏ**.

### Bước 5 — kiểm

```bash
cd backend && pytest tests/ -q       # kỳ vọng ~620 passed
```

⚠️ **620 xanh là bằng chứng yếu nếu chưa có `OPENAI_API_KEY`** — không khoá thì mọi đường
LLM chạy nhánh dự phòng tất định, suite không chạm tới đường AI lần nào.

---

## 5. Nếu buộc phải dựng lại thay vì merge

Chỉ nên làm với **một màn hình cụ thể**, không phải cả vai Admin. Với mỗi màn hình, prompt cần:

1. **Ảnh chụp màn hình** ở desktop 1440×900, cả sáng lẫn tối
2. **Hợp đồng API** — có sẵn ở `/docs` (Swagger) của backend đang chạy
3. **Mục tương ứng trong tài liệu này**, hoặc `FEATURE_ADMIN_AI_USAGE.md` nếu là màn Chi phí AI

### Ảnh nên chụp

| Màn | Vì sao cần |
|---|---|
| Tổng quan | bố cục hàng tín hiệu + work queue |
| Chi phí AI | hàng 4 ô số + biểu đồ cột + bảng theo tính năng |
| Lớp học | bảng + hành động trên hàng |
| Chương trình học | bảng môn + trạng thái ingest |
| Student 360 | bố cục hồ sơ nhiều khối |
| Một màn ở **chế độ tối** | chứng minh dùng token màu, không hardcode |
| Một màn ở **375px** | chứng minh bảng tự cuộn, trang không trượt ngang |

### Ràng buộc bắt buộc khi dựng lại

- **Mọi số liệu phải kèm `method_note`** giải thích cách đo — ràng buộc gốc ở
  `roles/CHUNG_admin.md` mục 2. Không bao giờ hiện số trần trụi.
- **Không tự bịa số liệu.** Backend chưa tính được thì hiện "chưa đo", không hiện số đẹp.
- **Chỉ dùng token màu** của design system (`text-fg`, `border-line`, `bg-[var(--bg-elevated)]`,
  `text-accent`…). Hardcode màu là hỏng dark mode — mà **dark mode + responsive chính là
  thứ ô UX/UI ≥7 chấm**.
- **Bảng phải bọc trong `overflow-x-auto`** — bảng tự cuộn, trang không bao giờ trượt ngang.
- **Trạng thái rỗng phải nói được gì đó**, không để bảng trắng.

---

## 6. Những gì cố ý KHÔNG làm

Ghi ở **ADR-021** và mục **Known Limitations** trong `README.md`. Đừng nhặt lên làm tiếp
mà không đọc lý do:

| Việc | Lý do |
|---|---|
| Instructor 360 mở rộng (`ClassActivity`, `Quiz`, `PracticeSet`) | Công lớn, không phục vụ F6/F7 |
| Student 360 thêm bộ nhớ AI / quiz / practice | Đã có 13 route; phần còn lại chỉ có nghĩa nếu mở DSAR |
| Đường vào DSAR cho người dùng | Nhánh `DELETE` xoá cả hồ sơ học tập — rộng hơn spec FR-1.3 |
| Admin đọc `InstructorStudentNote` | Ghi chú riêng tư trong quan hệ dạy–học |
| RLS đa tổ chức | Lọc hiện ở tầng ứng dụng; `tenant_scope.py` viết sẵn nhưng chưa nối route |

---

## 7. Bẫy đã biết — đọc trước khi sửa bất cứ thứ gì

| Bẫy | Hậu quả nếu vấp |
|---|---|
| `ai_usage.created_at` là **naive UTC** | So sánh với `datetime.now(UTC)` có tzinfo → lọc sai kỳ, **không báo lỗi** |
| `func.date()` trả **chuỗi** trên SQLite, **date** trên Postgres | Vỡ khi đổi backend DB |
| `load_dotenv()` xuất cả dòng trống ra `os.environ` | SDK bên thứ ba hiểu nhầm là "đã cấu hình" |
| `_needs_llm()` chỉ đẩy câu **cần tổng hợp** sang LLM | Hỏi câu tra cứu đơn giản sẽ không sinh dòng `ai_usage` nào — **đúng thiết kế**, không phải lỗi |
| Guardrail chặn thì **không gọi LLM** | Câu bị chặn không xuất hiện trong thống kê chi phí |
| Nút KEEP/UNBLOCK ở màn duyệt guardrail | Ghi trạng thái nhưng **không gửi gì cho sinh viên** — đừng demo như vòng lặp khép kín |
| LangSmith `403` mỗi lần gọi | `.env` bật `LANGCHAIN_TRACING_V2=true` với khoá không hợp lệ → thổi phồng số độ trễ |

---

## 8. Tài liệu liên quan

| File | Nội dung |
|---|---|
| [`FEATURE_ADMIN_AI_USAGE.md`](FEATURE_ADMIN_AI_USAGE.md) | Đặc tả đầy đủ màn Chi phí AI — dựng lại được chỉ từ file đó + 1 ảnh |
| [`ADMIN_BAN_DO_KET_NOI.md`](ADMIN_BAN_DO_KET_NOI.md) | Bản đồ 4 kiểu kết nối, 17 đầu việc và trạng thái từng cái |
| [`CHECKLIST_DONG_BO_ROLE.md`](CHECKLIST_DONG_BO_ROLE.md) | Trạng thái đồng bộ 3 role + việc phát sinh sau merge |
| [`decisions/ADR.md`](decisions/ADR.md) | 21 quyết định kiến trúc, mỗi cái 3 dòng Quyết định / Vì sao / Đánh đổi |
| `README.md` mục Known Limitations | 6 giới hạn có chủ đích |
