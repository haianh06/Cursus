# Docs riêng — Nguyễn Đức Chung · Role Admin (F6 Curriculum · F7 KPI)

**Cập nhật:** 11/08/2026 · **Đọc cùng:** [`docs/frontend/00_AI_CONTEXT_PACK.md`](../../../frontend/00_AI_CONTEXT_PACK.md) (design system — dán cho AI), [`../09-Cursus-Team-Assignment.md`](../09-Cursus-Team-Assignment.md) (bức tranh toàn team), [`../00-Cursus-Playbook.md`](../00-Cursus-Playbook.md) (spec gốc F6/F7).

**Cách dùng file này:** đọc mục 1-2 để hiểu vì sao role bạn khác hẳn 2 role kia (bạn phải TỰ XÂY backend, không chỉ nối), mục 3 để có tham khảo thiết kế thật, mục 4-5 để biết chính xác UI/tính năng cần build, mục 6 để biết làm gì hôm nay, mục 8 để copy prompt dán thẳng cho Gemini/Antigravity.

---

## 0. Bạn sở hữu gì

| Tính năng | Mã | Màn hình | File hiện tại |
|---|---|---|---|
| Bảng quản lý curriculum đã nạp vào hệ thống AI | F6 | Admin Console | `frontend/src/components/admin/AdminConsole.jsx` |
| KPI tổng — so sánh tỷ lệ nộp đúng hạn có/không dùng Cursus | F7 | Admin Console | cùng file |
| Xem audit log hệ thống | — (BTC không đánh số F riêng, nhưng có sẵn backend) | Admin Console | cùng file |

**Không phải việc của bạn:** dashboard sinh viên/giảng viên, màn login/register.

---

## 1. ⚠️ Đọc kỹ mục này trước — role của bạn khác 2 role kia

Hải Anh và Bình chỉ cần **nối** UI có sẵn vào API đã tồn tại trên `origin/chung`. Bạn thì khác: **không có `src/api/admin.py` ở bất kỳ branch nào của repo** — bạn là người duy nhất trong 4 người phải **tự thiết kế và viết endpoint backend mới**, không chỉ frontend. Đây không phải việc kém quan trọng hơn — ngược lại, KPI (F7) là bằng chứng số liệu duy nhất chứng minh sản phẩm "có tác dụng" (giá trị kinh doanh, CP1), giám khảo sẽ nhìn thẳng vào đây để hỏi "số này tính từ đâu ra".

---

## 2. Ràng buộc bắt buộc

1. **KPI phải luôn kèm `method_note` giải thích cách đo** — tuyệt đối không hiện 2 con số trần trụi (`78% vs 45%`) mà không có dòng giải thích ngay cạnh. UI hiện tại đã làm đúng điều này (`AdminConsole.jsx` dòng 95-102) — **giữ nguyên, đừng xoá khi làm đẹp lại**. Lý do: nếu không có method_note, số liệu dễ bị hiểu nhầm là kết quả nghiên cứu thật trong khi thực chất là mô phỏng — vi phạm trực tiếp "Quy định chung mục 3-4" của BTC.
2. **Không tự bịa số liệu KPI** — nếu backend chưa tính được số thật, giữ đúng ghi chú "mô phỏng minh hoạ phương pháp đo" như hiện tại, không âm thầm thay bằng số "đẹp" hơn.
3. **Trạng thái ingest (`ingested`/`processing`/`not_ingested`/`failed`) phải phản ánh đúng trạng thái xử lý thật**, không phải chỉ đổi màu badge cho đẹp — nếu tài liệu chưa xử lý xong, không được hiện "ingested".
4. Rule Engine (bật/tắt guardrail rule) — **guardrail hiện chạy cứng trong code (`qa_service.py`), chưa có endpoint cấu hình được**. Không tự ý build UI hứa hẹn "bật/tắt được" nếu backend chưa hỗ trợ — xem mục 5.3 để biết scope thật cho Gate 2.

---

## 3. Sản phẩm tham khảo thật — học cái gì, đừng bắt chước cái gì

| Sản phẩm | Link | Học cái gì cho Cursus | Đừng bắt chước |
|---|---|---|---|
| **LangSmith (LangChain)** | [langchain.com/langsmith/observability](https://www.langchain.com/langsmith/observability) | Dashboard quan sát pipeline RAG: token usage, latency, cost, trace từng bước ingest→retrieval→generate. **Tham khảo trực tiếp cho khối "Vector Store Database" đã có sẵn trong `AdminConsole.jsx`** (dòng 57) — có thể mở rộng thêm cột "số lần truy vấn", "thời gian ingest gần nhất" nếu dư giờ | LangSmith là công cụ dev-facing đầy đủ (trace chi tiết từng LLM call) — Admin Console của Cursus chỉ cần mức tổng quan cho vận hành, không cần sâu tới mức debug từng request |
| **Retool** | [retool.com/use-case/admin-dashboard](https://retool.com/use-case/admin-dashboard) | Ý tưởng thiết kế bảng dữ liệu quản trị: filter, trạng thái màu, hành động nhanh (xoá/sửa) ngay trên hàng — bảng curriculum hiện tại (`AdminConsole.jsx` dòng 138-203) đã đúng tinh thần này | Retool là low-code builder — không liên quan tới cách bạn code, chỉ tham khảo layout |
| **Base.vn** | [base.vn](https://base.vn/) | SaaS quản trị doanh nghiệp Việt Nam — bảng dữ liệu tối giản, số liệu KPI nổi bật ngay đầu trang, không rối mắt | Base.vn có quá nhiều module — Admin Console của Cursus chỉ cần 3 khối (Header+KPI / Add form / Bảng curriculum), đừng thêm module thừa |
| **Haravan (Myharavan)** | Ghi chú redesign: [Ra mắt giao diện mới trang quản trị Myharavan](https://support.haravan.com/support/solutions/articles/42000107683-ra-m%E1%BA%AFt-giao-di%E1%BB%87n-m%E1%BB%9Bi-trang-qu%E1%BA%A3n-tr%E1%BB%8B-myharavan) | Bài học thiết kế cụ thể: bản redesign 2024 của họ **ưu tiên bảng màu đơn giản để làm nổi bật thông tin quan trọng, menu chỉ giữ tính năng người bán thực sự dùng** — đúng nguyên tắc "restrained" mà design system Cursus theo đuổi (`00_AI_CONTEXT_PACK.md` mục 7) | |
| **GitHub — Kiranism/next-shadcn-dashboard-starter** | [github.com/Kiranism/next-shadcn-dashboard-starter](https://github.com/Kiranism/next-shadcn-dashboard-starter) | Admin dashboard mã nguồn mở có sẵn module quản lý danh sách (bảng + form thêm/sửa) — tham khảo cấu trúc component cho form "Thêm môn học" (đã có, dòng 106-136 `AdminConsole.jsx`), không copy nguyên UI kit (khác stack Next.js/TS) | |

---

## 4. UI/UX cụ thể — Admin Console (`AdminConsole.jsx`)

Đã có UI thật (206 dòng) — **không cần thiết kế lại**, chỉ nối dữ liệu thật + xây thêm phần Audit Log (đã có sẵn API, chỉ thiếu UI) + quyết định scope Rule Engine.

```
┌─────────────────────────────────────────────────────────────────┐
│ HEADER — tiêu đề + nút "Thêm môn học"                             │
├─────────────────────────────────────────────────────────────────┤
│ KPI SECTION — 2 card: "Với Cursus" (xanh, %) / "Baseline" (xám)   │
│ + dòng method_note bắt buộc luôn hiện                            │
├─────────────────────────────────────────────────────────────────┤
│ [Form thêm môn — chỉ hiện khi bấm nút, ẩn mặc định]               │
├─────────────────────────────────────────────────────────────────┤
│ BẢNG CURRICULUM — cột: Mã môn · Tên · Kỳ · Số chunk · Trạng thái  │
│ · [Xoá]                                                            │
└─────────────────────────────────────────────────────────────────┘
```

| Vùng | Component/class đã có | Việc cần làm |
|---|---|---|
| KPI section | `KPI` object hardcode (dòng 6-11) | Nối `GET /api/v1/admin/kpi` — **endpoint này bạn phải tự viết** (mục 5.2). Giữ nguyên cấu trúc 2 card + method_note |
| Form thêm môn | State local `form`, gọi `addCourse()` từ context | Nối `POST /api/v1/admin/courses` — **tự viết** (mục 5.1). Tự động ingest sau khi thêm, hoặc để trạng thái `not_ingested` chờ upload tài liệu riêng (quyết định UX, xem mục 5.1) |
| Bảng curriculum | `STATUS_CFG` map 4 trạng thái, đã đẹp sẵn (dòng 13-18) | Nối `GET /api/v1/admin/courses` — **tự viết** |
| Nút xoá môn | `deleteCourse()` context, có xác nhận 2 bước (dòng 184-194) | Nối `DELETE /api/v1/admin/courses/{code}` — **tự viết**, hoặc dùng chung route với `POST` tuỳ thiết kế REST bạn chọn |

### 4.1 Phần còn thiếu — Audit Log Terminal (có sẵn API, chỉ thiếu UI)

Khác với KPI/curriculum, phần này **KHÔNG cần bạn viết backend** — `GET /api/v1/audit/events` đã có sẵn trên `origin/chung` (`src/api/audit.py`). Việc của bạn thuần UI.

**Spec (dựa theo ý tưởng "Developer Audit Logs Terminal" từng được phác thảo trong một bản nháp cũ đã xoá — bản đó có style neon/terminal đen bị coi là quá "glow", **không copy màu sắc đó**, chỉ lấy ý tưởng bố cục):
- Danh sách log dạng bảng/list gọn, mỗi dòng: thời gian · người dùng · hành động · kết quả — dùng font `Geist Mono` (`.mono`, đã có trong design system) để có cảm giác "log kỹ thuật" mà không cần nền đen/chữ neon.
- Có thể filter theo loại hành động (đăng nhập, can thiệp SV, thêm/xoá môn...).
- Đây là bằng chứng "theo dõi lỗi/quyết định" mà BTC yêu cầu ở Quy định chung mục 4 ("theo dõi tối thiểu độ trễ, lỗi và chi phí") — đừng bỏ qua chỉ vì nó không phải F6/F7 chính thức.

### 4.2 Rule Engine — quyết định scope trước khi build (đọc mục 5.3)

---

## 5. Đặc tả tính năng chi tiết + ví dụ cụ thể (kèm hướng dẫn tự viết backend)

### 5.1 F6 — Bảng curriculum, tự viết `src/api/admin.py`

**Tái dùng, không viết lại từ 0:** `chunk_repository.py` (đã có trên `origin/chung`, dùng để đếm số chunk mỗi môn) và `document_ingest_service.py` (đã có trên `origin/thanhbinh` — xin merge thêm file này vào nhánh tích hợp, báo Đăng).

**Endpoint cần viết:**
```
GET  /api/v1/admin/courses                          → { courses: [{ subject_code, subject_name, semester, ingest_status, chunk_count }] }
POST /api/v1/admin/courses                           → thêm môn mới, ingest_status mặc định "not_ingested"
DELETE /api/v1/admin/courses/{subject_code}           → xoá môn
POST /api/v1/admin/courses/{code}/documents           → upload tài liệu, gọi document_ingest_service, trả về ingest_status="processing" rồi cập nhật "ingested"/"failed"
```
**Output mẫu (đối chiếu với Playbook F6):**
```json
{ "courses": [
  { "subject_code": "SSA101", "subject_name": "Kỹ năng học thuật", "semester": "1", "ingest_status": "ingested", "chunk_count": 72 },
  { "subject_code": "PRF192", "subject_name": "Cơ sở lập trình",   "semester": "1", "ingest_status": "not_ingested", "chunk_count": 0 }
]}
```

### 5.2 F7 — KPI, tự viết trong cùng `src/api/admin.py`

**Endpoint cần viết:** `GET /api/v1/admin/kpi` → `{ with_cursus_overall: 0.78, baseline_overall: 0.45, method_note: "..." }`.
**Nguồn số liệu:** đọc từ `seed_students_SSA101.json` (`docs/planning/v2/data/`) mục `kpi_comparison` đã tính sẵn — **không cần tính toán phức tạp ở Gate 2**, chỉ đọc ra và trả về đúng field, kèm `method_note` giải thích rõ đây là "2 kịch bản mô phỏng độc lập, không suy từ nhau" (nguyên văn yêu cầu ở Playbook F7).
**Bắt buộc:** field `method_note` không được để trống hoặc thiếu trong response — frontend đã code sẵn để luôn hiển thị nó, nếu backend không trả sẽ vỡ UI.

### 5.3 Rule Engine — quyết định scope, không tự hứa quá khả năng backend

UI mẫu cũ từng phác thảo "công tắc iOS bật/tắt rule" nhưng **backend hiện không hỗ trợ cấu hình guardrail động** — `guardrail_service.py` hiện chạy logic cứng trong code. Có 2 lựa chọn, **thống nhất với Đăng trước khi code**:
1. **(Khuyến nghị cho Gate 2)** Chỉ hiển thị **read-only** danh sách rule đang bật (đọc tĩnh từ 1 file config hoặc hardcode danh sách "làm hộ bài / giải hộ / viết code hộ..." đã có trong `guardrail_service.py`) — không có công tắc bật/tắt thật.
2. **(Mốc 3, nếu dư giờ)** Xây thật endpoint `GET/PATCH /api/v1/admin/guardrail-rules`, để bật/tắt ảnh hưởng thật tới `guardrail_service.py` — việc lớn hơn, cần bàn kỹ với Đăng vì đụng vào logic bảo mật lõi.

---

## 6. Lịch làm việc theo ngày

| Ngày | Việc cụ thể | Phụ thuộc |
|---|---|---|
| **11/08 (T3, hôm nay)** | Đọc file này. Thiết kế trước schema request/response cho `src/api/admin.py` (viết ra giấy/docstring, chưa cần chạy được) — vì bạn không phụ thuộc Job #0 để BẮT ĐẦU thiết kế, chỉ phụ thuộc để CHẠY THỬ | Không phụ thuộc ai để bắt đầu |
| **12/08 (T4)** | Viết code thật `src/api/admin.py` (2 endpoint GET courses/kpi trước, POST/DELETE sau) — test độc lập bằng cách chạy backend local nếu `chung` đã merge được 1 phần, hoặc test trên chính branch `chung`/`thanhbinh` trước khi merge | `chunk_repository.py`, `document_ingest_service.py` đã có sẵn trên chung/thanhbinh |
| **13/08 (T5) — mục tiêu "1 flow hoàn chỉnh"** | Nối `AdminConsole.jsx` vào API thật vừa viết — đây là bước cuối (bước 6) trong luồng demo 6 bước ở `09-Team-Assignment.md` mục 4 | Backend chạy (Job #0), code admin.py của chính bạn |
| **14/08 (Gate 2)** | Sáng: chỉ sửa lỗi chặn demo | — |
| **15-22/08 (Mốc 3)** | Audit Log UI (mục 4.1); quyết định + build Rule Engine thật nếu chọn lựa chọn 2 ở mục 5.3; CRUD ingest đầy đủ qua UI (`07-Production-Readiness-Checklist.md` liệt kê đây là việc Mốc 3) | |
| **23/08** | Freeze, rượt demo | — |

---

## 7. Definition of Done

- [ ] `src/api/admin.py` tồn tại, có ≥4 endpoint (courses GET/POST/DELETE, kpi GET), đăng ký vào `main.py` (`app.include_router(admin_router, prefix="/api/v1")` — xem cách `chung` đăng ký các router khác làm mẫu)
- [ ] `KPI` hardcode trong `AdminConsole.jsx` (dòng 6-11) đã bị xoá, dữ liệu từ API thật, `method_note` luôn hiện
- [ ] Bảng curriculum phản ánh đúng trạng thái ingest thật, không phải màu ngẫu nhiên
- [ ] Audit log hiện được ít nhất 5 sự kiện thật (đăng nhập, thêm môn...) khi demo
- [ ] Rule Engine ở đúng scope đã thống nhất với Đăng (read-only hoặc thật), không hứa UI vượt quá backend

---

## 8. Prompt mẫu — dán thẳng cho Gemini/Antigravity

```
Bạn là full-stack engineer cho Cursus (backend FastAPI + SQLAlchemy, frontend React 19 + Vite + Tailwind v4).
Tôi phụ trách role Admin: F6 (quản lý curriculum đã nạp), F7 (KPI). Khác các role khác, tôi phải TỰ VIẾT
endpoint backend mới vì chưa ai làm — không có sẵn để nối.

Context bắt buộc đọc trước (tôi đã dán/đính kèm):
- docs/frontend/00_AI_CONTEXT_PACK.md (design system, token màu/spacing/motion — cho phần frontend)
- Nội dung file docs/archive/planning-v2/roles/CHUNG_admin.md mục 5 (schema request/response cần viết)
- src/api/instructor.py hoặc src/api/student.py trên nhánh chung (làm mẫu cấu trúc route/dependency injection)

Nhiệm vụ hôm nay: [ví dụ "Viết src/api/admin.py với 2 endpoint GET /admin/courses và GET /admin/kpi,
tái dùng chunk_repository.py để đếm chunk mỗi môn, đọc KPI từ seed_students_SSA101.json"].

Ràng buộc bắt buộc:
- Response GET /admin/kpi PHẢI có field method_note, không được thiếu.
- Không tự tính KPI bằng công thức mới — đọc đúng số đã có sẵn trong file seed, không suy diễn.
- Theo đúng pattern auth/dependency injection mà các router khác (student.py, instructor.py) đã dùng
  (get_current_user_from_token, require_roles) — không tự chế cách auth riêng.
- Phần frontend: giữ nguyên toàn bộ class CSS/token đã có, chuỗi text mới thêm vào locales/en.js và vi.js.
- Nếu chưa chắc chunk_repository.py/document_ingest_service.py có hàm nào, đọc code trước, không tự bịa
  tên hàm.
```

---

## 9. Liên kết liên quan

[`docs/archive/planning-v2/00-Cursus-Playbook.md`](../00-Cursus-Playbook.md) F6/F7 · [`docs/archive/planning-v2/07-Cursus-Production-Readiness-Checklist.md`](../07-Cursus-Production-Readiness-Checklist.md) (CRUD ingest đầy đủ, việc Mốc 3) · [`docs/archive/planning-v2/roles/DANG_infra-auth-frontend.md`](DANG_infra-auth-frontend.md) (thống nhất scope Rule Engine, xin merge thêm file từ thanhbinh).
