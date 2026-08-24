# Cursus — AI Academic Companion

## Product Requirements Document (PRD) — v2.0 (đồng bộ 07/08/2026)

|                          |                                                                                                            |
| ------------------------ | ---------------------------------------------------------------------------------------------------------- |
| **Đề tài gốc** | EDU-01 — AI Learning Companion                                                                            |
| **Nhóm**          | Group06 ·**Team** Team093                                                                           |
| **Nhóm trưởng** | Trịnh Hải Đăng                                                                                         |
| **Thành viên**   | Nguyễn Hải Anh · Nguyễn Anh Bình · Nguyễn Đức Chung                                               |
| **Đối tượng**  | Sinh viên ngành SE (Software Engineering), FPT University, curriculum BIT_SE_K20D_K21A, toàn bộ 4 năm |
| **Trạng thái**   | v2.0 — bản chốt, thay thế mọi bản trước (kể cả bản ghi "3 tuần" và bản ghi "StudyMate X")    |

> **v2.0 thay đổi gì so với v1.0:** (1) chốt cứng 1 tên sản phẩm — **Cursus**; (2) chốt cứng timeline thật theo mốc; (3) MVP Scope viết lại theo MoSCoW gắn với từng mốc, không còn "Must" tràn lan; (4) sửa mâu thuẫn NFR tải hệ thống vs KPI 1.000 SV; (5) cập nhật Value Proposition theo dữ liệu cạnh tranh mới nhất; (6) đưa Business Model Canvas vào chính PRD thay vì nằm rời ở file kế hoạch.

---

## 1. Document Control

Đây là nguồn tham chiếu **duy nhất** cho phạm vi tính năng. Tài liệu kỹ thuật đi kèm: `02-Cursus-SRS.md` (đặc tả chức năng), `03-Cursus-Execution-Plan.md` (lịch trình theo mốc — dùng file này để biết "hôm nay làm gì"), `04-Cursus-Terminology.md` (thuật ngữ), `05-Cursus-Competitive-Analysis.md` (đối thủ, cập nhật mới nhất).

---

## 2. Executive Summary

**Cursus** là AI academic companion giúp sinh viên SE tự quản lý việc học theo chu trình **Plan → Do → Reflect**, grounded trên curriculum thật của FPT (BIT_SE_K20D_K21A), có guardrail chống làm hộ bài, và có dashboard cho giảng viên can thiệp sớm với HITL.

**Bài toán kinh doanh:** SV SE đăng ký nhiều môn song song, deadline/CLO nằm rải trong hàng chục syllabus dài; không có công cụ tổng hợp theo tuần, không có cơ chế tự phản tư, và nhà trường không có tín hiệu sớm để hỗ trợ SV trước khi trễ hạn/bỏ học.

**Giải pháp:** hệ thống agent có trạng thái (không phải chatbot hỏi-đáp), grounded trên dữ liệu FLM thật đã ingest, guardrail liêm chính học thuật, KPI đo được cụ thể.

---

## 3. Problem Statement

### 3.1. Sinh viên

- Syllabus mỗi môn dài (SSA101: 60 session, 11 CLO, nhiều mốc deadline), không có nơi tổng hợp theo tuần. (Sau khi ingest, `flm_parser.py` tách SSA101 thành 72 chunk — nhiều hơn 60 vì mỗi CLO và phần Overview/Grading cũng là 1 chunk riêng, không phải 1 chunk/session; xem `04-Cursus-Terminology.md` PHẦN A.2.)
- Không có thói quen lập kế hoạch chủ động.
- Không có công cụ giúp nhìn lại hiệu quả học tập hàng tuần.

### 3.2. Giảng viên

- Không có tín hiệu sớm về SV đang tụt lại.
- Không đủ thời gian theo dõi thủ công từng SV trong lớp 40-60 người.

### 3.3. Tổ chức (Phòng Đào tạo — người mua tiềm năng)

- Tỷ lệ SV trễ tiến độ/bỏ học ảnh hưởng KPI khoa, chi phí academic support cao.
- Không có công cụ tổng hợp dữ liệu tiến độ theo lớp/khoá.

---

## 4. Value Proposition & vị trí cạnh tranh (cập nhật 07/08/2026)

> Cập nhật dựa trên `05-Cursus-Competitive-Analysis.md` — đã đối chiếu với dữ liệu đối thủ mới nhất (Canvas IgniteAI Agent, Shovel, AI Hay), thay cho tuyên bố cũ "chưa ai làm" (không còn chính xác).

Cursus **không tuyên bố** là sản phẩm duy nhất làm planner AI hay hỏi-đáp grounded — cả hai thứ đó thị trường đã có (DormWay, Shovel, NotebookLM, AI Hay). Cursus định vị ở **giao điểm 3 yếu tố mà chưa đối thủ nào có cả 3 cùng lúc**:

1. Grounded trên **đúng curriculum của 1 trường cụ thể** (không phải tài liệu SV tự upload).
2. Vòng lặp **Reflect có cấu trúc, có memory xuyên tuần**, không chỉ analytics.
3. **Dashboard giảng viên + HITL** biến sản phẩm từ app cá nhân thành công cụ B2B2C bán được cho nhà trường.

**Rủi ro cạnh tranh cần nêu khi pitch (không né tránh):** Canvas IgniteAI Agent (Instructure) là đối thủ nguy hiểm nhất về cấu trúc — nếu Instructure mở rộng agent xuống phía SV, phạm vi tồn tại của Cursus bị thu hẹp. Câu trả lời khi bị hỏi: *"IgniteAI hiện hướng tới giảng viên/quản trị, chưa có companion cá nhân cấp SV, chưa có time-blocking hay reflect có cấu trúc — và quan trọng hơn, phụ thuộc hoàn toàn vào việc trường có mua Canvas hay không. FPT không dùng Canvas."* AI Hay là rủi ro về **phân phối** (đã có deal với chính FPT University) chứ không phải tính năng — Cursus không cạnh tranh ở "hỏi đáp nhanh", mà ở "quản trị cả học kỳ có workflow", phần AI Hay không làm.

---

## 5. Business Model Canvas (rút gọn)

| Khối             | Nội dung                                                                                                               |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Customer Segments | SV SE FPT (người dùng chính) · Giảng viên/cố vấn (người dùng phụ) · Phòng Đào tạo (người mua B2B2C) |
| Value Proposition | Xem mục 4                                                                                                              |
| Channels          | Web app (không cần LTI thật ở giai đoạn demo); định hướng nhúng LTI 1.3 vào FLM khi thương mại hoá      |
| Revenue Streams   | B2B2C — trường trả phí license theo số SV hoạt động/tháng, không thu phí SV trực tiếp                     |
| Key Resources     | Curriculum FLM đã ingest, embedding index, LLM API, đội vận hành guardrail/eval                                   |
| Key Partners      | Phòng Đào tạo FPT (định nghĩa ngưỡng rủi ro), nhà cung cấp LLM                                              |
| Cost Structure    | Token LLM, hosting vector DB, chi phí duy trì re-index khi syllabus đổi                                             |

**ROI story khi pitch:** "Nếu tỷ lệ nộp đúng hạn tăng X%, số SV cần academic intervention giảm → tiết kiệm giờ cố vấn/tháng → chi phí license < chi phí đó."

---

## 6. Mục tiêu & Success Metrics

| Mục tiêu                                                                                                          | KPI                                                                                                                                                                                       | Cách đo trong demo                                                                                                                                                                                                                     |
| ------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tăng tỷ lệ hoàn thành đúng hạn                                                                              | % nhiệm vụ tuần hoàn thành đúng deadline                                                                                                                                           | So sánh 2 kịch bản mô phỏng độc lập (có Cursus / không có Cursus) trên**cùng bộ SV giả lập nhưng sinh hành vi bằng 2 quy trình tách biệt**, không dùng chung 1 nguồn ngẫu nhiên, để tránh thiên vị |
| Chất lượng tự phản tư                                                                                         | Số phiên reflect hoàn thành/tuần + LLM-as-Judge chấm chiều sâu                                                                                                                    | Test trên tập dialogue mẫu                                                                                                                                                                                                            |
| Giảng viên phát hiện sớm                                                                                       | Thời gian từ "có dấu hiệu trễ" đến "GV nhận cảnh báo"                                                                                                                          | Kịch bản giả lập: SV bỏ lỡ 2 deadline liên tiếp → đo độ trễ tới khi lên dashboard                                                                                                                                         |
| Chất lượng RAG                                                                                                   | Faithfulness, answer relevancy (RAGAS)                                                                                                                                                    | Golden dataset: 10-15 câu ở Gate 2, mở rộng 15-20 câu ở Mốc 3 (xem`03` mục Mốc 3)                                                                                                                                             |
| Chặn "làm hộ bài"                                                                                               | % test case guardrail bị chặn đúng                                                                                                                                                    | Bộ 20+ câu tấn công (bao gồm biến thể gián tiếp)                                                                                                                                                                                |
| Chi phí & độ trễ ở quy mô 1.000 SV (dân số)**+ 1.000 SV đồng thời (đúng chữ đề bài EDU-01)** | Chi phí token/SV/tuần + P95 latency —**2 con số tách riêng**: (a) ngoại suy dân số 1.000 SV dùng trong 1 kỳ, (b) **đo thật** 2.500 concurrent bằng k6 ở Mốc 3 | (a) ngoại suy có công thức từ NFR-1 (`02-SRS.md` NFR-1b), trình bày là ước tính có phương pháp; (b) **NFR-1c — số đo thật bằng k6**, không phải ước tính                                                |

> Dòng cuối chính là bản sửa cho mâu thuẫn "NFR-1 nói <20 request nhưng KPI nói 1.000 SV" — từ nay 2 con số này **luôn đi kèm nhau**, không tách rời: NFR-1 (SRS) mô tả tải *thật đo được*, dòng KPI này mô tả *cách ngoại suy*.
>
> **1.000 SV (dân số) vs 1.000 SV đồng thời (concurrent) vs 2.000 người dùng (headroom) — 3 khái niệm khác nhau, hay bị nhầm lẫn khi pitch:**
>
> - `06-Cursus-Ha-tang-Supabase-Scale2000.md` mục 3 đánh giá hạ tầng ở mốc 2.000 người — đây là **bài kiểm tra dư địa hạ tầng** (infra headroom), KHÔNG phải mục tiêu KPI chính thức.
> - **1.000 SV (dân số)** ở dòng KPI này là con số cam kết dùng khi báo cáo tỷ lệ hoàn thành/chi phí trung bình.
> - **1.000 SV đồng thời (concurrent)** là chữ chính xác đề bài EDU-01 dùng ("kiểm soát chi phí/độ trễ token cho quy mô 1.000 SV dùng đồng thời") — đây là con số **khác hẳn** dân số, xem công thức ước tính riêng ở NFR-1c. Khi giám khảo hỏi thẳng theo đúng chữ đề bài, phải trả lời bằng NFR-1c, không phải NFR-1b.

---

## 7. Personas

**Persona 1 — "Đăng", SV năm 2 SE (primary):** đăng ký 6 môn/kỳ, từng trễ đồ án vì deadline "chôn" trong syllabus PDF dài. JTBD: *"Giúp em biết chính xác tuần này cần làm gì."*

**Persona 2 — "Minh", SV năm 4 SE (secondary — bổ sung để phủ toàn bộ 4 năm):** đang làm SE_GRA_ELE (đồ án tốt nghiệp) + OJT, nhịp học khác hẳn năm 1-2 (ít session cố định hơn, nhiều mốc milestone đồ án hơn). JTBD: *"Nhắc em các mốc nộp đồ án, không phải nhắc deadline bài tập thường."*

**Persona 3 — "Cô Hương", Giảng viên/cố vấn:** phụ trách 60 SV. JTBD: *"Cho tôi danh sách ưu tiên SV cần chú ý, đừng bắt tôi đọc dữ liệu thô."*

**Persona 4 — "Thầy Nam", Phòng Đào tạo (Admin — người mua):** quan tâm tỷ lệ hoàn thành toàn khoá. JTBD: *"Cho tôi thấy con số chứng minh công cụ này giảm tỷ lệ trễ hạn/bỏ học."*

---

## 8. Phạm vi (Scope) — theo 2 mốc thật (Gate 2 và Mốc 3)

> Lịch trình chi tiết từng ngày nằm ở `03-Cursus-Execution-Plan.md`. Bảng dưới đây chỉ chốt **cái gì thuộc mốc nào**.

### 8.1. Gate 2 — 14/08/2026 (5 ngày kể từ 09/08) — mục tiêu ~60% dự án, đủ "Cơ bản" + phần lớn "Nâng cao"

> Team tự tin đạt tốc độ này vì đã có kinh nghiệm làm những phần dưới đây trước đó. Chi tiết lịch theo ngày (chia theo 4 vai trò) xem `03-Cursus-Execution-Plan.md`.

**Must:**

- **Login đạt chuẩn UX** (không chỉ "chạy được") — tối đa 2 bước, loading state rõ, xử lý lỗi API, chuyển đúng màn theo role. Xem checklist đầy đủ ở `00-Cursus-Playbook.md` PHẦN 1B.
- Ingest tối thiểu 3 môn (SSA101 đã có sẵn).
- Luồng Plan: SV nhập mục tiêu tuần → AI trả 3-7 task có trích nguồn từ chunk đã ingest.
- Luồng Q&A: câu hỏi hợp lệ → trả lời có citation.
- **Reranker trong pipeline retrieval** (Plan + Q&A) — điều kiện PLO3 ("vượt naive RAG"), làm ngay từ Gate 2 chứ không vá sau.
- **Guardrail rule-based + nâng LLM classifier + test suite ≥20 case** — điểm khác biệt cạnh tranh chính (PRD mục 4), PLO6.
- **Reflect đầy đủ** theo đặc tả `02-SRS.md` mục 3.6 — 1 trong 3 yếu tố định vị cốt lõi, trọn vòng Plan-Do-Reflect ngay từ Gate 2.
- **Dashboard GV có logic thật + HITL flow duyệt alert** (E7) — bắt buộc để đạt "Cơ bản" đúng theo đề bài EDU-01 mục 3.1.
- **UI SV + GV hoàn thiện đúng chuẩn** — nâng chất lượng thị giác theo checklist ở `00-Cursus-Playbook.md` PHẦN 1B (đủ 4 trạng thái, không placeholder, responsive, dark mode, không lỗi console). **Cảnh báo cập nhật 10/08/2026 — gỡ tham chiếu sai:** bản trước ghi "tái dùng type contract + `types.ts`/`demo-service.ts` từ `frontend/` prototype" theo `docs/project/structure-team.md` mục 2.1 — mô tả đó là **prototype Next.js cũ đã không còn khớp thực tế**. Kiểm tra thật ngày 10/08/2026 cho thấy branch `haidang2425` hiện có frontend Vite/JSX thuần (không TypeScript, không `types.ts`/`demo-service.ts`), còn phần backend/RBAC/Gemini/Admin Console đầy đủ nhất đang nằm trên branch `chung`/`develop`, **chưa merge**. Trước khi Người C code UI theo mục này, bắt buộc: (1) xác nhận với team branch nào sẽ là gốc hợp nhất, (2) merge xong rồi mới viết lại `docs/project/structure-team.md` mục 2.1 cho khớp cấu trúc frontend thật, (3) khi đó mới áp dụng lại nguyên tắc "tái dùng cấu trúc đã có, không viết lại từ 0" — nguyên tắc vẫn đúng, chỉ là "cái đã có" cần xác định lại cho đúng. **Ưu tiên cao nhất theo yêu cầu trực tiếp: mentor thích mọi thứ hoàn thiện nhất ngay từ đầu.**
- **Mock/seed data đã kiểm chứng toàn bộ** — chạy hết kịch bản demo chính (`00` PHẦN 5) + kịch bản lỗi (PHẦN 5B) trên dữ liệu seed thật, đối chiếu số liệu đúng file JSON gốc, do Người D (PM/QA) chủ trì kiểm tra độc lập.
- **Sentry + structured logging** (NFR-10).
- **RAGAS 10-15 câu + báo cáo** (FR-9.1).
- **1 kịch bản demo lỗi độc lập** — xem `00-Cursus-Playbook.md` PHẦN 5B, đáp ứng Quy định chung mục 4.
- **Bản đầu các deliverable BTC yêu cầu** (README.md, Architecture Diagram, AI Logs xác nhận hoạt động — xem `08-Cursus-Deliverables-Checklist.md` cho danh sách đầy đủ 10 deliverable + thang điểm).
- Deploy online thật (có URL truy cập được).

**Should (làm nếu dư thời gian):** Redis cache, Auth 3 role thật, Admin console dạng form đơn giản.

### 8.2. Mốc 3 — Hoàn thiện cuối cùng, 23/08/2026 (9 ngày sau Gate 2) — phần còn lại để đạt 100%

> Nếu Gate 2 đạt đúng kế hoạch (~60%), Mốc 3 chỉ còn phần mở rộng quy mô/hoàn thiện, không còn tính năng lõi nào phải dựng từ đầu. Chi tiết lịch theo ngày xem `03-Cursus-Execution-Plan.md`.

**Must:**

- ~~Auth 3 role thật (form email+mật khẩu qua Supabase Auth, thay hẳn demo-login)~~ — **ĐÃ XONG sớm hơn kế hoạch (12/08/2026), và đổi hướng:** không làm form tự đăng ký công khai cho 3 role như dự kiến ban đầu — thay bằng invite-only (Admin mời qua `/admin/invites`, kích hoạt ở `/accept-invite`) + sandbox demo riêng tại `/demo/select-role` (tổ chức cô lập "Cursus Demo University", không phải flag mô phỏng). Lý do đổi hướng + chi tiết: `docs/decisions/ADR.md` ADR-007, `docs/archive/planning-v2/10-Cursus-Auth-Onboarding-Sandbox-Spec.md`.
- **FR-1.3 — API xoá dữ liệu cá nhân theo yêu cầu** (`02-Cursus-SRS.md` mục 3.1) — thực thi thật cam kết FERPA-mindset ở mục 3 (Problem Statement)/ràng buộc đề bài EDU-01, không chỉ nói ở docs.
- Admin Console đầy đủ CRUD (thêm/xoá tài liệu qua UI, KPI tổng hợp toàn khoá).
- Ingest mở rộng ~10 môn (ưu tiên năm 1-2), rồi tiếp năm 3-4 theo risk register mục 11.
- RAGAS mở rộng 15-20 câu (từ 10-15 câu Gate 2), có thể tiếp tục lên 30-50 câu.
- Guardrail test suite tinh chỉnh tới khi đạt ≥90% cả 2 chỉ tiêu (nếu Gate 2 chưa đạt).
- LLM-as-Judge cho Reflect chạy đầy đủ trên ≥10 phiên mẫu (FR-9.4).
- Load test thật đủ 2.500 concurrent bằng k6, có kiến trúc chịu tải 6 lớp sẵn sàng trước (`02-SRS.md` mục 4.2, dùng ngân sách hạ tầng đã có — `06` mục 2.2, nâng gói Gemini trả phí tạm thời trong lúc test).
- Notification/reminder 48h (FR-4.2).
- Hoàn thiện đầy đủ 10/10 deliverable BTC yêu cầu (xem `08-Cursus-Deliverables-Checklist.md`), nhắm thang điểm ≥35/50.

**Should:** Redis cache, Google OAuth thật, **Mock LMS API** (`02-SRS.md` FR-2.3 — nâng câu chuyện tích hợp Canvas/LTI, dữ liệu thật qua lớp API thay vì đọc file tĩnh, ~0.5-1 ngày), các mục còn lại nếu dư nguồn lực.

**Won't (ghi rõ là "hướng phát triển dài hạn", không build kể cả với Mock LMS API):** SSO/đăng nhập liên thông thật của LTI 1.3, tích hợp Canvas API thật (cần tư cách pháp nhân + tích hợp trường thật, ngoài tầm 1 đồ án), đa ngôn ngữ, mobile app native, billing thật, multi-region deploy.

> **Đánh giá trung thực với đề bài EDU-01:** nếu hoàn thành đúng kế hoạch Gate 2 + Mốc 3, sản phẩm đạt **"Cơ bản" đầy đủ + gần trọn "Nâng cao"** — phần duy nhất không đạt được (Canvas/LTI thật) là quyết định có chủ đích, không phải thiếu năng lực.

### 8.3. Giả định (Assumptions — cần xác nhận nếu có thời gian hỏi lại BTC)

- Giám khảo Gate 2 chấp nhận mock data FLM thay Canvas thật (đã có cơ sở từ đề bài, nhưng chưa có xác nhận trực tiếp bằng văn bản từ BTC).
- ~~Repo BTC cấp có bắt buộc deploy trực tiếp từ đó không~~ — **đã hỏi và xác nhận: KHÔNG bắt buộc.** Nhưng team **không dùng chiến lược 2 remote** (đảo quyết định 11/08/2026, xem `ADR-003` trong `docs/decisions/ADR.md`) — chỉ giữ 1 remote (repo BTC), migration/deploy chạy CLI thủ công, xem `06-Cursus-Ha-tang-Supabase-Scale2000.md` mục 0.7.
- Đối tượng thu hẹp "chỉ SE, chỉ FPT" được chấp nhận dù đề bài viết chung "Trường đại học X".

---

## 9. Danh sách tính năng (Feature Epics) — mapping PLO + mốc

| Epic                               | Mô tả                                            | PLO              | Mốc bắt buộc                                                                                  |
| ---------------------------------- | -------------------------------------------------- | ---------------- | ------------------------------------------------------------------------------------------------ |
| E1 — Auth & Role                  | Đăng nhập, phân quyền 3 role                  | PLO5, PLO6       | Gate 2 (demo-login) → **Đã xong 12/08:** invite-only + sandbox riêng, không phải form tự đăng ký (`ADR-007`, `10-Cursus-Auth-Onboarding-Sandbox-Spec.md`)                                                       |
| E2 — Curriculum Ingestion         | Nạp syllabus thật vào RAG                       | PLO3             | Gate 2 (≥3 môn) → Mốc 3 (~10 môn, mở rộng năm 3-4)                                       |
| E3 — Weekly Planning (Plan)       | AI chia nhỏ mục tiêu từ syllabus, có reranker | PLO1, PLO2, PLO3 | Gate 2 (đầy đủ, kể cả reranker)                                                            |
| E4 — Resource Q&A (Do)            | Hỏi-đáp có trích nguồn + nhắc việc         | PLO3             | Gate 2 (Q&A+reranker) → Mốc 3 (nhắc việc 48h)                                                |
| E5 — Reflection (Reflect)         | Đối thoại phản tư cuối tuần                 | PLO1, PLO2       | **Gate 2 (đầy đủ)**                                                                    |
| E6 — Academic Integrity Guardrail | Chặn "làm hộ bài"                              | PLO6             | Gate 2 (rule-based + LLM classifier + test suite ≥20 case) → Mốc 3 (tinh chỉnh đạt ≥90%)  |
| E7 — Instructor Dashboard & HITL  | Dashboard GV, duyệt alert                         | PLO6             | **Gate 2 (đầy đủ, logic thật)**                                                       |
| E8 — Admin Console                | Quản lý ingest, KPI tổng                        | PLO4, PLO5       | Mốc 3                                                                                           |
| E9 — Evaluation & Observability   | RAGAS, log cost/latency, guardrail test, Sentry    | PLO7             | Gate 2 (RAGAS 10-15 câu + Sentry) → Mốc 3 (RAGAS 15-20 câu + LLM-as-Judge + load test thật) |

*(Đặc tả chi tiết từng FR — input/xử lý/output/error, không phải format Given-When-Then — xem `02-Cursus-SRS.md` mục 3; đã đối chiếu để không còn mâu thuẫn với bảng mốc trên.)*

### 9.1. Mapping vào 3 cấu phần BTC chấm (CP1/CP2/CP3)

> BTC chấm theo đúng khung "Ba cấu phần cần cân bằng" (Quy định chung), không phải chỉ theo PLO ở bảng trên — bảng dưới quy các Epic/tài liệu đã có về đúng 3 nhãn đó để dễ đối chiếu lúc pitch, không viết thêm nội dung mới.

| Cấu phần                                           | Yêu cầu BTC                                        | Bằng chứng đã có trong docs                                                                                                                                                                                                                                                                                                                                                      |
| ---------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **CP1 — Bài toán và giá trị kinh doanh** | Đúng bài toán, có giá trị kinh doanh          | Mục 2-3 (Problem Statement), mục 4 (Value Proposition + vị trí cạnh tranh,`05-Competitive-Analysis.md`), mục 5 (Business Model Canvas + ROI story), mục 6 (KPI đo được cụ thể)                                                                                                                                                                                         |
| **CP2 — Khả năng triển khai**              | Hạ tầng, dữ liệu, vận hành triển khai được | `06-Cursus-Ha-tang-Supabase-Scale2000.md` (stack + ngân sách + đánh giá scale 2.000 người), `03-Cursus-Execution-Plan.md` (lịch trình theo mốc), `07-Production-Readiness-Checklist.md` (gap còn thiếu để chuẩn production) + `08-Cursus-Deliverables-Checklist.md` (10 deliverable + thang điểm), Epic E2 (Curriculum Ingestion — dữ liệu thật từ FLM) |
| **CP3 — Ứng dụng AI**                       | Tối ưu ứng dụng AI vững                         | Epic E3-E6, E9 (Plan/Q&A/Reflect/Guardrail/Eval), kiến trúc multi-agent LangGraph (`02-SRS.md` mục 1.4), reranker vượt naive RAG (ADR-004 ở `docs/decisions/ADR.md`), model routing chi phí (`02-SRS.md` mục 4.1)                                                                                                                                                       |

**Điểm cần chú ý khi pitch:** CP1 và CP3 đã có bằng chứng dày; CP2 phụ thuộc vào việc deploy thật chạy ổn định tới lúc chấm (rủi ro lớn nhất là Supabase free tier tự tạm dừng sau 7 ngày không truy cập — đã có phương án ở `06` mục 2.2, nên chốt nâng Pro trước ngày chấm, không phải trước ngày nộp).

---

## 10. Data Model

```
User (id, role, name, email)
   └── Student (user_id, enrolled_courses[])
   └── Instructor (user_id, managed_classes[])
   └── Admin (user_id)

Course (id, subject_code, subject_name, semester, no_credit, prerequisite)
   └── SyllabusChunk (chunk_id, subject_code, subject_name, section, text, source_label)
       — khớp đúng output thật của flm_parser.py (xem 04-Cursus-Terminology.md PHẦN A.2); không có field `id` riêng, chunk_id là khoá chính

WeeklyPlan (id, student_id, week_number, goal, tasks[])
   └── Task (id, plan_id, title, description, duration_estimate, source_chunk_id, deadline, status)
       — khớp đúng output của FR-3.1 (02-Cursus-SRS.md mục 3.3)

ReflectionSession (id, student_id, week_number, qa_pairs[], summary)
Alert (id, student_id, type, threshold_triggered, status, reviewed_by)
GuardrailLog (id, user_id, input_snippet_hash, blocked, reason, timestamp)
EvalRun (id, timestamp, metric_scores{}, dataset_version)
```

---

## 11. Rủi ro & Giảm thiểu (đã bổ sung rủi ro cạnh tranh)

| Rủi ro                                                                                                                                                                             | Khả năng                                                                | Tác động                                                                                        | Giảm thiểu                                                                                                                                                                                                                                                                                                     |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Không ingest kịp curriculum trước Gate 2                                                                                                                                        | Trung bình (đã giảm nhờ có parser + JSON mẫu sẵn)                 | Cao                                                                                                | Chỉ ingest ≥3 môn năm 1, đã có SSA101 sẵn                                                                                                                                                                                                                                                                |
| Guardrail chặn nhầm                                                                                                                                                               | Trung bình                                                               | Trung bình                                                                                        | Test sớm, tinh chỉnh threshold liên tục                                                                                                                                                                                                                                                                      |
| 4 người vỡ tiến độ khi tích hợp                                                                                                                                             | Cao nếu không quản lý                                                 | Cao                                                                                                | Daily sync, integrator cuối mỗi giai đoạn                                                                                                                                                                                                                                                                    |
| **Câu chuyện cạnh tranh bị giám khảo bẻ bằng Canvas IgniteAI Agent**                                                                                                  | Cao (đây là sản phẩm mới, nhiều khả năng giám khảo đã biết) | Cao                                                                                                | Chuẩn bị sẵn câu trả lời ở mục 4; không né tránh khi bị hỏi                                                                                                                                                                                                                                         |
| Đội hiện tại chưa code gì, chỉ còn 5 ngày tới Gate 2                                                                                                                      | Đã xảy ra                                                              | Cao                                                                                                | Cắt phạm vi Gate 2 xuống mức tối thiểu tuyệt đối (mục 8.1), ưu tiên AI coding agent cho phần lặp lại (CRUD, UI boilerplate)                                                                                                                                                                       |
| **Code đã phân tán trên nhiều branch (`chung`, `develop`, `haianh`) chưa merge về branch chính đang review (`haidang2425`) — xác nhận thật 10/08/2026** | Đã xảy ra                                                              | Cao (rủi ro trùng công/xung đột merge lớn nếu không xử lý trước khi phân công tiếp) | Nhóm trưởng chốt 1 branch tích hợp chính (khuyến nghị merge`chung` — đang có nhiều việc nhất theo git log: auth/RBAC/Gemini/Admin Console/Vite UI) trước khi giao việc tiếp cho Người A/B/C, rồi mới đối chiếu lại `docs/project/structure-team.md` mục 2.1 cho khớp code thật |

---

## 12. Non-Functional Requirements

Xem `02-Cursus-SRS.md` mục 4 — đã sửa để không còn mâu thuẫn với KPI 1.000 SV (mục 6 ở trên).

---

*Tài liệu này thay thế toàn bộ bản PRD v1.0. Đọc cùng `02-Cursus-SRS.md` và `03-Cursus-Execution-Plan.md`.*
