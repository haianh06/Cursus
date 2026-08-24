# Docs riêng — Nguyễn Hải Anh · Role Sinh viên (F2 Plan · F3 Q&A · Reflect)

**Cập nhật:** 11/08/2026 · **Đọc cùng:** [`docs/frontend/00_AI_CONTEXT_PACK.md`](../../../frontend/00_AI_CONTEXT_PACK.md) (design system — dán cho AI), [`../09-Cursus-Team-Assignment.md`](../09-Cursus-Team-Assignment.md) (bức tranh toàn team), [`../00-Cursus-Playbook.md`](../00-Cursus-Playbook.md) (spec gốc F2/F3).

**Cách dùng file này:** đọc mục 1-2 để hiểu đúng ràng buộc, mục 3 để có cảm hứng thiết kế thật (không phải tự nghĩ từ đầu), mục 4-5 để biết chính xác UI/tính năng cần build, mục 6 để biết làm gì hôm nay, mục 8 để copy prompt dán thẳng cho Gemini/Antigravity.

---

## 0. Bạn sở hữu gì

| Tính năng | Mã | Màn hình | File hiện tại |
|---|---|---|---|
| Lập kế hoạch tuần từ mục tiêu SV nhập | F2 | Student Home — cột trái | `frontend/src/components/student/StudentHome.jsx` |
| Hỏi-đáp có trích nguồn + phản ứng khi bị Guardrail chặn | F3 | Student Home — cột phải | cùng file |
| Phản tư cuối tuần (Reflect) | — | Trang riêng | `frontend/src/components/student/StudentReflection.jsx` |

**Không phải việc của bạn:** dashboard giảng viên, admin console, màn login/register (Đăng phụ trách khung auth, bạn chỉ cần biết `user` prop được truyền vào từ đâu).

---

## 1. Tại sao 2 tính năng này là "lõi" — đọc trước khi code

Đề bài BTC (EDU-01) định nghĩa sản phẩm bằng đúng chu trình **Plan → Do → Reflect**. F2 và Reflect là 2/3 mắt xích đó — nếu 2 cái này không mượt, cả sản phẩm mất trọng tâm dù các phần khác đẹp đến đâu. F3 (Q&A) là nơi guardrail "chống làm hộ bài" phải thể hiện rõ nhất, vì đây là màn hình giám khảo chắc chắn sẽ tự tay gõ thử câu "giải hộ em bài này" để test.

---

## 2. Ràng buộc bắt buộc (không thương lượng, vi phạm = bị BTC trừ điểm PLO6)

1. **Guardrail chạy TRƯỚC khi gọi LLM chính** — nếu câu hỏi thuộc dạng "làm hộ/giải hộ/viết code hộ", chặn ngay, không tốn tiền gọi AI. Pattern hiện có sẵn trong mock (`StudentHome.jsx` dòng 72-75) — khi nối API thật, đây là logic phía **backend** (`qa_service.py` trên `origin/chung`), frontend chỉ hiển thị đúng `blocked: true` mà backend trả về, **không tự đoán guardrail ở frontend nữa**.
2. **Không bao giờ bịa câu trả lời học thuật.** Nếu backend trả `source_label: null`, hiển thị đúng "Không tìm thấy thông tin liên quan trong tài liệu môn học" — không tự chế câu trả lời nghe hợp lý.
3. **Mọi task/câu trả lời có nguồn phải hiện citation chip** (`Syllabus SSA101 — Session 7` kiểu vậy) — không có citation = không hiện task đó mà không cảnh báo rõ ("gợi ý mang tính tham khảo").
4. **AI Tutor gợi ý hướng làm, không đưa đáp án trực tiếp** khi bị chặn guardrail — copy đúng tinh thần Khanmigo (xem mục 3).
5. Toàn bộ chuỗi hiển thị phải có trong `locales/en.js` và `vi.js` — không hardcode chuỗi Việt/Anh trong JSX.

---

## 3. Sản phẩm tham khảo thật — học cái gì, đừng bắt chước cái gì

| Sản phẩm | Link | Học cái gì cho Cursus | Đừng bắt chước |
|---|---|---|---|
| **Sunsama** | [sunsama.com](https://sunsama.com) | Nghi thức lập kế hoạch ngày/tuần rất rõ ràng — "hôm nay có gì" tách bạch khỏi "tuần này mục tiêu gì". `StudentHome.jsx` đã có khối "Timeline hôm nay" 3 cột (dòng 144-214) đúng tinh thần này — giữ nguyên, đừng xoá khi nối API thật | Sunsama thu phí cao, không có AI tutor/trích nguồn — không phải mô hình kinh doanh liên quan |
| **Notion AI** (tính năng "syllabus → study calendar") | [notion.com](https://www.notion.com) | Luồng "tải syllabus lên → AI tự trích deadline → tạo task list" **chính là F2** — bạn có thể mô tả prompt cho Gemini theo đúng luồng này | Notion là canvas tự do, Cursus cần luồng hẹp/có kiểm soát hơn (không để SV tự ý tạo cấu trúc lung tung) |
| **Motion** | [usemotion.com](https://www.usemotion.com) | Cách AI tự xếp việc theo độ ưu tiên/deadline, có nhãn "urgent" nổi bật — task list của bạn đã có badge "urgent" khi deadline <48h (`isUrgent()` dòng 10) | Motion tự động re-schedule toàn bộ lịch — Cursus không nên tự ý dời lịch của SV mà không hỏi |
| **Khanmigo (Khan Academy)** | Xem case study: [Khan Academy AI Tutor](https://www.freethink.com/consumer-tech/khanmigo-ai-tutor) | **Tham khảo trực tiếp cho F3**: nguyên tắc Socratic — AI hỏi dẫn dắt ("Bạn nghĩ bước tiếp theo là gì?") thay vì đưa đáp án; khi SV cố tình xin đáp án, Khanmigo *vẫn dẫn dắt* thay vì chặn cứng. Cursus nghiêm hơn (chặn hẳn với bài tính điểm), nhưng giọng điệu phản hồi guardrail nên học theo hướng "gợi mở", không phải "cấm đoán" | Khanmigo được phép giải thích sâu bài tập không tính điểm — Cursus giới hạn chặt hơn ở BẤT KỲ nội dung nào nghi là bài tính điểm |
| **OLM.vn** | [olm.vn](https://olm.vn/) | Nền tảng giáo dục Việt, giao diện thân thiện bám sát khung chương trình — tham khảo cách Việt hoá tự nhiên (không dịch máy móc từng chữ) cho copy tiếng Việt trong `locales/vi.js` | — |
| **GitHub — Cinnamon/kotaemon** | [github.com/Cinnamon/kotaemon](https://github.com/Cinnamon/kotaemon) | RAG chat mã nguồn mở, có citation kèm xem trước đoạn trích PDF khi click — copy Ý TƯỞNG "click citation → mở panel xem đoạn trích gốc" cho Source Preview (đã đặc tả ở `docs/frontend/03_COMPONENT_SPECIFICATIONS.md` mục "Source preview"), không copy code (khác stack Python/Gradio) | |
| **GitHub — render-examples/RAG-chatbot-template** | [github.com/render-examples/RAG-chatbot-template](https://github.com/render-examples/RAG-chatbot-template) | Stack **gần giống Cursus nhất** trong các ví dụ tìm được: React/Vite frontend + Postgres/pgvector + citation trong response — đọc cách họ tổ chức gọi API/hiển thị nguồn để đối chiếu cách bạn viết `lib/api.js` | Đừng copy nguyên schema DB — Cursus đã có `src/db/models.py` riêng trên `origin/chung` |

---

## 4. UI/UX cụ thể — Student Home (`StudentHome.jsx`)

Đã có UI thật (436 dòng), **không cần thiết kế lại từ đầu** — chỉ nối dữ liệu thật. Bảng dưới mô tả từng vùng để bạn (hoặc Gemini) biết chính xác đụng vào đâu.

```
┌─────────────────────────────────────────────────────────────────┐
│ BANNER (gradient tối) — chào SV + streak + nút "Bắt đầu tập trung"│
├─────────────────────────────────────────────────────────────────┤
│ TIMELINE HÔM NAY — 3 ô ngang: giờ · tên task · trạng thái       │
├───────────────────────────────────────┬─────────────────────────┤
│ SYNC BAR — môn đang chọn + dropdown    │                         │
├───────────────────────────────────────┤                         │
│ CỘT TRÁI (60%)                         │ CỘT PHẢI (40%)          │
│ • Ô nhập mục tiêu tuần + nút "Lập      │ AI CHAT PANEL           │
│   kế hoạch"                            │ • Header + nút demo     │
│ • Danh sách task, mỗi task:            │   guardrail             │
│   ✓/○ · tiêu đề · citation chip ·      │ • Khung hội thoại       │
│   badge "urgent" nếu <48h · nút xoá    │   (user/assistant/      │
│                                         │   blocked 3 kiểu bubble)│
│                                         │ • Ô nhập + nút gửi      │
└───────────────────────────────────────┴─────────────────────────┘
```

| Vùng | Component/class đã có | Việc cần làm khi nối API thật |
|---|---|---|
| Banner chào mừng | `.banner-gradient`, streak badge cứng "5 ngày streak" | Streak hiện đang hardcode — nối vào `GET /api/v1/student/dashboard` nếu backend trả về streak thật, nếu chưa có thì **ẩn badge streak** thay vì hiện số giả |
| Timeline hôm nay | Map cứng 3 task `t1/t2/t3` (dòng 163-167) | Thay bằng `GET /api/v1/plans/timetable` — bao nhiêu task trong ngày thì hiện bấy nhiêu, không cứng số 3 |
| Ô nhập mục tiêu + Lập kế hoạch | `handlePlan()` dòng 50-58, hiện `await new Promise(setTimeout)` giả lập loading | Thay bằng `POST /api/v1/plans/generate` thật — **giữ nguyên state `planState` loading/success**, chỉ đổi nguồn dữ liệu. Khi có kết quả, gọi thêm `POST /api/v1/plans/accept` khi SV xác nhận (xem mục 5.1) |
| Task list | `tasks.map(...)`, có citation chip đúng chuẩn rồi | `toggleTask`/`deleteTask` → nối `PATCH /api/v1/plans/tasks/{task_id}` |
| Course selector | Dropdown local, đọc từ `courses` mock | Nối `GET /api/v1/student/courses` |
| AI Chat | `handleSend()` dòng 64-93, đang tự đoán guardrail bằng regex JS | **Xoá đoạn regex `GUARDRAIL_PATTERNS`** (dòng 72-75) — đây là chỗ duy nhất bạn phải xoá code, không phải chỉ thêm. Guardrail thật chạy ở backend, frontend chỉ gọi `POST /api/v1/qa` và hiển thị đúng field `blocked` backend trả về |
| Chat bubble bị chặn | `.shake`, nút "Yêu cầu xem xét lại" (`sendAppeal`) | **Xem mục 5.3 — tính năng Appeal cần backend mới, phối hợp với Bình** |

### 4.1 Reflection (`StudentReflection.jsx`)

```
┌───────────────────────────────┬─────────────────────┐
│ BANNER — "Phản tư Tuần N" +    │  LỊCH SỬ PHẢN TƯ     │
│ streak                         │  (danh sách card,    │
├───────────────────────────────┤  mỗi card: tuần ·    │
│ WIZARD 3 BƯỚC (progress bar)   │  rating badge ·      │
│ 1. Đánh giá tuần (3 lựa chọn)  │  tóm tắt · ngày)     │
│ 2. Điều gì khó khăn (textarea) │                       │
│ 3. Kế hoạch tuần tới (textarea)│                       │
│ → Màn "Đã lưu" hiện tóm tắt    │                       │
└───────────────────────────────┴─────────────────────┘
```

Đã hoàn chỉnh về mặt UI (wizard step, progress bar, màn xác nhận) — việc cần làm: thay `addReflection()` local (context) bằng `POST /api/v1/student/reflections/generate`, thay `reflections` mock bằng `GET /api/v1/student/reflections`.

**Gợi ý nâng cấp màu (không bắt buộc, làm nếu dư giờ):** hiện Reflection dùng `var(--accent)` (xanh) cho mọi accent — có token riêng `var(--reflect)` (tím, `#7c3aed`/`#a78bfa`) trong design system dành đúng cho màn này, giúp phân biệt trực quan với Plan (xanh). Đổi progress bar + nút chính sang `var(--reflect)` nếu có thời gian, không bắt buộc cho Gate 2.

---

## 5. Đặc tả tính năng chi tiết + ví dụ cụ thể

### 5.1 F2 — Lập kế hoạch tuần

**Input SV nhập:** `"Hoàn thành Project Part 1 tuần này"`
**Gọi:** `POST /api/v1/plans/generate` — body `{ subject_code: "SSA101", goal_text: "..." }`
**Output mẫu (theo Playbook, đối chiếu khi backend trả về):**
```json
{ "tasks": [
  { "task_id": "t1", "title": "Xác định đề tài & outline Project Part 1", "duration_estimate": "2h", "source_label": "Syllabus SSA101 — Session 7" },
  { "task_id": "t2", "title": "Đọc chương liên quan trong College Success", "duration_estimate": "1.5h", "source_label": "Syllabus SSA101 — Overview & Grading Policy" },
  { "task_id": "t3", "title": "Viết nháp phần mở đầu", "duration_estimate": "1h", "source_label": "Syllabus SSA101 — Session 7" }
]}
```
**Trạng thái bắt buộc:** Loading = "Đang lập kế hoạch..." (skeleton 3 dòng, đã có `planState='loading'`) · Empty = "Chưa có kế hoạch cho tuần này." · Success = list task card có citation (đã có) · Error = "Không thể lập kế hoạch lúc này, thử lại sau." + nút Thử lại (**chưa có UI Error — cần thêm**).
**Edge case bắt buộc xử lý:** không tìm thấy nội dung liên quan trong syllabus → vẫn trả task chung chung kèm cảnh báo "Không tìm thấy dữ liệu môn cụ thể, đề xuất mang tính tham khảo" — hiển thị cảnh báo này rõ ràng, không giấu.

### 5.2 F3 — Hỏi đáp có trích nguồn

**Input hợp lệ:** `"Điều kiện để qua môn SSA101 là gì?"` → `{ blocked: false, answer: "Theo syllabus, để qua môn bạn cần điểm thi cuối kỳ ≥4 và điểm trung bình ≥5/10.", source_label: "Syllabus SSA101 — Overview & Grading Policy" }`
**Input ngoài phạm vi:** câu hỏi không liên quan syllabus → `{ blocked: false, answer: "Không tìm thấy thông tin liên quan trong tài liệu môn học.", source_label: null }`
**Input vi phạm liêm chính:** `"Giải hộ em bài tập nhóm tuần 4"` → `{ blocked: true, answer: "Mình không làm bài hộ được, nhưng mình có thể gợi ý hướng tiếp cận — bạn thử bắt đầu từ phần liên quan trong tài liệu môn xem sao.", block_reason: "academic_integrity" }` → render bubble đỏ (`.chat-bubble-blocked`, đã có `.shake`).
**Gọi:** `POST /api/v1/qa` — body `{ subject_code, question }`.

### 5.3 Tính năng "Yêu cầu xem xét lại" (Appeal) — cần xây mới, phối hợp với Bình

Đây là tính năng **đã có UI hoàn chỉnh trong mock** (`sendAppeal`/`resolveAppeal` trong `CursusContext.jsx`) nhưng **chưa có endpoint backend nào trên `origin/chung`** — không phải lỗi của bạn, chỉ là chưa ai xây. Luồng: SV bị chặn guardrail → bấm "Yêu cầu xem xét lại" → vào hàng đợi của Bình (Instructor) → Bình duyệt (mở lại câu trả lời, có ghi chú "ĐÃ ĐƯỢC GIẢNG VIÊN DUYỆT") hoặc từ chối (giữ chặn). **Việc cần làm:** báo Đăng cần thêm 2 endpoint mới (`POST /api/v1/qa/{message_id}/appeal`, `PATCH /api/v1/instructor/guardrail-queue/{id}`) — không tự ý bỏ tính năng này vì nó đã được thiết kế đủ kỹ (UI 2 phía ăn khớp nhau), chỉ là thiếu lớp backend.

### 5.4 Reflect

**Input:** rating (great/average/challenging) + `challenge` (textarea) + `plan` (textarea).
**Gọi:** `POST /api/v1/student/reflections/generate`.
**Ràng buộc:** phản tư phải được lưu và **dùng làm ngữ cảnh cho kế hoạch tuần sau** — đây là điểm khác biệt "AI đồng hành" thật sự so với 1 form khảo sát vô tri; nếu backend chưa hỗ trợ việc này, ít nhất phải hiển thị đúng thông điệp "đã lưu, sẽ dùng cho tuần sau" như UI hiện tại đang làm (dòng 92-98), không hứa suông.

---

## 6. Lịch làm việc theo ngày (bám `03-Cursus-Execution-Plan.md` + `09-Cursus-Team-Assignment.md`)

| Ngày | Việc cụ thể | Phụ thuộc |
|---|---|---|
| **11/08 (T3, hôm nay)** | Đọc file này + `00_AI_CONTEXT_PACK.md`. Polish UI hiện tại theo checklist `docs/frontend/08_SCREEN_CONSISTENCY_CHECKLIST.md` (không cần chờ backend): thêm trạng thái Error còn thiếu ở khối Plan, kiểm tra i18n đủ 2 ngôn ngữ. | Không phụ thuộc ai |
| **12/08 (T4)** | Đăng dự kiến xong Job #0 cuối ngày. Trong lúc chờ: viết sẵn `lib/api.js` cho phần Student (dựa theo endpoint mục 5), test bằng Postman/Swagger `/docs` khi Đăng báo backend chạy | Đăng (Job #0) |
| **13/08 (T5) — mục tiêu "1 flow hoàn chỉnh"** | Nối xong F2 (generate/accept/task update) **và** F3 (qa thật, bubble chặn đúng dữ liệu backend) — đây là 2 bước đầu tiên trong luồng demo 6 bước ở `09-Team-Assignment.md` mục 4, bắt buộc chạy được trước khi Bình test tiếp phần GV | Backend chạy (Job #0 xong) |
| **14/08 (Gate 2)** | Sáng: chỉ sửa lỗi chặn demo, không code tính năng mới | — |
| **15-22/08 (Mốc 3)** | Reflect hoàn thiện nối API thật; phối hợp Đăng+Bình xây appeal flow (mục 5.3) nếu còn thời gian; rà lại toàn bộ theo `docs/frontend/08_SCREEN_CONSISTENCY_CHECKLIST.md` | |
| **23/08** | Freeze, rượt demo | — |

---

## 7. Definition of Done — trước khi báo "xong"

- [ ] Không còn `await new Promise(setTimeout(...))` giả lập nào trong `StudentHome.jsx`/`StudentReflection.jsx` — mọi loading state đến từ `fetch()` thật
- [ ] Đoạn regex guardrail tự chế ở frontend (dòng 72-75 `StudentHome.jsx`) đã bị xoá, guardrail 100% do backend quyết định
- [ ] Task/câu trả lời không có `source_label` hiển thị đúng cảnh báo, không bịa nội dung
- [ ] 4 trạng thái Loading/Empty/Success/Error đầy đủ cho cả khối Plan và khối QA
- [ ] Mọi chuỗi mới thêm có trong `locales/en.js` và `vi.js`
- [ ] Test thật câu "giải hộ em bài này" trên UI đã nối API — phải thấy bubble đỏ, không phải câu trả lời bình thường

---

## 8. Prompt mẫu — dán thẳng cho Gemini/Antigravity

```
Bạn là frontend engineer cho Cursus (React 19 + Vite + Tailwind v4, JS thuần không TS).
Tôi phụ trách role Sinh viên: F2 (lập kế hoạch tuần), F3 (hỏi-đáp có trích nguồn), Reflect.

Context bắt buộc đọc trước (tôi đã dán/đính kèm):
- docs/frontend/00_AI_CONTEXT_PACK.md (design system, token màu/spacing/motion)
- Nội dung file docs/archive/planning-v2/roles/HAIANH_student.md mục 4-5 (UI hiện có + API cần nối)

Nhiệm vụ hôm nay: [ví dụ "Nối StudentHome.jsx phần lập kế hoạch tuần vào POST /api/v1/plans/generate
thay cho đoạn giả lập setTimeout, giữ nguyên UI/state hiện có, thêm trạng thái Error còn thiếu"].

Ràng buộc bắt buộc:
- Không tự đoán/tự viết logic guardrail ở frontend — 100% dựa vào field "blocked" backend trả về.
- Không bịa citation — nếu source_label null, hiển thị đúng câu cảnh báo đã định nghĩa ở mục 5.1/5.2.
- Giữ nguyên toàn bộ class CSS/token đã có (.card, .badge, var(--accent) v.v.) — không tự đổi màu/spacing.
- Chuỗi text mới phải thêm vào frontend/src/locales/en.js và vi.js.
- Nếu thiếu thông tin (ví dụ endpoint chưa rõ shape response), hỏi lại thay vì tự bịa field.
```

---

## 9. Liên kết liên quan

[`docs/archive/planning-v2/00-Cursus-Playbook.md`](../00-Cursus-Playbook.md) F2/F3 · [`docs/frontend/03_COMPONENT_SPECIFICATIONS.md`](../../../frontend/03_COMPONENT_SPECIFICATIONS.md) (Source preview, Empty/Error state) · [`docs/archive/planning-v2/roles/BINH_instructor.md`](BINH_instructor.md) (phối hợp appeal flow) · [`docs/archive/planning-v2/roles/DANG_infra-auth-frontend.md`](DANG_infra-auth-frontend.md) (khi cần API/auth chưa sẵn sàng).
