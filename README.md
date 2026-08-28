# Cursus — AI Academic Companion

> SV Trường FPT University học nhiều môn, deadline dày đặc, thiếu người đồng hành lập kế hoạch/theo dõi/tự nhìn lại việc học → Cursus là trợ lý học tập AI đi theo chu trình **Plan → Do → Reflect**, luôn trích nguồn từ đúng tài liệu môn học, có mascot Curi đồng hành.

Đề tài gốc **EDU-01** (AI20K Build Phase, ngân hàng đề Khoá 3 & 4) — chi tiết đối chiếu đề bài BTC ở [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) mục 2.

> 📖 **Repo có gần 80 file tài liệu — đọc [`DOCS_GUIDE.md`](DOCS_GUIDE.md) trước khi đọc bất kỳ file nào khác.** File đó lọc sẵn: giám khảo đọc 8 dòng nào, mỗi thành viên team đọc gì cho role của mình, cái gì có thể bỏ qua hoàn toàn.

| | |
|---|---|
| **Nhóm** | Group06 · Team093 (P-093) |
| **Nhóm trưởng** | Trịnh Hải Đăng (`haidang2425`) |
| **Thành viên** | Nguyễn Hải Anh (`haianh06`) · Nguyễn Anh Bình (`NguyenThanhBinh108`) · Nguyễn Đức Chung (`chungnguyenvp`) |
| **Đối tượng** | Sinh viên ngành SE (Software Engineering), FPT University, curriculum BIT_SE_K20D_K21A |
| **Chương trình** | VinUni AI20K Build Phase, Cohort 2/3 |

---

## Vấn đề & giải pháp

**Vấn đề:** SV chỉ "chạy theo bài" — không có ai giúp đặt mục tiêu tuần, chia nhỏ việc từ syllabus, và nhìn lại đã học được gì sau mỗi mốc. Giảng viên không có cách nào thấy sớm SV nào đang trễ tiến độ trước khi deadline đã trôi qua.

**Giải pháp — chu trình Plan → Do → Reflect có AI hỗ trợ:**

| # | Tính năng | Vai trò |
|---|---|---|
| F1 | Đăng nhập theo vai trò (SV / GV / Admin) | Tất cả |
| F2 | **Plan** — SV nêu mục tiêu tuần, AI chia nhỏ task từ đúng syllabus, có trích nguồn | Sinh viên |
| F3 | **Q&A có trích nguồn + Guardrail chặn "làm hộ bài"** — chạy guardrail trước khi gọi AI, không bịa nội dung | Sinh viên |
| F4 | Dashboard lớp cho giảng viên — % hoàn thành đúng hạn theo tuần, ẩn danh | Giảng viên |
| F5 | **Cảnh báo SV nguy cơ trễ + HITL** — GV tự bấm "đánh dấu đã can thiệp", hệ thống không tự gửi gì cho SV | Giảng viên |
| F6 | Bảng quản lý curriculum đã nạp vào hệ thống AI | Admin |
| F7 | KPI so sánh tỷ lệ nộp đúng hạn có/không dùng Cursus, kèm ghi chú phương pháp đo | Admin |

Mô tả input/output/API đầy đủ từng tính năng: [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) mục 13 (Plan → Do → Reflect), mục 16 (data/API contract) và mục 21 (acceptance criteria).

**Ràng buộc bắt buộc:** AI không làm hộ bài tính điểm · dữ liệu SV ẩn danh khi tổng hợp · gợi ý phải grounded + trích nguồn, không bịa · mọi hành động rủi ro (can thiệp SV) cần người phê duyệt.

---

## Trạng thái dự án (cập nhật 22/08/2026 — xem đầy đủ ở `docs/PROJECT_CONTEXT.md` mục "TRẠNG THÁI HIỆN TẠI", nguồn sự thật mới nhất)

- Nhánh làm việc hiện tại: `cleanup/repo-audit-20260820` (không phải `main`).
- **7/8 mục P0 an ninh/eval đã xong, có bằng chứng** (test/ảnh/log ở `docs/evidence/`): khoá role escalation, RBAC/IDOR sweep (2 lỗ hổng tìm thấy + vá), phòng thủ prompt injection (LLM07) + validate nội dung tài liệu trước khi embed (LLM08), trace `llm_success`/`fallback_used`/`retrieval_empty` cho Plan/Reflect/QA, xoá dữ liệu cá nhân (MVP), risk policy versioning, và 1 batch eval Gemini thật quy mô nhỏ (11 case, không phải full benchmark).
- **Mock LMS** — hệ thống mô phỏng LMS riêng biệt (app/DB/OAuth thật) đã dựng xong, Cursus đọc syllabus/deadline qua REST API thật thay vì chỉ file tĩnh.
- **Còn treo, cần xử lý thủ công trên Supabase Dashboard trước khi coi là xong hoàn toàn:** Row-Level Security đa tổ chức (P0#3, hiện 0% — filter tổ chức mới chỉ ở tầng ứng dụng) và đối chiếu `alembic_version` bị lệch chain.
- `pytest tests/` gần nhất: 461 passed, 7 skipped, 0 failed.
- Chi tiết quyết định kỹ thuật quan trọng: [`docs/decisions/ADR.md`](docs/decisions/ADR.md). Ngữ cảnh sản phẩm/kỹ thuật đầy đủ, cập nhật liên tục: [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md).

---

## Tech Stack (thật, đã dùng trong code — không phải gợi ý mặc định của template)

| Layer | Công nghệ |
|---|---|
| LLM + Embedding | Google Gemini (`gemini-3.6-flash`, `gemini-embedding-001`) — xem ADR-002. Tên model Gemini đã bị khai tử âm thầm 3 lần trong dự án (`config.py`/embedding/`model_fallbacks`), xem `docs/PENDING_DECISIONS.md` #3 |
| Agent orchestration | LangGraph route (`src/agents/graph.py`) tồn tại làm tham chiếu, **không nằm trong luồng sản phẩm chính** — thực tế là LLM-with-fallback theo từng service (ADR-012), xem `ARCHITECTURE.md` mục 3 |
| RAG | **Không dùng pgvector/reranker thật** dù ADR-004 từng định hướng vậy — code thật (`src/services/rag/retrieval_service.py`) là lexical TF/coverage scoring blend với cosine similarity thuần Python trên cache JSON, không có bge-reranker. Ghi nhận là điểm lệch tài liệu-vs-code, chưa vá (không urgent cho 23/08) |
| Backend | FastAPI, SQLAlchemy + Alembic, Postgres (Supabase), Redis, argon2/pyjwt cho auth |
| Frontend | React 19 + Vite + Tailwind CSS v4 (không TypeScript), react-router-dom v7 |
| Auth/DB/Storage | Supabase — xem ADR-001 |
| Deploy | Vercel (frontend) + Railway (backend) |
| AI usage logging | Hook tự động cho Claude Code/Cursor/Codex/Gemini CLI/Copilot/Antigravity (bắt buộc theo BTC) |

Toàn bộ quyết định kỹ thuật + lý do + đánh đổi: [`docs/decisions/ADR.md`](docs/decisions/ADR.md).

---

## Quick Start

### 1. Setup môi trường

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Điền GOOGLE_API_KEY (Gemini) và AI_LOG_API_KEY riêng của bạn (từ link mời BTC)
```

### 2. Cài AI Logging Hooks (bắt buộc, 1 lần sau khi clone)

```bash
bash scripts/setup_hooks.sh
# Windows PowerShell: powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1
```

### 3. Chạy Backend

```bash
python -m uvicorn src.main:app --reload --port 8000
# Swagger UI: http://localhost:8000/docs
```

### 4. Chạy Frontend

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

**Gặp lỗi `Fatal error in launcher` trên Windows** (thường do đổi tên/di chuyển thư mục dự án) hoặc cần hướng dẫn chi tiết hơn (state switcher demo, 5 màn hình mẫu): xem [`docs/project/run-guide.md`](docs/project/run-guide.md).

**Muốn chạy cả Mock LMS** (hệ thống ngoài mô phỏng Canvas, OAuth thật, để xem Cursus đồng bộ deadline/assignment từ 1 hệ thống thật riêng biệt): xem [`RUNNING.md`](RUNNING.md) mục 3.3.

### 5. Xem tiến độ team (không cần hỏi ai bằng lời nói)

```bash
# Bảng tổng quan tất cả 4 người, tất cả sprint (chạy được trên PowerShell/CMD/Bash, không cần cài gì thêm)
python scripts/progress_report.py

# Xem riêng từng người — kèm danh sách chi tiết còn thiếu việc gì
python scripts/progress_report.py --person DANG
python scripts/progress_report.py --person HAIANH
python scripts/progress_report.py --person BINH
python scripts/progress_report.py --person CHUNG

# Có cài `make` (macOS/Linux/Git Bash) thì gõ tắt được:
make progress
```

Lịch sử tick tiến độ team (giai đoạn trước khi hợp nhất branch) nằm ở [`docs/archive/planning-v2/progress/`](docs/archive/planning-v2/progress/) — giữ lại để tham khảo, không còn là quy trình đang chạy sau khi backend/frontend đã hợp nhất.

---

## Bản đồ tài liệu

Đầy đủ (giám khảo đọc gì, mỗi thành viên đọc gì, file nào bỏ qua): **[`DOCS_GUIDE.md`](DOCS_GUIDE.md)**. 4 link hay dùng nhất:

| Muốn biết gì | Đọc file |
|---|---|
| Business/product/role/pages + data/API contract/business rules/demo script/deploy (đọc trước tiên, dán cho AI coding assistant làm context) | [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) |
| Frontend — tính năng/dữ liệu cần có từng trang (không có spec UI/UX pixel-accurate riêng, có chủ đích) | [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) mục 6, hoặc đọc trực tiếp `frontend/src/components/` |
| Quyết định kỹ thuật quan trọng + lý do | [`docs/decisions/ADR.md`](docs/decisions/ADR.md) |

---

## 📋 10 Deliverables cho Demo Day

| # | Deliverable | Vị trí | Trạng thái |
|---|---|---|:---:|
| 1 | Source Code | `src/`, `frontend/` | ✅ |
| 2 | README.md | file này | ✅ |
| 3 | Architecture Diagram | `ARCHITECTURE.md` — cập nhật 22/08/2026 khớp kiến trúc thật (Mock LMS, trace wiring, RAG lexical+embedding, không pgvector/reranker) | ✅ |
| 4 | AI Logs | LangSmith + Auto AI Usage Logging | ✅ Hook đã chạy |
| 5 | Live URL | Vercel + Railway | ⚠️ Đang chuẩn bị — xem `ARCHITECTURE.md` mục Deployment, checklist còn 1 gap (`alembic_version` lệch chain) cần xử lý trước |
| 6 | Video Demo | `presentation/` | 📝 Kịch bản có sẵn (mục 19 `PROJECT_CONTEXT.md`), quay thật chưa làm |
| 7 | Pitch Deck | `presentation/` | 📝 Outline 10 trang có sẵn, thiết kế slide thật chưa làm |
| 8 | Development Journal | `JOURNAL.md` | ⚠️ Có tới Week 1 (01–09/08), khoảng trống 10–22/08 cần tự điền |
| 9 | Worklog | `WORKLOG.md` | ⚠️ Có tới 09/08, khoảng trống 10–22/08 cần tự điền |
| 10 | Evaluation Evidence | [`docs/AI_QUALITY_EVALUATION_REPORT.md`](docs/AI_QUALITY_EVALUATION_REPORT.md) (tổng hợp) + `eval/results/report.md` (chi tiết) + `docs/evidence/` | ✅ Eval Gemini thật bộ nhỏ (11 case) + toàn bộ bằng chứng test/ảnh/security-finding |

Chi tiết + thang điểm 50: [`docs/archive/planning-v2/08-Cursus-Deliverables-Checklist.md`](docs/archive/planning-v2/08-Cursus-Deliverables-Checklist.md).

## 📊 AI Usage Logging

Bắt buộc theo BTC — hook tự động cho Claude Code/Cursor/Codex/Gemini CLI/GitHub Copilot/Antigravity, log vào `.ai-log/session.jsonl`, tự submit lên grading server mỗi lần `git push`. ChatGPT/web tool khác dùng log thủ công:

```bash
bash scripts/_pyrun.sh scripts/log_manual.py --tool chatgpt --prompt "..."
```

Chi tiết cơ chế: [`docs/project/logging-guide.md`](docs/project/logging-guide.md).

## Known Limitations

Những giới hạn dưới đây là **quyết định có chủ đích** trong phạm vi Build Phase,
không phải lỗi chưa phát hiện. Mỗi mục đều có lý do truy được về ADR hoặc spec.

- **Instructor 360 chỉ ở mức tổng hợp (aggregate-only)** — hiện có 1 route. Chi tiết
  hoạt động giảng viên (`ClassActivity`, `Quiz`, `PracticeSet`, quyết định guardrail)
  để lại cho giai đoạn sau: công lớn, không phục vụ F6/F7 là hai mảng chính thức của
  role Admin.
- **Student 360 chưa bao gồm quiz / practice / semester** — 15 route hiện có phủ hồ sơ
  học tập và tín hiệu rủi ro, chưa phủ ba nguồn dữ liệu này.
- **Luồng DSAR qua Admin Console chưa mở** — tab "Yêu cầu dữ liệu" đã gỡ khỏi
  điều hướng; 7 route backend và bảng `DataRequest` vẫn còn trong code nhưng không có
  đường vào từ UI. Lý do đầy đủ: ADR-021.
- **FR-1.3 (xoá dữ liệu cá nhân theo yêu cầu) mới thực thi một phần** — đây là mục
  **Must của Mốc 3**, nên ghi rõ chứ không tính là đã xong. Hiện chỉ có nhánh
  self-service `POST /api/v1/student/personal-data/delete`, xoá `Message` +
  `Conversation` + `WeeklyReflection`. So với phạm vi spec còn thiếu `WeeklyPlan`,
  `StudyTask`, `GuardrailEvent`, và chưa có nhánh cho Admin xoá thay sinh viên (spec
  cho phép cả hai). Xem `docs/archive/planning-v2/02-Cursus-SRS.md` FR-1.3 và ADR-021.
- **Chi phí AI hiển thị dạng ước tính, và bảng giá chưa điền** — màn "Chi phí AI" tính
  chi phí bằng token nhân đơn giá niêm yết theo model, không phải số từ hoá đơn nhà
  cung cấp. `src/services/core/ai_pricing.py` hiện chưa khai báo đơn giá cho model nào
  nên cột chi phí báo "chưa có đơn giá"; token, độ trễ và tỷ lệ lỗi vẫn là số thật.
  Model không có trong bảng giá **không bị đoán giá** — có chủ đích.
- **RLS đa tổ chức (P0#3) vẫn 0%** — lọc theo tổ chức hiện thực hiện ở tầng ứng dụng,
  chưa đẩy xuống Row Level Security của Postgres. `src/db/tenant_scope.py` đã viết sẵn
  dependency cần thiết nhưng chưa gắn vào route nào; xem `docs/decisions/rls-migration-plan.md`.

## License

MIT — sử dụng cho mục đích giáo dục (AI20K Build Phase).
