# Outline bài thuyết trình — Cursus (10 trang)

> Đây là **outline nội dung chi tiết**, không phải slide hoàn chỉnh — thiết kế hình ảnh/layout/màu sắc do người làm (cần hình ảnh thật: screenshot, mascot Curi, sơ đồ). Toàn bộ nội dung số liệu/claim dưới đây lấy thẳng từ `docs/PROJECT_CONTEXT.md` (mục 3, 4.3, 9, 9.5, 19) — không tự thêm số liệu/claim mới. Khi build slide thật, đối chiếu lại các dòng có gắn `[Verify: ...]` bằng ảnh/log thật trong `docs/evidence/` trước khi đưa vào slide.

**Cấu trúc tổng: Vấn đề (trang 2) → Giải pháp (trang 3) → Kiến trúc (trang 4) → Demo 3 vai trò (trang 5-7) → An toàn & Eval (trang 8) → Giới hạn & hướng tiếp theo (trang 9-10).**

---

## Trang 1 — Title

- Tên dự án: **Cursus — AI Academic Companion**
- Đề tài gốc: EDU-01 "Trợ lý học tập cá nhân X", nhóm lĩnh vực A · AI Giáo dục (AI20K)
- Group06 · Team093 (P-093)
- Team: Trịnh Hải Đăng (Nhóm trưởng), Nguyễn Hải Anh, Nguyễn Anh Bình, Nguyễn Đức Chung
- 1 dòng tagline: "Người đồng hành AI theo chu trình Plan → Do → Reflect, luôn trích nguồn, không làm hộ bài, có giảng viên trong luồng"

---

## Trang 2 — Vấn đề

**Nguồn: mục 3 PROJECT_CONTEXT.md.**

- **Sinh viên:** mỗi môn có syllabus rất dài (ví dụ SSA101: 60 buổi học, 11 mục tiêu, 72 đoạn dữ liệu khi hệ thống đọc vào) — không ai gom deadline mọi môn lại theo tuần cho sinh viên xem. Không có thói quen chủ động lập kế hoạch, không có công cụ nhìn lại hiệu quả học tuần vừa qua.
- **Giảng viên:** phụ trách 40-60 sinh viên/lớp, không đủ thời gian theo dõi thủ công, không có tín hiệu sớm biết ai đang tụt lại trước khi quá trễ.
- **Phòng đào tạo (người trả tiền):** tỷ lệ SV trễ tiến độ/bỏ học ảnh hưởng kết quả khoa + chi phí hỗ trợ học thuật cao, không có công cụ tổng hợp dữ liệu tiến độ cả lớp/khoá để ra quyết định.
- Mô hình kinh doanh: **B2B2C** — trường trả phí theo SV hoạt động/tháng, SV không trả tiền trực tiếp.

---

## Trang 3 — Giải pháp: chu trình Plan → Do → Reflect

- 3 lời hứa cốt lõi (dùng đúng khi mở đầu demo — mục 19.1): **grounded** (mọi câu trả lời trích nguồn đúng tài liệu môn), **không làm hộ bài** (guardrail chặn + gợi mở thay vì đưa đáp án), **lecturer HITL** (con người quyết định can thiệp, hệ thống không tự nhắn SV).
- Plan: SV nêu mục tiêu tuần → AI chia nhỏ 4-6 task từ đúng syllabus, có estimate + nguồn.
- Do: nhắc việc, hỏi-đáp có trích nguồn, complete/defer có lý do.
- Reflect: đối thoại phản tư cuối tuần, tự đánh giá, feed thẳng vào kế hoạch tuần sau (memory xuyên tuần).
- 3 điều Cursus có mà chưa đối thủ nào có đủ cả 3 cùng lúc (mục 4.3): (1) bám sát đúng chương trình 1 trường cụ thể, (2) phản tư có cấu trúc + trí nhớ xuyên tuần, (3) dashboard giảng viên + con người quyết định.

---

## Trang 4 — Kiến trúc hệ thống

**Nguồn: `ARCHITECTURE.md` (đã cập nhật 22/08) — dùng đúng sơ đồ mermaid trong đó cho slide này, đừng vẽ lại từ trí nhớ.**

- Frontend React + Vite (Vercel) → Backend FastAPI (Railway) → Postgres (Supabase).
- Guardrail rule-based chạy **trước** mọi lệnh gọi LLM (rẻ, không tốn phí khi chặn được sớm).
- "Agent" thật là **LLM-with-fallback theo từng service** (không phải LangGraph agent-loop — route LangGraph tồn tại làm tham chiếu, không dùng trong luồng chính, ADR-012). Nói thẳng điều này nếu bị hỏi về kiến trúc multi-agent — tránh tuyên bố sai kiến trúc.
- RAG: **lexical scoring + cosine similarity thuần Python** (không pgvector/reranker thật — điểm cần nói đúng, tránh bị hỏi xoáy vào "bge-reranker" rồi không trả lời được). Vượt naive RAG ở chỗ: blend 2 tín hiệu, dedupe, bilingual query expansion.
- Mock LMS: hệ thống ngoài thật riêng biệt (app/DB/OAuth), Cursus gọi vào qua REST API — chứng minh năng lực tích hợp hệ thống ngoài mà không cần hợp tác Canvas thật.

---

## Trang 5 — Demo vai trò 1: Sinh viên (Plan → Do → Reflect)

**Kịch bản, theo mục 19.1 (0:35-4:35):**
- Mở SSA101 Group Project Part 1 → deadline/rubric có nguồn + lịch rảnh → generate plan → nhấn citation → dời 1 task, xác nhận.
- Complete 1 task, defer 1 task có lý do; hỏi câu kiến thức (có citation); hỏi "làm hộ em bài này" → guardrail chuyển sang khái niệm + câu hỏi gợi mở (không tạo deliverable).
- Reflection: hoàn thành/dời/actual time → chọn nguyên nhân + adjustment → xác nhận → Plan tuần sau thể hiện rõ ít nhất 1 thay đổi từ reflection đó.
- Dataset chuẩn dùng khi demo: SV Trịnh Hải Đăng, SE, Fall 2026 (mục 18).

---

## Trang 6 — Demo vai trò 2: Giảng viên (HITL)

**Kịch bản, theo mục 19.1 (4:35-5:35):**
- Chuyển Demo Lecturer (Cô Hương, cố vấn lớp SE-K20) → mở alert sinh viên "Nguyễn Minh" (completion 25%, 3 overdue, deadline 36h, risk score 5, evidence cụ thể — không dùng sentiment).
- Nhấn "Đã liên hệ", ghi note, đánh dấu alert hợp lệ/không hợp lệ (feedback dùng để đánh giá lại rule sau này).
- Nhấn mạnh: giảng viên chỉ thấy **lớp được Admin gán**, không xem được lớp khác (đã có test cross-instructor, [Verify: `tests/test_api/test_ownership_module.py`]); không tự động nhắn SV — con người quyết định can thiệp.

---

## Trang 7 — Demo vai trò 3: Admin (Phòng đào tạo)

- Bảng curriculum đã nạp vào hệ thống AI (44 môn syllabus thật, không phải mẫu).
- Risk Policy versioning: xem version hiện tại, preview trước khi publish, rollback có lý do bắt buộc — không sửa đè lịch sử.
- Tab Mock LMS: preview/publish/rollback đồng bộ dữ liệu từ hệ thống ngoài (Mock LMS) — mở 2 tab song song lúc demo để chứng minh đây là 2 hệ thống thật tách biệt (mục 18).
- KPI tỷ lệ nộp đúng hạn có/không dùng Cursus — nói rõ đây là **minh hoạ phương pháp đo, dữ liệu mô phỏng tĩnh**, không phải kết quả đo thật trước/sau triển khai (tránh tuyên bố quá mức, mục 2.7).

---

## Trang 8 — An toàn & Eval (PLO6, PLO7)

**Guardrail & HITL:**
- Guardrail chạy trước LLM, 2 lớp (intent-classification + rule engine DB-backed, ADR-008) — không tuyên bố "100% chặn được", báo precision/recall + failure case thật khi bị hỏi.
- Phòng thủ prompt injection (LLM07, pattern-based ở tầng prompt) + validate nội dung tài liệu trước khi embed (LLM08, flag không reject — ADR-018).
- Risk score chỉ dùng tín hiệu hành vi quan sát được, không dùng cảm xúc/nhân khẩu học, không dùng để chấm điểm/kỷ luật.

**Eval AI thật [Verify: `eval/results/report.md`, `docs/evidence/test-runs/20260822-2350-p0-5-final.xml`]:**
- Bộ eval nhỏ với Gemini thật (không phải full benchmark): 5 câu QA + 3 kịch bản Plan + 3 kịch bản Reflection = 11 lệnh gọi. Kết quả: 8/11 xác nhận `llm_success=True` thật (QA 2/5, Plan 3/3, Reflection 3/3), 2/11 model từ chối trung thực vì `insufficient_context`, 1/11 đúng thiết kế route sang extractive không cần LLM.
- `pytest tests/`: 461 passed, 7 skipped, 0 failed (toàn bộ suite, không chỉ phần eval).
- Nói rõ khi bị hỏi: đây là 1 batch nhỏ đã duyệt ngân sách API, không phải benchmark quy mô lớn.

**An ninh RBAC/IDOR — đáng nói vì tự tìm và tự vá được:**
- Tự phát hiện + vá 2 lỗ hổng IDOR thật trong quá trình audit (giảng viên xem được guardrail-review/activity log của lớp không phải mình phụ trách) — có test cross-instructor xác nhận đã đóng.
- Audit log trước đây không lọc theo tổ chức (bất kỳ Admin nào xem được audit log tổ chức khác) — đã vá đầy đủ (migration + SQL đã chạy trên DB thật, verify 420/446 dòng có organization_id).

---

## Trang 9 — Giới hạn & rủi ro (nói thẳng, không né)

**Nguồn: mục 9 P0#3, mục 12, mục 2.7 PROJECT_CONTEXT.md — chỉ liệt kê gap còn thật sự tồn tại lúc thuyết trình, kiểm tra lại trước khi dùng slide này.**

- **RLS đa tổ chức chưa bật thật** (Postgres Row Level Security có tồn tại trong migration nhưng bị bypass bởi DB role hiện tại) — cách ly tổ chức hiện dựa vào filter `organization_id` ở tầng ứng dụng, không phải tầng DB. Đây là gap bảo mật lớn nhất còn biết, nói thẳng thay vì né.
- KPI tỷ lệ nộp đúng hạn có/không Cursus là **minh hoạ mô phỏng**, chưa phải số đo thật trước/sau triển khai pilot.
- Chưa demo đa tổ chức thật (2+ trường) — có chủ đích, cơ chế multi-tenant tồn tại trong code nhưng không cần dựng tổ chức thứ 2 để trình diễn.
- Tích hợp Canvas LMS thật của 1 trường cụ thể — ngoài phạm vi đồ án (cần tư cách pháp nhân); đã thay bằng Mock LMS tự dựng (REST API, OAuth thật) để chứng minh năng lực tích hợp.
- LTI 1.3 launch đầy đủ — vẫn là stretch goal, chưa làm (chỉ có REST API baseline).
- Load test 2.500 kết nối đồng thời — nếu chưa chạy kịp trước Demo Day, nói rõ đây là việc đang làm, không tuyên bố đã đo.

---

## Trang 10 — Hướng tiếp theo & Ask

- **Bước tiếp theo ngắn hạn:** hoàn tất RLS đa tổ chức ở tầng DB thật, mở rộng quy mô eval AI (không chỉ 11 case), load test 2.500 kết nối, LTI 1.3 nếu còn thời gian sau P0/P1.
- **Bước tiếp theo dài hạn (roadmap, mục 11 PROJECT_CONTEXT.md):** AI chủ động gợi ý mục tiêu tuần dựa trên tiến độ/reflection trước; nhắc tự động 48h trước hạn; đo thật KPI tỷ lệ nộp đúng hạn với pilot thật (không phải mô phỏng); demo đa tổ chức thật.
- **Ask:** (điền theo mục đích thuyết trình cụ thể — nếu là Demo Day chấm điểm BTC, phần này có thể thay bằng "Câu hỏi thường gặp" lấy từ mục 19.2 PROJECT_CONTEXT.md thay vì "ask" kiểu gọi vốn, vì đây không phải pitch gọi đầu tư).
