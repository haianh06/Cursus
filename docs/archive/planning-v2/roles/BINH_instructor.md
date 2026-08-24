# Docs riêng — Nguyễn Anh Bình · Role Giảng viên (F4 Dashboard · F5 Risk + HITL)

**Cập nhật:** 11/08/2026 · **Đọc cùng:** [`docs/frontend/00_AI_CONTEXT_PACK.md`](../../../frontend/00_AI_CONTEXT_PACK.md) (design system — dán cho AI), [`../09-Cursus-Team-Assignment.md`](../09-Cursus-Team-Assignment.md) (bức tranh toàn team), [`../00-Cursus-Playbook.md`](../00-Cursus-Playbook.md) (spec gốc F4/F5).

**Cách dùng file này:** đọc mục 1-2 để hiểu đúng ràng buộc HITL (đây là phần BTC chắc chắn kiểm tra), mục 3 để có tham khảo thiết kế thật, mục 4-5 để biết chính xác UI/tính năng cần build, mục 6 để biết làm gì hôm nay, mục 8 để copy prompt dán thẳng cho Gemini/Antigravity.

---

## 0. Bạn sở hữu gì

| Tính năng | Mã | Màn hình | File hiện tại |
|---|---|---|---|
| Dashboard tổng quan lớp (ẩn danh) | F4 | Instructor Home — phần trên | `frontend/src/components/instructor/InstructorHome.jsx` |
| Danh sách SV nguy cơ trễ + nút "Đánh dấu đã can thiệp" (**HITL**) | F5 | Instructor Home — phần giữa | cùng file |
| Hàng chờ duyệt "Yêu cầu xem xét lại" của SV bị Guardrail chặn | — (đã thiết kế sẵn trong mock, chưa có tên mã F) | Instructor Home — phần dưới | cùng file |
| Chi tiết 1 case rủi ro | — | **Chưa có UI, cần build mới** | — |

**Không phải việc của bạn:** dashboard sinh viên, admin console, màn login/register.

---

## 1. Tại sao F5/HITL là phần chắc chắn bị chấm điểm nặng nhất trong role của bạn

Quy định chung BTC ghi rõ: *"Các quyết định điểm số... phải có người chịu trách nhiệm phê duyệt"* và sản phẩm tối thiểu phải *"thể hiện HITL cho hành động rủi ro"*. F5 chính là hiện thân trực tiếp của yêu cầu này — nếu nút "Đánh dấu đã can thiệp" chỉ đổi màu UI mà không thật sự phản ánh "hệ thống không tự động gửi gì cho SV, người quyết định là GV", giám khảo sẽ phát hiện ngay khi hỏi xoáy vào chỗ này.

---

## 2. Ràng buộc bắt buộc

1. **Hệ thống KHÔNG BAO GIỜ tự động gửi bất cứ gì cho SV** khi bạn bấm "Đánh dấu đã can thiệp" — API chỉ đổi trạng thái nội bộ (`status: 'reviewed'`), không kích hoạt email/notification tự động. Nếu sau này có tính năng gửi thông báo, phải là hành động **riêng, do GV chủ động bấm thêm**, không gộp chung vào nút can thiệp.
2. **Dashboard lớp chỉ hiện số liệu tổng hợp** — không hiện tên/nội dung chat riêng của từng SV ở màn tổng quan (đã đúng trong UI hiện tại — badge "FERPA Compliant" đã có sẵn, giữ nguyên tinh thần này).
3. **Công thức cảnh báo rủi ro không phải AI đoán** — dựa công thức có sẵn (trễ ≥2 deadline liên tiếp trong 2 tuần, HOẶC hoàn thành <50% task trong 3 tuần liên tiếp) đã tính sẵn trong seed data, bạn chỉ hiển thị lý do backend trả về, không tự suy diễn thêm.
4. Khi duyệt "Yêu cầu xem xét lại" của SV (mục 5.3) — đây là hành động rủi ro thứ 2 cần HITL, không tự động unblock.

---

## 3. Sản phẩm tham khảo thật — học cái gì, đừng bắt chước cái gì

| Sản phẩm | Link | Học cái gì cho Cursus | Đừng bắt chước |
|---|---|---|---|
| **Starfish (EAB)** | Tổng quan: [eab.com/solutions/starfish](https://eab.com/solutions/starfish/) | **Tham khảo trực tiếp nhất cho F5**: cho phép GV gắn cờ SV có nguy cơ (điểm thấp/vắng nhiều/trễ bài) VÀ có tính năng "kudos" — ghi nhận SV tiến bộ, không chỉ toàn cảnh báo tiêu cực. Cân nhắc thêm 1 badge tích cực nhỏ cho SV cải thiện, không bắt buộc Gate 2 nhưng là hướng nâng cấp tốt cho Mốc 3 | Starfish tích hợp trực tiếp với hệ thống điểm/LMS thật của trường — Cursus dùng dữ liệu mô phỏng, đừng thiết kế UI ngụ ý đang đọc dữ liệu trường thật |
| **Civitas Learning** | Bài viết cảnh báo: [Is Your Early Alert System Harming Student Success?](https://www.civitaslearning.com/blog/effective-early-alert-system-in-higher-education/) | **Bài học quan trọng nhất, đọc kỹ**: hệ thống cảnh báo sớm dùng sai cách (soi mói, punitive) làm SV cảm thấy bị theo dõi, phản tác dụng. Cursus phải giữ giọng điệu `suggested_action` là **hỗ trợ** ("Đặt lịch gặp trao đổi", "Gửi tin nhắn động viên" — đã đúng trong seed data), không phải cảnh cáo | Đừng thêm điểm "risk score" trần trụi kiểu chấm điểm SV — giữ định dạng lý do cụ thể + hành động gợi ý như hiện tại |
| **Canvas LMS — Instructor Analytics** | Tổng quan sản phẩm: [instructure.com/canvas](https://www.instructure.com/canvas) | Canvas (chính LMS mà đề bài BTC nhắc tới) có màn giảng viên dạng 2 cấp: tổng quan lớp + drill-down từng SV — đúng cấu trúc bạn cần build cho "Risk Case Detail" (mục 4.2, hiện chưa có UI) | |
| **GitHub — shadcndashboard/shadcndashboard** | [github.com/shadcndashboard/shadcndashboard](https://github.com/shadcndashboard/shadcndashboard) | Dashboard mã nguồn mở React+Vite+Tailwind (cùng nhóm công nghệ gần Cursus), có sẵn bố cục KPI card + bảng dữ liệu + biểu đồ — tham khảo cấu trúc component cho bảng "Risk Case Detail", không copy nguyên UI kit (Cursus đã có design system riêng, xem `00_AI_CONTEXT_PACK.md`) | |

---

## 4. UI/UX cụ thể — Instructor Home (`InstructorHome.jsx`)

Đã có UI thật (211 dòng) cho phần Dashboard + Alert list + Guardrail Queue — **không cần thiết kế lại**, chỉ nối dữ liệu thật + build thêm 1 màn còn thiếu (Risk Case Detail).

```
┌─────────────────────────────────────────────────────────────────┐
│ HEADER — tiêu đề + badge "FERPA Compliant"                       │
├───────────────┬───────────────┬───────────────────────────────┤
│ Tổng SV        │ SV nguy cơ     │ Guardrail chờ duyệt              │  ← 3 StatCard
├───────────────┴───────────────┴───────────────────────────────┤
│ CỘT TRÁI (60%)                       │ CỘT PHẢI (40%)            │
│ Biểu đồ % hoàn thành theo tuần        │ Danh sách cảnh báo SV      │
│ (bar chart 4 tuần, cảnh báo nếu       │ (mỗi card: tên · lý do ·   │
│ xu hướng giảm)                        │ gợi ý · nút "Can thiệp")   │
├───────────────────────────────────────┴───────────────────────┤
│ HÀNG CHỜ DUYỆT GUARDRAIL — mỗi card: SV · câu hỏi bị chặn ·      │
│ 2 nút "Giữ chặn" / "Duyệt bỏ chặn"                                │
└─────────────────────────────────────────────────────────────────┘
```

| Vùng | Component/class đã có | Việc cần làm khi nối API thật |
|---|---|---|
| 3 StatCard (SV/nguy cơ/guardrail chờ duyệt) | `StatCard` component (dòng 12-24) | Nối `GET /api/v1/instructor/dashboard` — bỏ `DASH_DATA` hardcode (dòng 6-10) |
| Biểu đồ % hoàn thành theo tuần | `BarChart` component (dòng 26-63), đã có cảnh báo tự động khi tuần cuối < tuần đầu | Nối cùng `GET /api/v1/instructor/dashboard`, giữ nguyên logic cảnh báo xu hướng giảm |
| Danh sách cảnh báo SV | `AlertCard` (dòng 65-92) | Nối `GET /api/v1/instructor/risks`. Nút "Can thiệp" → `POST /api/v1/instructor/risks/{id}/intervention` (xem mục 5.2) |
| Hàng chờ Guardrail | Đọc từ `queue` context, nút Duyệt/Giữ chặn (dòng 188-196) | **Đây chính là tính năng Appeal ở mục 5.3 — cần endpoint mới, phối hợp Hải Anh + Đăng, xem chi tiết dưới** |

### 4.1 Màn còn thiếu — Risk Case Detail (chưa có UI, bạn cần build mới)

Đây là 1 Critical Gap đã biết. Khi GV click vào 1 `AlertCard`, cần mở chi tiết đầy đủ hơn thay vì chỉ đọc 1 dòng lý do.

**Spec đề xuất (theo `docs/frontend/03_COMPONENT_SPECIFICATIONS.md` mục Drawer):** mở dạng Drawer trượt từ phải, rộng 400px desktop / full-width bottom sheet mobile, nội dung:
- Tên SV (ẩn ID nội bộ nếu không cần) + môn học
- Lịch sử hoàn thành task 4-6 tuần gần nhất (mini bar chart hoặc list)
- Chi tiết bằng chứng: deadline nào đã trễ, task nào bị block — **tuyệt đối không hiện nội dung chat/câu hỏi riêng của SV** (yêu cầu privacy đã ghi trong audit cũ)
- Nút "Đánh dấu đã can thiệp" (giống `AlertCard` nhưng ở đây có thêm ô ghi chú GV tự nhập lý do can thiệp — trường `note` gửi kèm `POST .../intervention`)

**Gọi:** `GET /api/v1/instructor/risks/{risk_id}`.

---

## 5. Đặc tả tính năng chi tiết + ví dụ cụ thể

### 5.1 F4 — Dashboard lớp

**Gọi:** `GET /api/v1/instructor/dashboard?subject_code=SSA101`
**Output mẫu:** `{ class_size: 12, class_avg_completion_by_week: [0.9, 0.79, 0.73, 0.7] }` — khớp đúng với `DASH_DATA` mock hiện tại, chỉ là số thật thay vì hardcode.
**Ràng buộc:** không hiện tên/nội dung riêng SV ở màn này, chỉ số tổng hợp.

### 5.2 F5 — Cảnh báo + HITL

**Gọi xem:** `GET /api/v1/instructor/risks?subject_code=SSA101`
**Output mẫu (theo Playbook, khớp với seed data thật `seed_students_SSA101.json`):**
```json
{ "alerts": [
  { "student_id": "sv03", "display_name": "Huy",  "reason": "Tỷ lệ hoàn thành <50% trong 3 tuần liên tiếp", "suggested_action": "Đặt lịch gặp trao đổi", "status": "pending_review" },
  { "student_id": "sv04", "display_name": "Mai",  "reason": "Trễ deadline liên tiếp 2 tuần gần nhất",       "suggested_action": "Gửi tin nhắn động viên",  "status": "pending_review" }
]}
```
**Gọi duyệt:** `POST /api/v1/instructor/risks/{risk_id}/intervention` — body ví dụ `{ action: "Đặt lịch gặp trao đổi", note: "Đã gọi điện trao đổi, hẹn gặp thứ 5" }`. **Response không kích hoạt bất kỳ thông báo nào tới SV** — chỉ đổi `status → reviewed`.
**Trạng thái UI:** card chuyển từ viền vàng (`pending_review`) sang viền xanh mờ đi (`reviewed`) — đã có sẵn logic này (dòng 68 `InstructorHome.jsx`), giữ nguyên.

### 5.3 Hàng chờ duyệt "Yêu cầu xem xét lại" (Appeal) — cần xây mới, phối hợp Hải Anh + Đăng

SV bị chặn guardrail có thể bấm "Yêu cầu xem xét lại" (xem `docs/archive/planning-v2/roles/HAIANH_student.md` mục 5.3). Khi đó, 1 item xuất hiện trong hàng chờ của bạn:
```json
{ "id": "gr1", "student_name": "Minh Tuấn", "question": "Giải hộ em bài tập Programming Assignment 2", "timestamp": "...", "status": "pending" }
```
Bạn có 2 lựa chọn: **"Giữ chặn"** (giữ nguyên, SV nhận thông báo "Giảng viên đã từ chối yêu cầu xem xét lại") hoặc **"Duyệt bỏ chặn"** (Curi trả lời lại với gợi ý hướng làm, không phải đáp án — SV nhận thông báo "Đã được giảng viên duyệt bỏ chặn"). UI 2 trạng thái này **đã có sẵn hoàn chỉnh trong mock** (`InstructorHome.jsx` dòng 188-196) — việc của bạn là nối vào endpoint thật.
**Cần xây mới (báo Đăng):** `GET /api/v1/instructor/guardrail-queue`, `PATCH /api/v1/instructor/guardrail-queue/{id}` — endpoint này **chưa tồn tại trên `origin/chung`**, vì tính năng này được thiết kế ở tầng frontend trước, chưa có ai làm backend. Đây không phải lỗi của bạn — chỉ cần biết để không tưởng nhầm là đã có sẵn như F4/F5.

---

## 6. Lịch làm việc theo ngày

| Ngày | Việc cụ thể | Phụ thuộc |
|---|---|---|
| **11/08 (T3, hôm nay)** | Đọc file này. Polish UI hiện tại theo `docs/frontend/08_SCREEN_CONSISTENCY_CHECKLIST.md`. Phác thảo layout Risk Case Detail (mục 4.1) — chỉ cần wireframe/JSX rỗng, chưa cần API | Không phụ thuộc ai |
| **12/08 (T4)** | Viết `lib/api.js` phần Instructor (F4/F5) trong lúc chờ Đăng xong Job #0. Bắt đầu build UI Risk Case Detail (Drawer) | — |
| **13/08 (T5) — mục tiêu "1 flow hoàn chỉnh"** | Nối xong F4 (dashboard load số thật) và F5 (`POST .../intervention` — đây là bước 4-5 trong luồng demo 6 bước ở `09-Team-Assignment.md` mục 4, phải xong sau khi Hải Anh xong F2/F3) | Backend chạy (Job #0), Hải Anh xong F2/F3 để có dữ liệu SV thật để test |
| **14/08 (Gate 2)** | Sáng: chỉ sửa lỗi chặn demo | — |
| **15-22/08 (Mốc 3)** | Hoàn thiện Risk Case Detail; phối hợp xây endpoint appeal (mục 5.3) nếu còn thời gian; xác nhận với Đăng có cần giữ tính năng Appeal ở Gate 2 hay dời hẳn Mốc 3 nếu backend chưa kịp | |
| **23/08** | Freeze, rượt demo | — |

---

## 7. Definition of Done

- [ ] `DASH_DATA` hardcode (dòng 6-10 `InstructorHome.jsx`) đã bị xoá, dữ liệu 100% từ API
- [ ] Nút "Đánh dấu đã can thiệp" gọi đúng `POST .../intervention`, xác nhận bằng thực nghiệm rằng không có request nào khác được gửi tới SV
- [ ] Dashboard không hiện tên/nội dung chat riêng SV ở màn tổng quan
- [ ] Risk Case Detail (Drawer) hiển thị được ít nhất: lịch sử hoàn thành, lý do cụ thể, ô ghi chú can thiệp
- [ ] Test thật: từ tài khoản demo Giảng viên, xác nhận thấy đúng SV Huy/Mai trong danh sách rủi ro (theo seed data)

---

## 8. Prompt mẫu — dán thẳng cho Gemini/Antigravity

```
Bạn là frontend engineer cho Cursus (React 19 + Vite + Tailwind v4, JS thuần không TS).
Tôi phụ trách role Giảng viên: F4 (dashboard lớp), F5 (cảnh báo rủi ro + HITL "đánh dấu đã can thiệp").

Context bắt buộc đọc trước (tôi đã dán/đính kèm):
- docs/frontend/00_AI_CONTEXT_PACK.md (design system, token màu/spacing/motion)
- Nội dung file docs/archive/planning-v2/roles/BINH_instructor.md mục 4-5 (UI hiện có + API cần nối)

Nhiệm vụ hôm nay: [ví dụ "Build màn Risk Case Detail dạng Drawer theo spec mục 4.1 — trượt từ phải,
400px desktop, hiển thị lịch sử hoàn thành + lý do + ô ghi chú can thiệp"].

Ràng buộc bắt buộc:
- Nút can thiệp/duyệt guardrail KHÔNG được tự ý thêm logic gửi email/notification cho SV — chỉ đổi
  trạng thái nội bộ qua đúng endpoint đã chỉ định.
- Không hiện nội dung chat/câu hỏi riêng của SV ở màn dashboard tổng quan (chỉ ở Risk Case Detail nếu
  thật sự cần bằng chứng, và chỉ hiện cho đúng SV đang xem, không lộ chéo).
- Giữ nguyên toàn bộ class CSS/token đã có — không tự đổi màu/spacing.
- Chuỗi text mới phải thêm vào frontend/src/locales/en.js và vi.js.
- Nếu thiếu thông tin (endpoint chưa rõ), hỏi lại thay vì tự bịa field.
```

---

## 9. Liên kết liên quan

[`docs/archive/planning-v2/00-Cursus-Playbook.md`](../00-Cursus-Playbook.md) F4/F5 · [`docs/frontend/03_COMPONENT_SPECIFICATIONS.md`](../../../frontend/03_COMPONENT_SPECIFICATIONS.md) (Drawer, Risk alert) · [`docs/archive/planning-v2/roles/HAIANH_student.md`](HAIANH_student.md) (phối hợp appeal flow) · [`docs/archive/planning-v2/roles/DANG_infra-auth-frontend.md`](DANG_infra-auth-frontend.md) (khi cần API/auth chưa sẵn sàng).
