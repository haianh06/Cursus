# Cursus — Execution Plan v2.3

## Thay thế toàn bộ roadmap cũ — đây là lịch trình DUY NHẤT đang áp dụng

> **11/08/2026 — phân công theo "Người A/B/C/D" bên dưới đã được thay bằng mô hình sở hữu theo role sản phẩm** (mỗi người sở hữu 1 vai trò SV/GV/Admin, nhóm trưởng sở hữu hạ tầng) — xem [`09-Cursus-Team-Assignment.md`](09-Cursus-Team-Assignment.md) để biết ai làm phần nào, có gắn cụ thể vào từng ngày trong bảng lịch dưới đây. **Ngày/mục tiêu/checklist trong file này vẫn là khung thời gian chính thức, không đổi.**

**Hôm nay:** 10/08/2026 (Thứ Hai) · **Deadline nộp bài cuối cùng: 23/08/2026 (13 ngày nữa).**

> **Mục tiêu Gate 2 đã nâng lên theo đúng yêu cầu: đạt ~60% toàn bộ dự án vào 14/08** — dựa trên việc team đã có kinh nghiệm làm những phần này trước đây, không phải ước lượng thận trọng mặc định nữa. Cách làm: dồn phần lớn danh sách từng dự kiến cho "Giai đoạn 3A" (Reflect, Reranker, Guardrail nâng cấp, Dashboard GV, Sentry, RAGAS, kịch bản lỗi, hồ sơ bàn giao) vào thẳng Gate 2. Mốc 3 (15→23/08) giờ chỉ còn phần hoàn thiện cuối (Auth 3 role thật, Admin Console đầy đủ, mở rộng ingest, RAGAS/guardrail đạt ngưỡng đầy đủ, LLM-as-Judge, load test thật).

```
09/08 (hôm nay) ──► 10 ──► 11 ──► 12 ──► 13 ──► 14/08 (GATE 2 — ~60% dự án) ──► 15...22 (Mốc 3) ──► 23/08 (NỘP BÀI, 100%)
```

---

> **Việc chặn cần xử lý trước — xác nhận thật 10/08/2026:** branch `haidang2425` (đang review docs) tụt lại phía sau `chung`/`develop` — phần lớn backend (auth/RBAC/JWT, Gemini QA service, Admin Console F6/F7) đã có sẵn trên `chung`, chưa merge. Nhóm trưởng cần merge branch tích hợp chính **trước khi** phân công tiếp việc bên dưới, nếu không rủi ro 2 người code trùng phần đã có. Xem `01-Cursus-PRD.md` mục 11 (risk register) và `08-Cursus-Deliverables-Checklist.md` mục 1 dòng "Source Code".

## GATE 2 — 14/08/2026 (5 ngày) — MỤC TIÊU: ~60% DỰ ÁN, ĐỦ "CƠ BẢN" + PHẦN LỚN "NÂNG CAO"

### Toàn bộ việc bắt buộc có tới 14/08

| # | Việc | FR/Epic liên quan | Vì sao ở Gate 2 |
|---|---|---|---|
| 1 | **Login (F1) đạt chuẩn UX** — tối đa 2 bước, có loading state, xử lý lỗi API rõ ràng, chuyển đúng màn theo role | FR-1.1, `00` PHẦN 1B | Đây là điểm chạm đầu tiên của mentor/giám khảo — phải mượt ngay từ Gate 2, không "tạm chạy được" |
| 2 | Ingest tối thiểu 3 môn (SSA101 đã có sẵn) | FR-2.1 | Đủ dữ liệu thật cho toàn bộ luồng bên dưới |
| 3 | Luồng Plan hoàn chỉnh: nhập mục tiêu → nhận task có trích nguồn → sửa/xoá task | FR-3.1, FR-3.2 | Luồng lõi 1 |
| 4 | Luồng Q&A: hỏi hợp lệ có trích nguồn | FR-4.1 | Luồng lõi 2 |
| 5 | **Reranker vào pipeline retrieval** (Plan + Q&A) | FR-3.1/4.1, `02-SRS.md` mục 1.4 | Điều kiện PLO3 "vượt naive RAG" — làm ngay từ đầu, không vá sau |
| 6 | **Guardrail rule-based + nâng LLM classifier + test suite ≥20 case** | FR-5.1, FR-9.3 | Điểm khác biệt cạnh tranh chính, PLO6 |
| 7 | **Reflect đầy đủ** (Plan → Do → Reflect trọn vòng) | `02-SRS.md` mục 3.6 | 1 trong 3 yếu tố định vị cốt lõi (PRD mục 4) |
| 8 | **Dashboard GV có logic thật + HITL** | E7 (FR-7.1-7.3) | Bắt buộc để đạt "Cơ bản" đúng đề bài EDU-01 mục 3.1 |
| 9 | **UI hoàn thiện đúng chuẩn** (SV + GV) — nâng chất lượng thị giác theo checklist `00` PHẦN 1B (4 trạng thái, không placeholder, responsive, dark mode, không lỗi console). **Trước khi làm: merge branch `chung`/`develop` vào `haidang2425` (đang chưa merge, xác nhận thật 10/08/2026) rồi viết lại `docs/project/structure-team.md` mục 2.1 — mô tả `types.ts`/`demo-service.ts` cũ đã lỗi thời, frontend thật hiện tại là Vite/JSX thuần** | `00` PHẦN 1B | Mentor ưu tiên nhìn thấy phần này hoàn thiện ngay từ đầu — nhưng phải code trên đúng nền code mới nhất của team, không phải nền cũ đã bị bỏ |
| 10 | **Mock/seed data kiểm chứng toàn bộ** — chạy hết kịch bản demo chính + lỗi trên dữ liệu seed thật, xác nhận không state nào vỡ | `00` PHẦN 1B (mục Mock/seed data) | Chứng minh sản phẩm hoạt động ổn định thật, không chỉ "trông có vẻ chạy" |
| 11 | **Sentry + structured logging** | NFR-10 | Rẻ, ~30 phút setup, điểm cộng Quy định chung mục 4 |
| 12 | **RAGAS 10-15 câu + báo cáo** | FR-9.1 | Số liệu thật cho phần eval |
| 13 | **Kịch bản demo lỗi tập rượt** | `00` PHẦN 5B | Bắt buộc theo Quy định chung mục 4 |
| 14 | **Bản đầu deliverable BTC** (README.md, Architecture Diagram, xác nhận AI Logs hoạt động) | `08-Cursus-Deliverables-Checklist.md` | Càng chuẩn bị sớm càng đỡ gấp cuối |
| 15 | Deploy online có URL truy cập được (Vercel + Railway + Supabase) | — | "Chạy trên máy tôi" không tính là xong |

### Lịch theo ngày (5 ngày, chia việc song song theo 4 vai trò — điều chỉnh theo số người thật)

| Ngày | Người A (Backend) | Người B (RAG/AI) | Người C (Frontend) | Người D (PM/QA) |
|---|---|---|---|---|
| **09/08 (CN)** | Setup Supabase (pgvector bật ngay) + Railway + repo (clone từ BTC, thêm remote riêng — `06` mục 0.2). Khung FastAPI, F1 demo-login. | Xác nhận `chunks_SSA101.json`, chuẩn bị embedding qua Gemini (`gemini-embedding-001`, cắt 768 chiều bằng MRL — xem `02-SRS.md` mục 3.2). | Setup Vercel, scaffold Next.js, dựng khung 2 màn (SV + GV). **Mua domain** (`06` mục 0.5), trỏ DNS về Vercel. | Chuẩn bị thêm dữ liệu môn nếu cần, theo dõi tiến độ. |
| **10/08 (T2)** | F2 Plan end-to-end, validate `source_chunk_id`. | Viết Planner logic + tích hợp reranker (`bge-reranker-v2-m3`). | UI Student Home: khu vực nhập mục tiêu + task list. | Soạn danh sách pattern guardrail rule-based. |
| **11/08 (T3)** | F3 Q&A + Guardrail rule-based, bắt đầu nâng LLM classifier. | Reranker cho Q&A; bắt đầu viết 20+ test case guardrail. | UI Q&A chat; nối FE-BE thật (bỏ mock). | Soạn golden dataset RAGAS (10-15 câu). |
| **12/08 (T4)** | Backend Reflect (FR-6.1-6.4) — API start/answer/summary. | Prompt tóm tắt Reflect + guardrail LLM classifier hoàn thiện, chạy test suite. | UI Reflect (đối thoại tuần tự) + UI Dashboard GV (biểu đồ + alert list). | Setup Sentry (BE+FE). Bắt đầu soạn hồ sơ bàn giao. |
| **13/08 (T5)** | Deploy toàn bộ (Vercel+Railway+Supabase), nối domain nếu có. Sửa lỗi deploy (env var, CORS). | Chạy RAGAS, xuất báo cáo. Hỗ trợ sửa lỗi retrieval nếu có. | Polish UI theo đúng checklist `00` PHẦN 1B (4 trạng thái, không placeholder, responsive). | **Chủ trì kiểm chứng mock/seed data**: chạy hết 8 bước kịch bản demo chính (`00` Phần 5) trên dữ liệu seed thật, đối chiếu số liệu đúng file JSON gốc, ghi lại bug nếu có. |
| **14/08 (T6 — Gate 2)** | Sáng: dừng code mới, chỉ sửa lỗi chặn demo. | Cùng A sửa lỗi cuối. | Cùng A sửa lỗi UI cuối, kiểm tra lại không lỗi console. | Chủ trì rượt kịch bản demo chính + lỗi (`00` PHẦN 5, 5B) lần cuối, chuẩn bị câu trả lời dự kiến (`05` mục 4). |

### Nếu tiến độ chậm — không cắt, chỉ đổi thứ tự ưu tiên
Nếu tới 12/08 vẫn chưa xong việc #1-#6 (login + luồng lõi + reranker + guardrail): tạm dừng việc #7-#14 (Reflect, Dashboard, UI polish, mock data, Sentry, RAGAS, kịch bản lỗi, hồ sơ), dồn lực hoàn thành #1-#6 + deploy (#15) trước — đây là mức sàn tuyệt đối không được thiếu. Các việc bị dừng dời sang đầu Mốc 3, không huỷ bỏ. **Login (#1) và UI cơ bản không nằm trong danh sách có thể dời** — đây là 2 việc mentor nhìn đầu tiên, luôn phải xong cùng luồng lõi.

### Checklist trước Gate 2
- [ ] Login đạt chuẩn UX (`00` PHẦN 1B) — mượt, có loading state, xử lý lỗi rõ, chuyển đúng màn theo role
- [ ] Luồng Plan + Q&A (có reranker) chạy trên bản deploy thật, không lỗi
- [ ] Guardrail (rule-based + LLM classifier) chặn đúng, test suite ≥20 case có số liệu thật
- [ ] Reflect chạy trọn vòng Plan-Do-Reflect trên bản deploy thật
- [ ] Dashboard GV có logic thật + nút "Đánh dấu đã can thiệp" hoạt động
- [ ] UI SV + GV đạt đủ checklist ở `00` PHẦN 1B (4 trạng thái, không placeholder, responsive, không lỗi console) — không phải bản cũ chưa đạt chuẩn
- [ ] Mock/seed data đã kiểm chứng: chạy hết kịch bản demo chính + lỗi trên dữ liệu seed thật, số liệu khớp đúng file JSON gốc
- [ ] Sentry bắt được lỗi thật khi test
- [ ] RAGAS có báo cáo số liệu cụ thể (10-15 câu)
- [ ] Kịch bản demo lỗi đã tập rượt
- [ ] Có URL deploy truy cập được từ máy khác

---

## MỐC 3 — Hoàn thiện cuối cùng, 23/08/2026 (9 ngày sau Gate 2) — phần còn lại để đạt 100%

> Nếu Gate 2 đạt đúng ~60% như kế hoạch, Mốc 3 chỉ còn phần "làm cho đầy đủ, mở rộng quy mô" — không còn tính năng lõi nào phải dựng từ đầu.

| Việc | Nội dung đầy đủ | FR/Ghi chú |
|---|---|---|
| **Auth 3 role thật** | Form đăng ký/đăng nhập email+mật khẩu qua Supabase Auth, thay hẳn demo-login | FR-1.1 |
| **Admin Console đầy đủ** | CRUD ingest qua UI (thêm/xoá tài liệu), KPI tổng hợp toàn khoá | FR-8.1/8.2 (E8) |
| **Ingest mở rộng ~10 môn** | Ưu tiên năm 1-2, sau đó năm 3-4 theo risk register PRD mục 11 | |
| **RAGAS mở rộng 15-20 câu** (từ 10-15 câu Gate 2) | Có thể tiếp tục lên 30-50 câu | FR-9.1 |
| **Guardrail test suite đạt ≥90% cả 2 chỉ tiêu** | Tinh chỉnh threshold/prompt classifier nếu Gate 2 chưa đạt | FR-9.3 |
| **LLM-as-Judge cho Reflect** | Chạy đầy đủ trên ≥10 phiên mẫu, có báo cáo điểm | FR-9.4 |
| **Kiến trúc chịu tải 6 lớp** (API key rotation, rate limiting, cache, circuit breaker, connection pooling, hàng đợi nếu cần) | Xem chi tiết `02-SRS.md` mục 4.2 — làm TRƯỚC load test, không thì test chỉ đo ra "sập ở đâu" | Điều kiện để load test dưới đây có ý nghĩa |
| **Load test thật đủ 2.500 concurrent** | Dùng k6 (free, giả lập 2.500 người dùng ảo từ 1 máy chạy test, không cần 2.500 máy thật) bắn thẳng vào endpoint Plan/Q&A trên bản deploy thật, sau khi đã có kiến trúc chịu tải ở trên. Tạm nâng gói Gemini trả phí đúng khung giờ test (ngân sách `06` mục 2.2) để không bị rate-limit sai lệch kết quả | NFR-1c — số đo thật, vượt xa yêu cầu gốc đề bài (1.000) |
| **Notification/reminder 48h** | Job scheduler quét deadline, nhắc SV in-app | FR-4.2 |
| **Mock LMS API** (Should, nếu dư giờ) | Bọc dữ liệu FLM đã ingest thành 1 API nội bộ, nâng câu chuyện tích hợp Canvas/LTI — xem `02-SRS.md` FR-2.3 | ~0.5-1 ngày, không chặn nộp bài nếu chưa kịp |
| **Đủ 10/10 deliverable BTC yêu cầu** (Pitch Deck, Video Demo, JOURNAL.md, WORKLOG.md, eval report...) | Bổ sung từ bản đầu ở Gate 2, nhắm thang điểm ≥35/50 | `08-Cursus-Deliverables-Checklist.md` |

### Lịch theo ngày (15/08 → 23/08, 9 ngày, linh hoạt theo tiến độ Gate 2 thật)

| Ngày | Việc trọng tâm |
|---|---|
| **15-16/08** | Auth 3 role thật + Admin Console (CRUD ingest, KPI). |
| **17/08** | Ingest mở rộng ~10 môn. |
| **18/08** | Tinh chỉnh Guardrail tới ≥90%; RAGAS mở rộng 15-20 câu. |
| **19/08** | LLM-as-Judge chạy đầy đủ; **bắt đầu xây kiến trúc chịu tải** (`02-SRS.md` mục 4.2): tạo 5-10 API key Gemini + code round-robin, bật PgBouncer Supabase, nối circuit breaker vào fallback OpenAI đã có. |
| **20/08** | Hoàn thiện kiến trúc chịu tải (cache + hàng đợi nếu cần); chạy thử k6 ở mức thấp trước (200-500 concurrent) để kiểm tra không lỗi trước khi lên full scale. |
| **21/08** | **Load test thật đủ 2.500 concurrent bằng k6**, nâng gói Gemini trả phí đúng khung giờ test; xuất báo cáo P95 latency + tỷ lệ lỗi. Notification 48h. |
| **22/08** | Hoàn thiện đủ 10/10 deliverable (Pitch Deck, JOURNAL.md, WORKLOG.md, eval report); buffer sửa lỗi. |
| **23/08 (NỘP BÀI)** | Sáng: freeze code, rượt kịch bản demo (chính + lỗi) lần cuối. Chiều: nộp bài. |

---

*Đọc cùng `01-Cursus-PRD.md` (phạm vi, đã đồng bộ mục 8.1/8.2) và `02-Cursus-SRS.md` (đặc tả kỹ thuật, đã đồng bộ Definition of Done mục 6).*
