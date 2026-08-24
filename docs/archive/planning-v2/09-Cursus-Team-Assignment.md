# 09 — Cursus Team Assignment (Phân công theo Role, tới 23/08/2026)

**Viết:** 11/08/2026 · **Mô hình:** thay "Người A (Backend)/B (RAG)/C (Frontend)/D (PM)" ở `00-Cursus-Playbook.md` PHẦN 6 và bảng lịch ở `03-Cursus-Execution-Plan.md` bằng **mô hình sở hữu theo role sản phẩm** — mỗi thành viên sở hữu trọn 1 vai trò người dùng (frontend + nối API cho vai trò đó), nhóm trưởng sở hữu hạ tầng dùng chung. Đây là quyết định của nhóm trưởng Trịnh Hải Đăng, áp dụng từ hôm nay.

> ⚠️ **Cập nhật 12/08/2026 — mô hình sở hữu frontend thật đã đổi, đọc trước khi thắc mắc "sao code frontend khác doc":** 3 file `roles/{HAIANH,BINH,CHUNG}_*.md` mô tả UI/UX **để từng người tự vibe-code, dùng để tự test backend/luồng nghiệp vụ phần mình** — không phải giao diện sẽ merge làm bản chính thức. **Đăng trực tiếp thiết kế + code toàn bộ frontend production cho cả 4 role** (mock-data layer riêng, không phụ thuộc backend), rồi tự kiểm tra/merge toàn bộ luồng cuối cùng — đúng tinh thần "sở hữu hạ tầng dùng chung" ở bảng dưới, chỉ mở rộng ra luôn cả UI 3 role kia thay vì chỉ khung chung. Nội dung API/luồng nghiệp vụ trong `roles/*.md` vẫn đúng, chỉ phần UI cuối là do Đăng quyết.

> **Quan hệ với các doc khác:** file này **không thay đổi lịch theo ngày/mục tiêu Gate 2 (~60%, 14/08) / Mốc 3 (23/08)** đã chốt ở `03-Cursus-Execution-Plan.md` — chỉ đổi **ai làm phần nào**. Đọc `03` để biết "hôm nay hạn chót gì", đọc file này để biết bức tranh tổng của cả 4 người. **Mỗi người còn có 1 file chi tiết riêng, chỉnh chu hơn nhiều** — mô tả UI/UX cụ thể (kèm ASCII layout), tham khảo sản phẩm thật (quốc tế + Việt Nam + link GitHub), ví dụ input/output từng tính năng, lịch theo ngày và prompt vibe-code sẵn dùng: [`roles/DANG_infra-auth-frontend.md`](roles/DANG_infra-auth-frontend.md) · [`roles/HAIANH_student.md`](roles/HAIANH_student.md) · [`roles/CHUNG_admin.md`](roles/CHUNG_admin.md) · [`roles/BINH_instructor.md`](roles/BINH_instructor.md). File này (`09`) là bản tóm tắt/tra cứu nhanh; 4 file trong `roles/` mới là bản đầy đủ để code theo.

---

## 0. Đội hình

| Người | GitHub | Sở hữu |
|---|---|---|
| **Trịnh Hải Đăng** (nhóm trưởng) | `haidang2425` | Hạ tầng/deploy, auth (F1), khung frontend dùng chung + design system, data pipeline + Canvas ảo, review toàn bộ code, docs |
| Nguyễn Hải Anh | `haianh06` | Role **Sinh viên** — F2 (Plan), F3 (Q&A phía SV), Reflect |
| Nguyễn Đức Chung | `chungnguyenvp` | Role **Admin** — F6 (curriculum), F7 (KPI) |
| Nguyễn Anh Bình | `NguyenThanhBinh108` | Role **Giảng viên** — F4 (dashboard lớp), F5 (risk + HITL) |

---

## 1. 🚨 JOB #0 — Việc chặn tất cả các việc khác (sở hữu: Đăng, hạn chót: hết ngày 12/08)

### Phát hiện (xác nhận thật 11/08/2026)

Repo hiện phân mảnh trên 5 branch, **chưa từng merge vào nhau**:

| Branch | Có gì | Không có gì |
|---|---|---|
| `haidang2425` (đang HEAD) | Frontend hoàn chỉnh: landing page, mascot Curi, design system, 6 màn auth, dashboard SV/GV/Admin | **Backend rỗng** — `src/api/routes.py` vẫn nguyên khung BTC (`/chat`, `/status`); toàn bộ dữ liệu là mock `useState` trong `CursusContext.jsx`, không có `fetch()` nào |
| `origin/chung` = `origin/haianh` (commit cuối 08/08) | **Backend production-grade đầy đủ**: `src/api/auth.py` (register/login/MFA-TOTP/quên mật khẩu/xác thực email/refresh/logout/session), `plans.py` (F2), `qa.py` (F3), `instructor.py` (F4+F5), `student.py`, `canvas_routes.py` (**Mock Canvas LMS API 13 endpoint — chính là "Canvas ảo"**), `audit.py`; RBAC, CSRF, rate limit, security headers; `src/db/models.py` (SQLAlchemy); `requirements.txt` đã bật thật sqlalchemy/alembic/psycopg2/redis/argon2/pyjwt/chromadb/langchain-google-genai | Frontend cũ hơn (TypeScript, chưa có landing page/mascot/design system hiện tại) |
| `origin/thanhbinh` | = `chung` + thêm `document_ingest_service.py`, `conversation_intent_service.py`, `curriculumFallback.js` | Cùng frontend cũ với `chung`, không phải bản `haidang2425` |
| `origin/develop` | Bộ auth/security riêng (session/token/MFA/permissions) — gần giống `chung` (auth_service.py chỉ khác 11 dòng) | — |

**Không có API admin nào tồn tại ở bất kỳ branch nào** (`src/api/admin.py` chưa được tạo ở đâu cả) — F6/F7 cần xây mới hoàn toàn (xem mục 2.3).

### Chiến lược đã chốt

Giữ **frontend của `haidang2425`** làm chuẩn UI. Giữ **`src/` của `origin/chung`** làm chuẩn backend. Việc là **tích hợp**, không phải "chọn 1 bên xoá bên kia".

### Việc làm cụ thể (Đăng)

1. Tạo branch tích hợp mới từ `haidang2425` (vd `integration/backend-merge`), **không code trực tiếp trên `haidang2425`** trong lúc merge.
2. Copy nguyên `src/` của `origin/chung` đè lên (trừ `src/agents/` — giữ bản BTC skeleton nếu `chung` không đổi gì đáng kể, kiểm tra lại trước khi đè) + `requirements.txt` + `src/db/`, `src/repositories/`, `src/security/`, `src/services/`, `src/api/*`, `src/schemas/`, `src/knowledge/`, `src/prompts/`.
3. Cập nhật `.env`/`.env.example`: `DATABASE_URL` Postgres thật (Supabase, theo ADR-001), `REDIS_URL`, JWT secret, `GOOGLE_API_KEY` (Gemini, theo ADR-002) — **không dùng `OPENAI_API_KEY` mặc định trong `.env.example` gốc BTC**.
4. Chạy migration (`alembic upgrade head` — kiểm tra `chung` đã có sẵn migration script chưa, nếu chưa thì tạo từ `src/db/models.py`).
5. Từ frontend cũ trên `chung`: **chỉ lấy phần logic gọi API** (`lib/api.js`, `lib/rbac.js`, cách `AuthContext.jsx` lưu/refresh token) — viết lại thành `frontend/src/lib/api.js` mới, khớp base URL + path thật (`/api/v1/...`) đã liệt kê ở mục 6 (phụ lục). **Không copy UI/JSX từ bản cũ** — UI giữ nguyên bản hiện tại của `haidang2425`.
6. Verify tối thiểu trước khi coi Job #0 xong: `uvicorn src.main:app` chạy được, Swagger `/docs` liệt kê đủ router (`auth`, `plans`, `qa`, `instructor`, `student`, `canvas`, `audit`), gọi thử `POST /api/v1/auth/login` từ Swagger UI trả JWT thật (không cần frontend nối xong).
7. Sau khi backend chạy được độc lập → mới giao cho 3 người mục 2 nối UI thật vào (đừng đợi tích hợp 100% xong mới bắt đầu, 3 người có thể nối API song song ngay khi Swagger UI xác nhận route của họ hoạt động).
8. Đóng risk item tương ứng ở `01-Cursus-PRD.md` mục 11 (risk register) và cập nhật `docs/project/structure-team.md` mục 2.1 khi xong.

**Vì sao Đăng làm việc này chứ không chia đều:** đây là việc dễ xung đột nhất (đè file, đổi cấu trúc `src/`) — để 1 người làm dứt điểm nhanh hơn 4 người cùng đụng vào. 3 người còn lại trong lúc chờ vẫn code UI/logic role của mình dựa trên **API contract đã biết trước** (mục 6), ghép vào ngay khi Job #0 xong — không ngồi chờ không làm gì.

---

## 2. Phạm vi từng người — tới hết dự án (23/08)

### 2.1 Trịnh Hải Đăng — Team lead / Hạ tầng / Auth / Khung frontend / Data & "Canvas ảo"

| Việc | Mô tả cụ thể | Deliverable liên quan |
|---|---|---|
| Job #0 | Tích hợp backend `chung` vào frontend `haidang2425` (mục 1) | Source Code |
| Deploy | Vercel (frontend) + Railway (backend) + Supabase (DB/Auth/Storage) — theo `06-Cursus-Ha-tang-Supabase-Scale2000.md` | Live URL |
| Auth (F1) | Nối `LoginScreen.jsx`/`RegisterScreen.jsx`/`ForgotPasswordScreen.jsx`/`ResetPasswordScreen.jsx`/`EmailVerificationScreen.jsx`/`OnboardingScreen.jsx` vào đúng endpoint auth thật (mục 6) — xử lý cookie access/refresh token, chuyển đúng route theo role trả về từ `/auth/me` | F1 |
| Design system enforcement | Review mọi PR của 3 người còn lại đối chiếu `docs/frontend/00_AI_CONTEXT_PACK.md` — không cho merge nếu vi phạm token/motion/a11y đã quy định | Checklist `08_SCREEN_CONSISTENCY_CHECKLIST.md` |
| Data pipeline | Mở rộng ingest thêm môn (Mốc 3: ~10 môn) bằng `docs/planning/v2/scripts/flm_parser.py`; mở rộng seed SV bằng `gen_seed_students.py` | FR-2.1 |
| "Canvas ảo" | `canvas_routes.py` đã có sẵn 13 endpoint trên `chung` — việc còn lại là kiểm chứng dữ liệu mock nhất quán với dữ liệu FLM đã ingest, expose đúng response shape mà `student.py`/`instructor.py` cần | ADR-005 |
| Backend review | Đọc lại toàn bộ `src/security/`, `src/services/*` đã kế thừa từ `chung` — vá lỗ hổng nếu có trước khi 3 người khác build lên trên (ưu tiên: CSRF/rate-limit đã bật đúng chưa, guardrail có chạy trước khi gọi LLM không — F3 ràng buộc bắt buộc) | PLO6 |
| Docs | Duy trì toàn bộ cây `docs/` khớp code thật (đang làm) | Deliverable #2, #3 |

### 2.2 Nguyễn Hải Anh — Sinh viên (F2 Plan, F3 Q&A phía SV, Reflect)

Toàn bộ backend cho role này **đã có sẵn trên `chung`** (`plans.py`, `qa.py`, `student.py`) — việc là nối UI đã có (`StudentHome.jsx`, `StudentReflection.jsx`) vào, không phải xây API mới.

| Tính năng | UI file | Endpoint thật (sau Job #0) | Ví dụ cụ thể |
|---|---|---|---|
| Xem thời khoá biểu/dashboard | `StudentHome.jsx` | `GET /api/v1/student/dashboard`, `GET /api/v1/plans/timetable` | Vào trang, load task tuần này + môn đang học, thay hoàn toàn `INITIAL_TASKS`/`INITIAL_COURSES` trong `CursusContext.jsx` |
| Tạo kế hoạch tuần (F2) | `StudentHome.jsx` (khu nhập mục tiêu) | `POST /api/v1/plans/generate` → nhận `tasks[]` có `source_label` → `POST /api/v1/plans/accept` khi SV chốt | SV gõ "Hoàn thành Project Part 1", bấm Tạo kế hoạch → gọi `generate`, render list `PlanTaskCard`, mỗi task hiện rõ trích nguồn (không hiện task không có `source_label` mà không cảnh báo) |
| Sửa/xoá task | `StudentHome.jsx` | `PATCH /api/v1/plans/tasks/{task_id}` | Bấm nút sửa giờ ước tính hoặc đánh dấu hoàn thành trên 1 task card |
| Hỏi-đáp có trích nguồn (F3) | `StudentHome.jsx` (chat) hoặc tách thành `AiTutorChat.jsx` riêng | `POST /api/v1/qa` (body `{subject_code, question}`) | SV hỏi "Điểm qua môn cần bao nhiêu?" → render `.chat-bubble-assistant` + citation chip; nếu bị chặn guardrail → render `.chat-bubble-blocked` (đỏ), **không hiện như lỗi hệ thống** |
| Nộp tài liệu môn (nếu cần cho luồng ingest cá nhân) | mới, chưa có UI | `POST /api/v1/student/courses/{course_id}/documents` | Thấp ưu tiên, chỉ làm nếu dư giờ |
| Reflect | `StudentReflection.jsx` | `GET /api/v1/student/reflections`, `POST /api/v1/student/reflections/generate` | Cuối tuần, SV bấm "Bắt đầu phản tư" → gọi `generate`, hiện đối thoại tổng kết + lưu vào lịch sử |
| Rủi ro của chính mình | mới | `GET /api/v1/student/risks` | Hiện badge cảnh báo nếu SV đang bị GV đánh dấu nguy cơ (đọc, không sửa được) |

**Việc cần làm ngay khi chưa xong Job #0:** tiếp tục polish UI/UX của các màn trên theo `docs/frontend/00_AI_CONTEXT_PACK.md` (đúng token màu PLAN/DO/REFLECT, đúng state loading/empty/error/success) — không phải ngồi chờ.

### 2.3 Nguyễn Đức Chung — Admin (F6 curriculum, F7 KPI)

⚠️ **Khác 2 role kia: backend cho Admin CHƯA TỒN TẠI ở bất kỳ branch nào** — không có `src/api/admin.py`. Đây là role duy nhất phải **tự xây API mới**, không chỉ nối vào cái có sẵn.

| Việc | Mô tả | Ghi chú |
|---|---|---|
| Xây `src/api/admin.py` (mới) | `GET /api/v1/admin/courses` (trạng thái ingested/not_ingested + `chunk_count`), `GET /api/v1/admin/kpi` (so sánh `with_cursus_overall` vs `baseline_overall`, **bắt buộc kèm `method_note`** theo `00-Cursus-Playbook.md` F7) | Tái dùng `chunk_repository.py` (đã có trên `chung`) và `document_ingest_service.py` (đã có trên `thanhbinh` — xin merge thêm file này) làm nền, không viết lại từ 0 |
| Upload tài liệu môn mới | `POST /api/v1/admin/courses/{code}/documents` gọi `document_ingest_service.py` | |
| Xem audit log | `AdminConsole.jsx` phần "Developer Audit Logs Terminal" | `GET /api/v1/audit/events` — **endpoint này đã có sẵn trên `chung`, dùng ngay, không cần xây** |
| Rule Engine (bật/tắt guardrail rule) | UI đã phác thảo (iOS switch) nhưng **guardrail hiện chạy cứng trong `qa_service.py`, chưa có endpoint cấu hình được** | Quyết định cùng Đăng: scope Gate 2 chỉ hiển thị rule đang bật (read-only), việc cho phép Admin bật/tắt thật dời sang Mốc 3 nếu kịp — đừng tự ý hứa UI làm được việc backend chưa hỗ trợ |
| Kế thừa UI | `AdminConsole.jsx` (206 dòng) đã được Bình dựng trước đây (xem `WORKLOG.md` 09/08) | Trao đổi trực tiếp với Bình trước khi sửa sâu — tránh hiểu nhầm/giẫm việc, đây là bàn giao chính thức trong đợt đổi phân công này |

### 2.4 Nguyễn Anh Bình — Giảng viên (F4 dashboard, F5 risk + HITL)

Backend cho role này **đã có sẵn đầy đủ trên `chung`** (`instructor.py`) — khớp gần như 1:1 với F4/F5.

| Tính năng | UI file | Endpoint thật (sau Job #0) | Ví dụ cụ thể |
|---|---|---|---|
| Dashboard lớp (F4) | `InstructorHome.jsx` | `GET /api/v1/instructor/dashboard` | Biểu đồ % hoàn thành theo tuần cả lớp — **chỉ số tổng hợp, không hiện tên/nội dung riêng SV ở màn này** (đúng yêu cầu ẩn danh của đề bài) |
| Danh sách rủi ro (F5) | `InstructorHome.jsx` | `GET /api/v1/instructor/risks` | Danh sách SV nguy cơ trễ kèm lý do cụ thể |
| Chi tiết 1 case | mới (chưa có UI — "Risk Case Detail" là 1 Critical Gap đã biết) | `GET /api/v1/instructor/risks/{risk_id}` | Cần dựng thêm màn/drawer chi tiết — xem spec Drawer ở `docs/frontend/03_COMPONENT_SPECIFICATIONS.md` |
| **Đánh dấu đã can thiệp (HITL — chắc chắn bị chấm)** | `InstructorHome.jsx` | `POST /api/v1/instructor/risks/{risk_id}/intervention` | GV bấm nút, chọn hành động (vd "Đặt lịch gặp"), ghi chú → gọi API → **API này không gửi bất cứ thông báo nào cho SV**, chỉ đổi trạng thái nội bộ — giữ đúng nguyên tắc "hệ thống không tự động gửi gì cho SV" |
| **Xác nhận 11/08/2026 — Guardrail review queue LÀ tính năng thật đã thiết kế xong, không phải nghi vấn:** đọc lại `frontend/src/context/CursusContext.jsx` (`sendAppeal`/`resolveAppeal`/`queue`) xác nhận đây là luồng SV bị chặn → bấm "Yêu cầu xem xét lại" → vào hàng đợi GV → GV duyệt bỏ chặn hoặc giữ chặn. UI 2 phía đã hoàn chỉnh (`StudentHome.jsx` + `InstructorHome.jsx`), **chỉ thiếu endpoint backend** — chưa tồn tại trên bất kỳ branch nào | Cần xây mới: `POST /api/v1/qa/{message_id}/appeal`, `GET`/`PATCH /api/v1/instructor/guardrail-queue/{id}` — việc phối hợp giữa Hải Anh và Bình, xem chi tiết ở `roles/HAIANH_student.md` mục 5.3 và `roles/BINH_instructor.md` mục 5.3 |

---

## 3. Lịch gắn với ngày thật (dùng mốc ngày ở `03-Cursus-Execution-Plan.md`, gắn tên người)

| Ngày | Đăng | Hải Anh | Chung | Bình |
|---|---|---|---|---|
| **11/08 (T3, hôm nay)** | Bắt đầu Job #0: tạo branch tích hợp, copy `src/` từ `chung`, cấu hình `.env` Postgres/Redis thật | Đọc mục 6 (bảng endpoint), polish UI `StudentHome.jsx`/`StudentReflection.jsx` theo design system trong lúc chờ | Đọc mục 6, bắt đầu thiết kế `src/api/admin.py` (chưa cần chạy được, viết schema/route trước) | Đọc mục 6, polish UI `InstructorHome.jsx`, phác thảo màn Risk Case Detail còn thiếu |
| **12/08 (T4)** | Hoàn tất Job #0 — backend chạy độc lập, Swagger `/docs` xác nhận đủ router, login thật trả JWT | Bắt đầu nối `lib/api.js` mới vào `StudentHome.jsx` cho F2 (generate/accept plan) | Viết logic `admin.py` (courses + kpi), nối `chunk_repository`/`document_ingest_service` | Nối `InstructorHome.jsx` vào `GET /instructor/dashboard` + `/risks` |
| **13/08 (T5) — mục tiêu "1 flow hoàn chỉnh"** | Sửa lỗi tích hợp phát sinh, hỗ trợ cả 3 người nối API, deploy thử lên Railway/Vercel | Hoàn thiện F2 nối xong + bắt đầu F3 (Q&A) | Hoàn thiện `admin.py`, nối UI Admin Console vào API thật | Nối xong `POST .../intervention` (HITL) — đây là mảnh ghép cuối của luồng demo chính (mục 4) |
| **14/08 (T6 — Gate 2)** | Sáng: freeze code, chỉ sửa lỗi chặn demo | Cùng sửa lỗi cuối phần SV | Cùng sửa lỗi cuối phần Admin | Cùng sửa lỗi cuối phần GV |
| **15-22/08 (Mốc 3)** | Auth 3 role thật (đã có MFA sẵn từ Job #0, chỉ cần bật UI), ingest mở rộng ~10 môn, kiến trúc chịu tải, load test | F2/F3/Reflect hoàn thiện theo checklist `08_SCREEN_CONSISTENCY_CHECKLIST.md`, RAGAS phối hợp cùng Đăng | Admin Console đầy đủ CRUD ingest qua UI, Rule Engine thật nếu kịp | Risk Case Detail hoàn chỉnh, guardrail review queue (nếu xác nhận cần), test kịch bản lỗi cho GV |
| **23/08 (nộp bài)** | Freeze, rượt demo lần cuối, nộp | — | — | — |

---

## 4. "1 flow hoàn chỉnh" cho Thứ Năm 13/08 — Definition of Done

Chọn **1 luồng xuyên suốt cả 4 vai trò** làm mục tiêu chung ngày T5, thay vì mỗi người xong việc riêng mà không ai test nối liền:

1. SV đăng nhập thật (Đăng — Job #0 + F1) →
2. SV tạo kế hoạch tuần, nhận task có trích nguồn (Hải Anh — F2) →
3. SV hỏi 1 câu học thuật, nhận trả lời có trích nguồn; hỏi 1 câu "làm hộ bài" và bị guardrail chặn đúng (Hải Anh — F3) →
4. GV mở dashboard, thấy % hoàn thành lớp cập nhật + thấy SV này trong danh sách rủi ro nếu có (Bình — F4/F5) →
5. GV bấm "Đánh dấu đã can thiệp" cho 1 case, xác nhận trạng thái đổi, xác nhận SV không nhận được thông báo tự động nào (Bình — F5/HITL) →
6. Admin mở console, thấy đúng danh sách môn đã ingest + số liệu KPI (Chung — F6/F7).

**Chạy được hết 6 bước trên 1 lần liên tục, không lỗi, không cần restart server = đạt mục tiêu Thứ Năm.** Đây cũng chính là khung kịch bản demo chính sẽ dùng cho Gate 2 và Demo Day — làm đúng lần này đỡ phải dựng lại kịch bản demo sau.

---

## 5. Quy tắc phối hợp (tránh giẫm chân, tránh xung đột merge)

1. Mỗi người chỉ sửa file trong thư mục role của mình (`components/student/`, `components/instructor/`, `components/admin/`) + file API tương ứng trong `src/api/`. Sửa `index.css`, `components/shared/`, `context/` dùng chung → báo Đăng trước, không tự ý đổi (đây là design system/hạ tầng chung, đổi lệch sẽ vỡ đồng bộ 4 màn).
2. Trước khi tạo endpoint mới, tra bảng phụ lục mục 6 — phần lớn đã có sẵn trên `chung`, đừng viết lại trùng.
3. Đăng review mọi PR trước khi merge vào nhánh tích hợp chính — đối chiếu `docs/frontend/00_AI_CONTEXT_PACK.md` (token/motion/a11y) và `docs/frontend/08_SCREEN_CONSISTENCY_CHECKLIST.md`.
4. Phát hiện việc trùng lặp với người khác (như Chung/Bình cùng đụng `AdminConsole.jsx`) → dừng lại, nhắn trong nhóm, không code đè lên nhau âm thầm.
5. Cuối mỗi ngày, mỗi người tự thêm 1 dòng vào `WORKLOG.md` — đừng để dồn cuối tuần (đã có tiền lệ dựng lại từ git log, dễ sai sót).
6. **Tick tiến độ vào đúng file của mình** trong `docs/archive/planning-v2/progress/` mỗi khi 1 việc đã test thật xong, commit ngay — đây là cách nhóm trưởng biết ai tới đâu mà không cần hỏi (`make progress` để xem bảng tổng, `docs/archive/planning-v2/progress/README.md` để biết quy tắc tick). Khi cả 4 người cùng xanh 1 cột sprint → đó là tín hiệu khách quan để merge/freeze, không phải cảm tính.

---

## 6. Phụ lục — Bảng endpoint thật đã có sẵn trên `origin/chung` (tra trước khi tự viết mới)

| Method | Path (prefix `/api/v1`) | File nguồn | Role gọi |
|---|---|---|---|
| POST | `/auth/register` (**đổi 12/08/2026: bắt buộc `invite_token`, không còn tự đăng ký mở — xem `ADR-007`**), `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/logout-all` | `auth.py` | Tất cả (register: chỉ người có invite hợp lệ) |
| POST | `/auth/demo-session` (**mới** — không cần mật khẩu, chỉ đăng nhập được vào 3 tài khoản mẫu trong tổ chức sandbox `cursus-demo`) | `auth.py` | Công khai |
| GET | `/auth/invites/{token}` (**mới** — tra cứu lời mời trước khi kích hoạt) | `auth.py` | Công khai |
| POST/GET | `/admin/invites` · DELETE `/admin/invites/{id}` (**mới** — Admin mời Teacher/Student/Admin, giới hạn trong tổ chức của chính mình) | `admin.py` | Admin |
| GET | `/admin/access-requests` (**mới**) | `admin.py` | Admin |
| POST | `/public/access-requests` (**mới** — form "Yêu cầu quyền truy cập cho tổ chức") | `public.py` | Công khai |
| GET | `/auth/me` (nay trả thêm `organization_id`/`organization_name`/`is_demo`), `/auth/sessions` | `auth.py` | Tất cả |
| DELETE | `/auth/sessions/{session_id}` | `auth.py` | Tất cả |
| POST | `/auth/mfa/totp/setup`, `/auth/mfa/totp/enable`, `/auth/mfa/disable`, `/auth/mfa/recovery-codes/regenerate` | `auth.py` | Tất cả (Mốc 3) |
| POST | `/auth/password/forgot`, `/auth/password/reset`, `/auth/password/change` | `auth.py` | Tất cả |
| POST | `/auth/email/verify`, `/auth/email/resend` | `auth.py` | Tất cả |
| GET | `/plans/timetable`, `/plans/weekly` | `plans.py` | Sinh viên |
| POST | `/plans/timetable/bootstrap`, `/plans/timetable/blocks`, `/plans/generate`, `/plans/accept` | `plans.py` | Sinh viên |
| PATCH | `/plans/timetable/blocks/{id}`, `/plans/tasks/{task_id}` | `plans.py` | Sinh viên |
| DELETE | `/plans/timetable/blocks/{id}` | `plans.py` | Sinh viên |
| POST | `/qa` | `qa.py` | Sinh viên |
| GET | `/student/dashboard`, `/student/courses`, `/student/courses/{id}`, `/student/assignments/{id}`, `/student/risks`, `/student/reflections` | `student.py` | Sinh viên |
| POST | `/student/courses/{id}/documents`, `/student/reflections/generate` | `student.py` | Sinh viên |
| DELETE | `/student/courses/{id}/documents/{doc_id}` | `student.py` | Sinh viên |
| GET | `/instructor/dashboard`, `/instructor/risks`, `/instructor/risks/{id}` | `instructor.py` | Giảng viên |
| POST | `/instructor/risks/{id}/intervention` | `instructor.py` | Giảng viên |
| GET | `/canvas/users/{id}`, `/canvas/courses`, `/canvas/courses/{id}`, `/canvas/courses/{id}/{users\|enrollments\|modules\|assignments\|files\|pages\|announcements\|quizzes}`, `/canvas/calendar_events` | `canvas_routes.py` | Nội bộ (mock LMS) |
| POST | `/canvas/courses/{id}/assignments/{aid}/submissions` | `canvas_routes.py` | Nội bộ |
| GET | `/audit/events` | `audit.py` | Admin |
| — | **Không có** `/admin/courses`, `/admin/kpi` | — | **Chung phải tự xây (mục 2.3)** |

**Chưa tồn tại ở đâu, cần xây mới (không phải "cần quyết định có làm không" — cả 2 mục đầu đã xác nhận là tính năng thật cần làm, chỉ chưa có backend):** endpoint appeal + guardrail-queue cho GV duyệt (mục 2.2/2.4, đã xác nhận thiết kế xong ở frontend), rule engine cấu hình được cho Admin (mục 2.3 — quyết định scope Gate 2 vs Mốc 3, xem `roles/CHUNG_admin.md` mục 5.3), notification/reminder 48h (đã ghi nhận là việc Mốc 3 trong `03-Cursus-Execution-Plan.md`).
