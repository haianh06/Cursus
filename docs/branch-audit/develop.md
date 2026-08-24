# Audit nhánh `develop` (worktree: `P-093-develop-worktree`)

> Tài liệu này được viết bằng cách đọc trực tiếp source code tại `D:\VINAI_Team_093\P-093-develop-worktree` (KHÔNG chỉnh sửa gì trong worktree đó). Mục tiêu: đủ chi tiết để dựng lại toàn bộ sản phẩm của nhánh này mà không cần đọc lại code gốc, phục vụ so sánh với nhánh `haidang2425` để quyết định merge.
>
> Lưu ý ngay từ đầu: `ARCHITECTURE.md` trong chính nhánh này đã **lỗi thời** — nó mô tả "LLM/RAG mới ở dạng khai báo cấu hình, chưa nối vào luồng xử lý", nhưng thực tế code (`src/services/llm.py`, `rag.py`, `qa_service.py`, `qa_answer_service.py`, `retrieval_service.py`, `guardrail_service.py`, hơn 80 file test) cho thấy pipeline RAG + guardrail + Q&A đã được cài đặt đầy đủ và có test bao phủ sâu. Tài liệu này ưu tiên sự thật trong code hơn docs có sẵn.

---

## 1. Tổng quan

**Sản phẩm:** Cursus — "AI Academic Companion" cho sinh viên ngành Software Engineering tại FPT University (curriculum `BIT_SE_K20D_K21A`). Đề tài gốc **EDU-01** (chương trình VinUni AI20K Build Phase). Nhóm: Group06 · Team093 (P-093), trưởng nhóm `haidang2425`.

**Vấn đề giải quyết:** sinh viên học nhiều môn, deadline dày, không có ai giúp lập kế hoạch tuần/theo dõi tiến độ/nhìn lại việc học; giảng viên không phát hiện sớm sinh viên có nguy cơ trễ deadline.

**Giải pháp** — chu trình **Plan → Do → Reflect** có AI hỗ trợ, cộng thêm một trợ lý hỏi-đáp (Q&A) bám sát tài liệu môn học (RAG, có trích nguồn, có guardrail chặn "làm hộ bài"). Mascot "Curi" xuất hiện xuyên suốt UI (màn hình loading, chat bubble, auth).

**3 persona:**
- **Student** — lập kế hoạch tuần, thời khoá biểu, tự học có Pomodoro, hỏi-đáp AI theo môn (Course Companion Chat), luyện tập (flashcard/MCQ), phản tư (reflection) cuối tuần, xem cảnh báo rủi ro của chính mình, quản lý bộ nhớ hội thoại (opt-in).
- **Instructor** — dashboard lớp (tỷ lệ hoàn thành đúng hạn), danh sách sinh viên có nguy cơ trễ (risk signals) kèm HITL (đánh dấu đã can thiệp), duyệt hàng đợi câu trả lời bị guardrail chặn (guardrail review queue), ghi nhận hoạt động lớp (class activity log), duyệt bộ đề luyện tập do AI sinh (practice set approval).
- **Admin** — quản lý danh mục môn học (thêm/ẩn/khôi phục), tải lên/thay thế/xoá tài liệu môn học (ingest vào RAG), cấu hình guardrail rules (bật/tắt từng rule), risk policy (ngưỡng cảnh báo, có versioning + audit "vì sao đổi"), mời người dùng (invite instructor/admin), quản lý user, xem audit log toàn hệ thống, cấu hình academic term/exam.

**Điểm khác biệt nổi bật so với "nhánh chuẩn" đoán được từ tên/thư mục:** Đây rõ ràng là nhánh `develop` **rộng và sâu hơn nhiều** so với những gì `ARCHITECTURE.md` của chính nó tự mô tả (tài liệu đó có vẻ được viết ở một thời điểm sớm hơn nhiều so với code hiện tại). Nhánh này có toàn bộ hệ thống RAG/Q&A + guardrail + admin console + risk policy + practice set generator + student memory (bộ nhớ hội thoại dài hạn) + self-study Pomodoro session — đều đã có migration, model, service, API, và test riêng. So với working directory hiện tại của repo chính (nhánh `haidang2425`, đang có các file như `AdminInstructor360.jsx`, `AdminDataRequests.jsx`, `InstructorQuizManager.jsx`, `ClassComparisonPanel.jsx`, `risk_signal_service.py`, `quiz_service.py`, `email_service.py`...), có thể suy đoán nhánh `haidang2425` tập trung mở rộng theo hướng **admin analytics/instructor tooling nâng cao (quiz, class comparison, instructor 360, data requests)**, trong khi nhánh `develop` tập trung sâu vào **lõi RAG Q&A + guardrail + risk policy + student self-study/memory** — hai nhánh có khả năng đã phát triển **cùng một số bảng DB** (`risk_signals`, `class_activities`, `guardrail_*`) theo hai hướng khác nhau, đúng như bối cảnh "phân kỳ xa, nhiều conflict" được mô tả.

---

## 2. Kiến trúc backend

### 2.1 Sơ đồ thư mục (`src/`)

```
src/
  main.py                # FastAPI app, đăng ký toàn bộ router, middleware, lifespan (warm RAG index)
  config.py               # Settings (pydantic-settings) — CORS, quota, secrets, feature flags
  paths.py                # đường dẫn file tĩnh (mock_data, uploads)
  academic/                # domain logic thuần (không phụ thuộc DB/HTTP)
    practice.py            # sinh câu hỏi luyện tập từ nội dung slide
    slots.py                # slot thời khoá biểu (weekday/slot_id)
    study_scheduler.py      # thuật toán xếp lịch tự học quanh giờ học chính khoá
  api/                     # FastAPI routers (1 file = 1 router, xem 2.3)
  db/
    connection.py           # engine/session factory
    models.py                # TOÀN BỘ ORM models (SQLAlchemy 2.0 Mapped), ~65 bảng
  knowledge/
    faq_bank.py, faq_entries.json   # FAQ tĩnh dùng để trả lời nhanh không tốn quota LLM
  prompts/                 # prompt templates (markdown) cho companion/qa/extraction
  repositories/            # data-access layer, 1 repo/aggregate, nhận Session qua constructor
  schemas/                 # Pydantic response/request models dùng chung (qa.py, self_study.py)
  security/                 # auth/permission/middleware layer (xem 2.4)
  services/                 # business logic (xem 2.2), gọi repositories + models trực tiếp
```

### 2.2 Luồng request điển hình

`main.py` mount middleware theo thứ tự (trong-ra-ngoài): `SecurityHeadersMiddleware → CsrfProtectionMiddleware → RateLimitMiddleware → RequestContextMiddleware → CORSMiddleware` (CORS phải ngoài cùng để preflight OPTIONS không rơi vào route handler thành 405). `lifespan()` gọi `rag.warm_index()` khi khởi động để build sẵn index FLM syllabus (~400 chunk) một lần lúc deploy thay vì để request đầu tiên của sinh viên phải chịu chi phí đó.

Luồng chuẩn: **router (`api/*.py`)** nhận request đã qua `Depends(require_roles(...))` (RBAC theo `UserRole`) → gọi **service** (business logic, ví dụ `QaAnswerService`, `WeeklyPlanService`) → service gọi **repository** (data access, ví dụ `ConversationRepository`, `PracticeSetRepository`) → repository thao tác **model** (SQLAlchemy ORM, `src/db/models.py`) qua `Session` lấy từ `Depends(get_db)`. Một số router gọi thẳng `db: Session = Depends(get_db)` và query model trực tiếp (không qua repo) cho các thao tác đơn giản (vd nhiều đoạn trong `student.py`, `instructor.py`).

Ví dụ cụ thể — luồng hỏi-đáp (`POST /api/v1/qa`):
1. `api/qa.py::ask_question` nhận `question`, `subject_code`.
2. Gọi `_ask_question()` nội bộ → dựng `QaAnswerService` (service chính, `services/qa_answer_service.py`, ~1300 dòng).
3. `QaAnswerService` gọi `GuardrailService` (`services/guardrail_service.py`) trước — nếu bị chặn (`BLOCKED`) thì trả câu trả lời an toàn ngay, ghi `GuardrailEvent`, KHÔNG gọi LLM.
4. Nếu qua guardrail: gọi `RetrievalService`/`rag.retrieve()` lấy chunk liên quan từ `document_chunks` (hoặc mock syllabus data), kiểm tra `llm_quota_ok` (`LlmQuotaUsage`, 5 lượt LLM thật/ngày/sinh viên — vượt quota thì hạ cấp về câu trả lời trích xuất (extractive), không chặn cứng).
5. Gọi `llm.py::invoke_with_model_fallback()` (Gemini qua `ChatGoogleGenerativeAI`, có fallback nhiều model) để sinh câu trả lời có trích dẫn.
6. Kiểm tra "grounding" (`_check_grounding`, `_grounding_overlap_ratio`) — câu trả lời phải bám sát chunk trích, tránh bịa.
7. Lưu `Message` (role ASSISTANT) + `RAGTrace` (chunk đã dùng) + `LLMUsageEvent` (chi phí/token).
8. Trả về `QaAnswer` (Pydantic, `schemas/qa.py`) gồm câu trả lời + danh sách citation.

### 2.3 Danh sách API endpoint (theo router, prefix `/api/v1`)

Ghi chú auth: hầu hết router có `dependencies=[Depends(require_roles(...))]` ở cấp router (áp dụng cho MỌI route trong file); ngoại lệ ghi riêng.

**`auth.py`** — prefix `/auth`, không yêu cầu role cố định (một số endpoint public, một số cần session hiện tại qua cookie).
| Method | Path | Mục đích |
|---|---|---|
| POST | `/auth/register` | Đăng ký bằng invite token |
| POST | `/auth/login` | Đăng nhập email/password, trả cookie access+refresh, hỗ trợ `remember_me` |
| POST | `/auth/google` | Đăng nhập/đăng ký qua Google (Supabase session id) |
| GET | `/auth/me` | Lấy profile hiện tại (dùng để bootstrap `App.jsx`) |
| PATCH | `/auth/me` | Cập nhật profile (full_name, major, student_code) |
| PUT | `/auth/me/preferences` | Lưu theme/language vào `users.preferences` (JSON) |
| GET/POST | `/auth/mfa/...` | TOTP MFA: status, setup, enable, regenerate recovery codes, disable |
| POST | `/auth/password/forgot` `/reset` `/change` | Quên/đặt lại/đổi mật khẩu |
| POST | `/auth/email/verify` `/resend` | Xác minh email |
| POST | `/auth/refresh` | Refresh access token bằng refresh token (rotation, phát hiện reuse) |
| POST | `/auth/logout` `/logout-all` | Đăng xuất 1 phiên / toàn bộ phiên |
| GET | `/auth/sessions` | Danh sách phiên đăng nhập (device) |
| DELETE | `/auth/sessions/{id}` | Thu hồi 1 phiên |

**`invitations.py`** — prefix `/auth/invitations`: `POST /accept` (chấp nhận lời mời bằng token).

**`public.py`** — prefix `/public`, không cần đăng nhập: `POST /access-requests` (form "yêu cầu cấp quyền" từ trang landing cho tổ chức muốn dùng thử).

**`student.py`** — prefix `/student`, role STUDENT.
| Method | Path | Mục đích |
|---|---|---|
| GET | `/student/dashboard` | Tổng hợp dashboard trang chủ SV |
| GET | `/student/courses`, `/courses/enrolled` | Danh sách môn học / môn đã đăng ký |
| GET | `/student/courses/{course_id}` | Chi tiết môn + tài liệu |
| GET/POST/DELETE | `/student/courses/{course_id}/documents...` | Xem/tải lên/xoá tài liệu do SV tự thêm cho môn |
| GET | `/student/lecture-plan`, `/lecture-plan/{id}`, POST `/lecture-plan/generate` | Kế hoạch buổi học theo tuần (khác với weekly plan assignment-based) |
| GET | `/student/knowledge-status` | Trạng thái đã ingest tài liệu RAG cho môn hay chưa |
| GET | `/student/assignments/{id}` | Chi tiết 1 assignment |
| GET | `/student/risks` | Cảnh báo rủi ro của chính SV đó |
| GET/POST | `/student/reflections...` | Xem trước câu hỏi phản tư, tóm tắt preview, lưu reflection, tiến độ tuần, sinh reflection tự động |

**`qa.py`** — prefix `/qa`, role STUDENT.
| Method | Path | Mục đích |
|---|---|---|
| POST | `/qa` | Hỏi 1 câu, trả lời đồng bộ có trích dẫn |
| POST | `/qa/stream` | Hỏi dạng streaming (SSE) |
| GET | `/qa/citations/{chunk_id}` | Xem chi tiết 1 chunk trích dẫn |
| POST | `/qa/messages/{message_id}/feedback` | 👍/👎 câu trả lời |
| GET/POST/DELETE | `/qa/conversations...` | CRUD hội thoại theo môn (`subject_code`, tối đa 10 thread/SV/môn) |

**`student_memory.py`** — prefix `/student/memory`, role STUDENT: `GET/PUT /consent` (opt-in bộ nhớ dài hạn), `GET ""` (danh sách memory entries), `DELETE /{entry_id}`, `DELETE ""` (xoá hết — "quên tất cả").

**`self_study.py`** — prefix `/student/self-study`, role STUDENT: `GET /upcoming`, `/weekly-stats`, `/sessions/active`, `POST /sessions` (bắt đầu phiên Pomodoro gắn với 1 schedule block), `GET /sessions/{id}`, `POST /sessions/{id}/abandon`.

**`semester.py`** — prefix `/student/semesters`, role STUDENT: `GET /catalog`, `/status`, CRUD `SemesterSetup` (tên kỳ học, ngày bắt đầu/kết thúc, danh sách môn, khung giờ tuần, ngày nghỉ) — dùng cho onboarding wizard.

**`plans.py`** — prefix `/plans`, role STUDENT.
| Method | Path | Mục đích |
|---|---|---|
| GET/POST/PATCH/DELETE | `/plans/timetable...` | Thời khoá biểu tự học (block lặp lại theo tuần, `recurrence_series_id`) |
| GET | `/plans/defer-reasons` | Danh sách lý do hoãn task (enum) |
| GET | `/plans/weekly` | Kế hoạch tuần hiện tại |
| POST | `/plans/generate` | AI sinh kế hoạch tuần từ syllabus |
| POST | `/plans/from-lectures`, `/from-reflection` | Sinh kế hoạch từ lecture plan / từ reflection tuần trước |
| POST | `/plans/accept` | Chấp nhận đề xuất kế hoạch |
| PATCH/DELETE | `/plans/tasks/{task_id}` | Cập nhật trạng thái/xoá 1 task |

**`practice.py`** — prefix `/practice`, role STUDENT: `GET /sets` (lấy bộ luyện tập theo course+week), `POST /sets` (yêu cầu AI sinh bộ mới nếu chưa có).

**`instructor.py`** — prefix `/instructor`, role INSTRUCTOR hoặc ADMIN.
| Method | Path | Mục đích |
|---|---|---|
| GET | `/instructor/dashboard` | % hoàn thành đúng hạn theo tuần, theo lớp (ẩn danh hoá) |
| GET | `/instructor/dashboard/export` | Xuất báo cáo dashboard |
| GET | `/instructor/risks`, `/risks/{id}` | Danh sách/chi tiết cảnh báo rủi ro SV |
| POST | `/instructor/risks/{id}/intervention` | Ghi nhận đã can thiệp (HITL — KHÔNG tự gửi gì cho SV) |
| GET | `/instructor/risks/{id}/interventions` | Lịch sử can thiệp |
| GET | `/instructor/kudos` | Danh sách SV đáng khen (tiến bộ tốt) |
| GET/POST | `/instructor/guardrail-reviews...` | Hàng đợi câu trả lời bị guardrail BLOCK — GV quyết định `KEPT_BLOCKED`/`UNBLOCKED` |
| GET/POST/PATCH/DELETE | `/instructor/class-activities...` | Ghi log hoạt động lớp (ASSIGNMENT/PROGRESS_TEST/LAB/OTHER theo ngày) |
| GET/PATCH/POST | `/instructor/practice-sets...` | Duyệt/sửa/approve/reject bộ luyện tập do AI sinh trước khi hiển thị cho SV |

**`admin.py`** — prefix `/admin`, role ADMIN.
| Method | Path | Mục đích |
|---|---|---|
| GET | `/admin/courses` | Danh mục môn học (bao gồm override thêm/ẩn) |
| GET | `/admin/kpi` | KPI tỷ lệ nộp đúng hạn có/không dùng Cursus |
| GET/PATCH | `/admin/guardrail-rules` | Xem/bật-tắt từng guardrail rule |
| POST | `/admin/guardrail-rules/restore-defaults` | Khôi phục rule mặc định |
| GET | `/admin/analytics/summary` | Tổng hợp phân tích |
| POST/DELETE/POST | `/admin/courses` (`create`/`hide`/`restore`) | Thêm/ẩn/khôi phục môn trong catalog |
| GET/POST/PUT/DELETE | `/admin/courses/{code}/documents...` | Quản lý tài liệu môn (ingest vào RAG) |
| GET/PUT | `/admin/academic-term` | Cấu hình kỳ học hiện hành (tuần học/tuần thi) |
| GET/PUT/DELETE | `/admin/courses/exams...` | Lịch thi (PE/FE) theo môn |

**`admin_users.py`** — prefix `/admin/users`: `GET ""` (danh sách user), `PATCH /{id}` (khoá/mở khoá, đổi role...).

**`admin_invitations.py`** — prefix `/admin/invites`: `GET ""`, `POST ""` (tạo lời mời), `POST /{id}/revoke`.

**`admin_policy.py`** — prefix `/admin/risk-policy`: `GET ""` (policy đang active), `GET /history` (lịch sử version), `POST /preview` (xem trước tác động thay đổi ngưỡng trước khi áp dụng), `POST` (tạo version mới, có `change_reason` bắt buộc), `POST` (kích hoạt 1 version).

**`admin_settings.py`** — prefix `/admin/settings`: `GET/PUT` cấu hình key-value chung (`AdminSetting`).

**`audit.py`** — prefix `/audit`, role ADMIN (+ có thể thêm role khác theo dependencies): `GET /events` — audit log toàn hệ thống (actor, event_type, decision, metadata).

**`canvas_routes.py`** — prefix `/canvas`, role ADMIN: mô phỏng API Canvas LMS (courses/users/enrollments/modules/assignments/submissions/files/pages/announcements/calendar_events/quizzes) — dùng làm **mock external system** để sinh dữ liệu demo/test, không phải LMS thật.

### 2.4 Security layer (`src/security/`)
- `tokens.py` — JWT access/refresh token, `token_family_id` để phát hiện refresh-token reuse (rotation).
- `passwords.py` — hashing (bcrypt/argon2 tuỳ cấu hình).
- `permissions.py` + `authorization.py` — `require_roles(*roles)` dependency dùng ở mọi router.
- `ownership.py` — kiểm tra SV chỉ truy cập được tài nguyên của chính mình (vd conversation, plan).
- `policy.py` — các policy chung (CSRF, session policy).
- `middleware.py` — `CsrfProtectionMiddleware`, `RateLimitMiddleware`, `RequestContextMiddleware`, `SecurityHeadersMiddleware`.
- `exception_handlers.py`, `logging.py`, `request_context.py`, `token_exceptions.py` — hạ tầng phụ trợ.

### 2.5 Services quan trọng (`src/services/`)

| File | Vai trò chính |
|---|---|
| `llm.py` | Cấu hình + gọi Gemini (`ChatGoogleGenerativeAI`) với `invoke_with_model_fallback()` — thử tuần tự nhiều model nếu model chính lỗi/quá tải. |
| `rag.py` | Index + retrieve nội dung syllabus (lexical TF-IDF + embedding backend), `warm_index()` chạy lúc boot, `retrieve(query, subject_code, k)`. |
| `retrieval_service.py` | `RetrievalService` — truy vấn `document_chunks` thật trong DB (khác `rag.py` là mock/syllabus tĩnh), re-rank ngữ nghĩa, dedupe, tính `score_chunk`. |
| `qa_service.py` | `QaService` — điều phối tầng cao cho luồng hỏi-đáp (routing câu hỏi, gọi các service con). |
| `qa_answer_service.py` | `QaAnswerService` (~1300 dòng, phức tạp nhất repo) — sinh câu trả lời cuối: guardrail gate → quota gate → retrieval → LLM/extractive → grounding check → soạn câu trả lời tự nhiên + trích dẫn. Có xử lý riêng cho câu hỏi "overview" (`_is_overview_question`), câu hỏi off-topic, và web search fallback. |
| `guardrail_service.py` | `GuardrailService`, `GuardrailDecision` — phân loại câu hỏi/câu trả lời `ALLOWED/LIMITED/BLOCKED` dựa trên `guardrail_rules.py` (rule engine tĩnh) + `GuardrailRule` DB (bật/tắt theo admin). |
| `guardrail_rules.py` | Định nghĩa các rule cụ thể (vd chặn yêu cầu "làm hộ bài", nội dung ngoài phạm vi học thuật). |
| `crisis_support.py` | Phát hiện dấu hiệu khủng hoảng tâm lý trong hội thoại, trả hướng dẫn hỗ trợ thay vì trả lời học thuật bình thường. |
| `off_topic_service.py` | Phát hiện câu hỏi lệch chủ đề môn học. |
| `conversation_intent_service.py`, `query_contextualization.py`, `query_normalization.py` | Tiền xử lý câu hỏi: nhận diện ý định, viết lại câu hỏi theo ngữ cảnh hội thoại trước đó, chuẩn hoá dấu tiếng Việt. |
| `companion_service.py` | Logic cho "Course Companion Chat" (chat theo môn, khác `qa.py` — có thể là luồng chat tự do hơn, có prompt `companion_v1.md`). |
| `student_memory_service.py` | Đọc/ghi `StudentMemoryEntry` (preference/weak_topic/strength_topic), tôn trọng `StudentMemoryConsent`. |
| `llm_quota_service.py` | Đếm/giới hạn 5 lượt gọi LLM thật/ngày/SV (`LlmQuotaUsage`), degrade về extractive khi vượt quota. |
| `token_budget.py` | Quản lý ngân sách token cho prompt (cắt bớt context). |
| `web_search_service.py` | Tìm kiếm web bổ sung khi RAG nội bộ không đủ (fallback nguồn). |
| `embedding_service.py` | Sinh embedding cho retrieval ngữ nghĩa. |
| `answer_format.py` | Định dạng câu trả lời cuối (markdown, citation numbering). |
| `qa_trace.py` | Ghi `RAGTrace`/`LLMUsageEvent` cho mỗi câu trả lời (phục vụ đánh giá/QA). |
| `faq_service.py` | Trả lời nhanh từ `knowledge/faq_entries.json` không tốn quota LLM. |
| `practice_generator.py`, `practice_set_service.py` | Sinh bộ câu hỏi luyện tập (MCQ/flashcard) từ slide, qua hàng đợi duyệt của giảng viên (`PracticeSet.status`). |
| `weekly_plan_service.py`, `planner.py`, `reflection.py` | Lõi chu trình Plan/Reflect: sinh kế hoạch tuần từ syllabus, xử lý phản tư cuối tuần. |
| `timetable_service.py`, `academic/study_scheduler.py`, `academic/slots.py` | Xếp lịch tự học quanh giờ học chính khoá, xử lý block lặp lại. |
| `lecture_plan_service.py` | Luồng kế hoạch buổi học độc lập thứ hai (timetable/lecture sessions) — theo comment trong `App.jsx`, đây là "second, independent plan-generation flow", KHÔNG nối vào PlanBuilder cũ. |
| `pomodoro.py`, `self_study_service.py` | Quản lý phiên Pomodoro tự học (`SelfStudySession`). |
| `risk_signal_service.py`, `risk_policy_service.py` | Tính toán cảnh báo rủi ro SV (LATE_SUBMISSION/ABANDONMENT/OVERLOAD/ACADEMIC_DECLINE/WEEKLY_GOAL_FAILURE) theo `RiskPolicy` đang active (có versioning). |
| `class_activity_service.py` | CRUD nhật ký hoạt động lớp do GV nhập tay (dùng để tính risk). |
| `admin_document_ingest_service.py`, `admin_ingest_runner.py`, `document_ingest_service.py` | Pipeline ingest tài liệu (upload → chunk → lưu `Document`/`DocumentChunk`, theo dõi qua `CourseIngestJob`). |
| `admin_read_service.py` | Đọc tổng hợp cho admin dashboard/KPI. |
| `audit_service.py` | Ghi `AuditLog` cho mọi hành động nhạy cảm (admin mutation, login...). |
| `auth_service.py`, `session_service.py`, `refresh_token_service.py`, `device_service.py`, `mfa_service.py`, `password_reset_service.py`, `email_verification_service.py` | Toàn bộ hạ tầng xác thực (JWT, phiên, MFA TOTP, quên/đổi mật khẩu, xác minh email). |
| `email_service.py`, `email_provider.py`, `smtp_email_service.py` | Gửi email (xác minh, reset mật khẩu, mời) qua SMTP/provider trừu tượng. |
| `notification_service.py` | Thông báo trong app (chuông thông báo ở `Topbar`). |
| `demo_data.py`, `student_mock_data_service.py` | Sinh dữ liệu demo cho tài khoản demo/onboarding nhanh. |
| `academic_term_service.py`, `semester_service.py` | Quản lý kỳ học (`AcademicTerm`) và setup kỳ học cá nhân SV (`SemesterSetup`). |
| `onboarding_status.py`, `course_topic_hints.py`, `conversation_service.py`, `chat_router_service.py`, `provider_errors.py`, `auth_exceptions.py`, `auth_dto.py`, `plan_store.py` | Các module hỗ trợ nhỏ hơn (routing chat theo nhiều "chatbot" con, DTO, xử lý lỗi provider LLM).

---

## 3. Data model & migrations

Toàn bộ model nằm trong **một file duy nhất** `src/db/models.py` (1004 dòng, ~65 bảng), không chia theo domain. Alembic có 21 file migration trong `migrations/versions/` (baseline + 20 incremental), theo timeline:

| Migration | Nội dung chính |
|---|---|
| `20260808_baseline_schema` | Toàn bộ schema gốc: users, sessions, invitations, verification_tokens, mfa_*, audit_logs, curriculum/program/course/section/module/lesson, documents/document_chunks, announcements, assignments/quizzes/rubrics/submissions, weekly_plans/daily_plans/schedule_blocks/study_tasks, conversations/messages/rag_traces/llm_usage_events/guardrail_events, weekly_reflections/risk_signals/instructor_interventions, rag_evaluation_*, guardrail_evaluation_*. |
| `20260813_guardrail_rules` | Bảng `guardrail_rules` (bật/tắt rule theo admin). |
| `20260815_admin_course_overlay` | Bảng `admin_course_overrides` (thêm/ẩn môn ngoài catalog gốc). |
| `20260816_guardrail_reviews` | Thêm cột HITL vào `guardrail_events`: `review_status`, `block_reason`, `blocked_answer`, `reviewed_by`, `reviewed_at`, `reviewer_note`. |
| `20260817_conversation_subject` | Thêm `subject_code` vào `conversations` (chat theo môn, đa thread). |
| `20260817_message_feedback` | Bảng `message_feedback` (👍/👎, unique theo message+student). |
| `20260817_student_memory` | Bảng `student_memory_consent` + `student_memory_entries`. |
| `20260818_llm_quota_usage` | Bảng `llm_quota_usage` (giới hạn 5 lượt LLM/ngày/SV). |
| `20260818_semester_setup` | Bảng `semester_setups`, `semester_courses`, `semester_week_slots`, `semester_exceptions`. |
| `20260819_academic_term` | Bảng `academic_terms`, `course_exams`, `course_exam_sessions`, `course_exam_session_students`. |
| `20260820_practice_sets` | Bảng `practice_sets`, `practice_items`. |
| `20260821_self_study_sessions` | Bảng `self_study_sessions` (Pomodoro). |
| `20260821_study_task_defer_reason` | Thêm `defer_reason_code`, `defer_note` vào `study_tasks`. |
| `20260821_user_onboarding_profile` | Thêm cột onboarding vào `users`. |
| `20260823_user_preferences` | Thêm `preferences` (JSON) vào `users` (theme/language/showMascot). |
| `20260824_admin_invites` | (liên quan `invitations` cho admin/instructor invite). |
| `20260825_admin_policy` | Bảng `risk_policies` (policy version). |
| `20260826_risk_policy_version_required` | Ràng buộc `policy_version` bắt buộc trên `risk_signals`. |
| `20260827_instructor_note_and_guardrail_extras` | Thêm `instructor_note` vào `risk_signals` + mở rộng guardrail. |
| `20260828_practice_item_source_document` | Thêm `source_document_id` vào `practice_items` (trích nguồn cho câu luyện tập). |
| `20260830_schedule_block_recurrence` | Thêm `recurrence_series_id` vào `schedule_blocks` (block lặp lại theo tuần). |

**Đặc điểm nổi bật của schema:**
- Không có RLS (Row-Level Security) ở tầng Postgres — mọi tenant-scoping làm ở tầng ứng dụng qua `security/ownership.py` (kiểm tra `student_id`/`instructor_id` khớp user hiện tại).
- `RiskPolicy` có **versioning tường minh** (`policy_version` là PK dạng string, `is_active` bool, `change_reason` bắt buộc, `created_by`) — mọi `RiskSignal` sinh ra đều gắn cứng `policy_version` đã dùng để tính, cho phép audit "vì sao cảnh báo này xuất hiện".
- `GuardrailEvent` đóng vai trò **HITL queue** — không tách bảng riêng, review status/nguồn quyết định nằm ngay trên bảng event.
- `MessageFeedback` (👍/👎) và `GuardrailEvent.review_status` là **2 luồng feedback độc lập**: một cho câu trả lời "được phép nhưng không tốt", một cho câu trả lời "bị chặn nhưng có thể chặn nhầm" — comment trong model nói rõ ý đồ thiết kế này.
- `StudentMemoryConsent` — **privacy-by-design, mặc định OFF**: không đọc/ghi bộ nhớ chéo phiên cho tới khi SV bật consent tường minh.
- `LlmQuotaUsage` — giới hạn cứng 5 lượt gọi LLM thật/ngày/SV là **quyết định sản phẩm** (comment trích dẫn "decision log #5"), vượt quota chỉ hạ cấp về extractive chứ không chặn cứng.
- `ScheduleBlock.recurrence_series_id` — cho phép sửa/xoá theo phạm vi "chỉ occurrence này" hay "toàn bộ series".
- `CourseIngestJob` theo dõi trạng thái pipeline ingest tài liệu bất đồng bộ (status, error, completed_at).
- `RAGEvaluationCase/Result` và `GuardrailEvaluationCase/Result` — hạ tầng eval offline có sẵn trong schema (khớp với thư mục `eval/` ở root và `scripts/eval_chatbot_quality.py`).

---

## 4. Tính năng đã hoàn thiện (theo persona)

### Student
| Tính năng | API | Trạng thái (test) | File chính |
|---|---|---|---|
| Đăng ký/đăng nhập/MFA/quên mật khẩu | `/auth/*` | Có test đầy đủ (`test_auth_module.py`, `test_mfa_module.py`, `test_password_reset_module.py`, `test_email_verification_module.py`) | `src/services/auth_service.py`, `mfa_service.py` |
| Onboarding + Semester setup wizard | `/student/semesters` | Có test (`test_semester.py`) | `SemesterSetupWizard.jsx`, `semester_service.py` |
| Lập kế hoạch tuần (Plan) | `/plans/*` | Có test (`test_plans.py`) | `StudentPlanner.jsx`, `weekly_plan_service.py` |
| Thời khoá biểu tự học + block lặp | `/plans/timetable*` | Có test (`test_timetable_module.py`) | `Timetable.jsx`, `timetable_service.py` |
| Kế hoạch hôm nay (Do) | (dùng chung `/plans`) | — | `TodayPlanScreen.jsx` |
| Tự học Pomodoro | `/student/self-study/*` | Có test (`test_self_study.py`, `test_pomodoro.py`) | `SelfStudySession.jsx`, `pomodoro.py` |
| Hỏi-đáp AI có trích nguồn (RAG) | `/qa`, `/qa/stream` | Test rất sâu (7+ file `test_qa_answer_service_*`, `test_qa_module.py`, `test_qa_error_handling.py`) | `CourseCompanionChat.jsx`, `qa_answer_service.py` |
| Guardrail chặn câu hỏi ngoài phạm vi/làm hộ bài | (nằm trong `/qa`) | Có test (`test_guardrail_service.py` ở services, `test_admin_guardrail.py` ở api) | `guardrail_service.py`, `guardrail_rules.py` |
| Bộ nhớ hội thoại dài hạn (opt-in) | `/student/memory/*` | Có test (`test_student_memory_module.py`, `test_student_memory_service.py`) | `student_memory_service.py` |
| Phản hồi 👍/👎 câu trả lời | `/qa/messages/{id}/feedback` | Có test (`test_message_feedback.py`) | `message_feedback_repository.py` |
| Phản tư cuối tuần (Reflect) | `/student/reflections/*` | Có test (`test_reflection_band.py`, `test_reflection_weekly_win.py`) | `StudentReflection.jsx`, `reflection.py` |
| Luyện tập (flashcard/MCQ) | `/practice/sets` | Có test (`test_practice_sets.py`, `test_practice_generator.py`) | `StudentPractice.jsx`, `practice_set_service.py` |
| Kế hoạch buổi học (lecture plan) — luồng thứ 2 độc lập | `/student/lecture-plan*` | Có test (`test_lecture_plan.py`) | `LecturePlanPanel.jsx`, `lecture_plan_service.py` |
| Xem cảnh báo rủi ro của bản thân | `/student/risks` | Chưa thấy file test riêng theo tên — có thể phủ gián tiếp qua `test_risk_signal_service.py` | `student.py` |
| Upload tài liệu môn (SV tự thêm) | `/student/courses/{id}/documents` | Có test (`test_student_upload.py`, `test_student_course_document.py`) | `student.py` |

### Instructor
| Tính năng | API | Trạng thái | File chính |
|---|---|---|---|
| Dashboard lớp (tỷ lệ hoàn thành, ẩn danh) | `/instructor/dashboard` | Có test trong `test_instructor.py` (đang bị sửa dở — xem git status `M tests/test_api/test_instructor.py`) | `InstructorHome.jsx`, `instructor.py` |
| Cảnh báo rủi ro SV + HITL intervention | `/instructor/risks*` | Có test (`test_risk_signal_service.py`, `test_risk_policy_service.py`) | `RiskCaseDrawer.jsx` |
| Hàng đợi duyệt câu trả lời bị guardrail chặn | `/instructor/guardrail-reviews*` | Có test (`test_guardrail_reviews.py`) | `GuardrailReviewQueue.jsx` |
| Nhật ký hoạt động lớp | `/instructor/class-activities*` | Chưa thấy file test API riêng tên `test_class_activity*` — cần xác nhận thêm | `InstructorClassActivityPanel.jsx`, `class_activity_service.py` |
| Duyệt bộ luyện tập AI sinh | `/instructor/practice-sets*` | Phủ gián tiếp qua `test_practice_sets.py`/`test_admin_document_ingest_service.py` | `InstructorPracticeQueuePanel.jsx`, `practice_set_service.py` |
| Kudos (SV tiến bộ tốt) | `/instructor/kudos` | Chưa thấy test riêng | `instructor.py` |

### Admin
| Tính năng | API | Trạng thái | File chính |
|---|---|---|---|
| Quản lý danh mục môn (thêm/ẩn/khôi phục) | `/admin/courses*` | Có test (`test_admin_course_crud.py`) | `AdminAcademicPanel.jsx` |
| Ingest tài liệu môn vào RAG | `/admin/courses/{code}/documents*` | Có test (`test_admin_document_ingest_service.py`) | `admin_document_ingest_service.py` |
| Cấu hình guardrail rule | `/admin/guardrail-rules*` | Có test (`test_admin_guardrail.py`, `test_guardrail_rule_repository.py`) | `guardrail_rule_repository.py` |
| Risk policy (versioning + preview) | `/admin/risk-policy*` | Có test (`test_admin_policy.py`) | `admin_policy.py`, `risk_policy_service.py` |
| Quản lý user | `/admin/users*` | Có test (`test_admin_users.py`) | `admin_users.py` |
| Quản lý lời mời (invite) | `/admin/invites*` | Có test (`test_admin_invitations.py`) | `admin_invitations.py` |
| Cài đặt hệ thống (key-value) | `/admin/settings` | Có test (`test_admin_settings.py`) | `admin_settings.py` |
| Audit log | `/audit/events` | Có test (`test_audit_module.py`) | `audit.py`, `audit_service.py` |
| Kỳ học/lịch thi | `/admin/academic-term`, `/admin/courses/exams` | Có test (`test_academic_calendar.py`) | `academic_term_service.py` |
| Mock Canvas LMS API | `/canvas/*` | Không có test riêng theo tên `test_canvas*` (dùng nội bộ để seed demo) | `canvas_routes.py` |
| KPI so sánh có/không dùng Cursus | `/admin/kpi` | Phủ gián tiếp qua `test_admin.py`/`test_admin_contracts.py` | `admin_read_service.py` |

**Ghi chú chung về test:** 100+ file test (`tests/test_api`, `tests/test_services`, `tests/test_security`, `tests/test_academic`, `tests/test_migrations`), độ phủ đặc biệt sâu cho luồng Q&A/guardrail (grounding, diacritics, quota, streaming, memory context safety đều có file test riêng) — đây là phần được đầu tư kỹ nhất trong nhánh này.

---

## 5. UI/UX chi tiết

### 5.1 Kiến trúc frontend
- React 18 + Vite (không phải Next.js dù `ARCHITECTURE.md` ghi vậy — đó là điểm docs lỗi thời khác). Router: `react-router-dom` (`BrowserRouter`), toàn bộ dashboard theo role được `React.lazy()` code-split (Student/Instructor/Admin không tải chung bundle).
- **State**: 3 context toàn cục — `CursusContext` (user hiện tại + notifications), `Gate2Context` (state nghiệp vụ của SV: plan/timetable, chỉ mount khi role student), `ThemeContext`/`LanguageContext` (theme sáng/tối, VI/EN). Không dùng Redux/Zustand.
- **i18n**: 2 file phẳng `locales/en.js`/`vi.js` (534 dòng mỗi file), `useLanguage()` hook trả `t(key)`.
- **Design system**: Tailwind CSS v4 (cấu hình kiểu CSS-first, `@import "tailwindcss"` + khối `@theme` trong `index.css`, KHÔNG có `tailwind.config.js` riêng). `index.css` (3098 dòng) định nghĩa toàn bộ design token qua CSS custom properties: `--accent`, `--brand-blue`, `--gold`, `--sidebar-bg`, bán kính (`--radius-sm/md`), shadow (`--shadow-elevation-1/2`), và **theme sáng/tối song song** (biến đổi giá trị token, không đổi class). Font chính: Geist/Inter.
- **Mascot "Curi"**: `CursusMascot.jsx` xuất hiện ở màn hình loading khởi động (`App.jsx`), nút chat nổi (`CuriChatLauncher.jsx`), auth screens — có nhiều "state" biểu cảm (`thinking`, `celebrate`).

### 5.2 App shell (`App.jsx`, 876 dòng)
- `Sidebar` — cố định 220px, nền navy đậm cố định (không đổi theo theme), menu theo role (`user.role === 'student' | 'instructor' | 'admin'`), có toggle ngôn ngữ + đăng xuất ở đáy.
- `Topbar` — hiển thị "học kỳ hiện tại", ô tìm kiếm (đang bị disable — "chưa hoạt động"), `NotificationsBell` (dropdown, đánh dấu đã đọc), toggle theme, toggle ngôn ngữ, avatar → điều hướng `/{role}/settings`.
- `AppShell` — dùng `IntersectionObserver` để active-highlight mục sidebar theo section đang cuộn (chỉ cho student). Bọc route con student trong `Gate2Provider`.
- Route bảo vệ qua `ProtectedRoute` (kiểm `authStatus` + `allowedRoles`), có `AuthedElsewhereRedirect` cho user đã đăng nhập mà vào lại route công khai.
- Có `ScrollManager` xử lý riêng hành vi cuộn khi refresh vs điều hướng nội bộ (tránh "nhảy" trang khi F5 một trang dài).
- Overlay loading khởi động có mascot + 3 icon nổi (sách, mũ tốt nghiệp, sparkles) + hiệu ứng bounce — chỉ hiện cho route không phải landing page (landing luôn render ngay lập tức cho khách ẩn danh).

### 5.3 Các màn hình chính (component-level)
- **`StudentHome.jsx`** — dashboard tổng quan SV (widget kế hoạch tuần, cảnh báo rủi ro cá nhân, tiến độ).
- **`StudentPlanner.jsx`** — màn lập kế hoạch tuần: form mục tiêu → gọi `POST /plans/generate` → hiển thị task được AI chia nhỏ từ syllabus kèm trích nguồn → `POST /plans/accept`.
- **`TodayPlanScreen.jsx`** — danh sách task hôm nay, đổi trạng thái (`PATCH /plans/tasks/{id}`), có `DeferTaskDialog.jsx` (chọn lý do hoãn từ `GET /plans/defer-reasons`).
- **`Timetable.jsx`** — lưới thời khoá biểu tuần, tạo/sửa/xoá block (form chọn "chỉ lần này" hay "toàn bộ chuỗi lặp" khi sửa/xoá recurrence).
- **`CourseCompanionChat.jsx`** — giao diện chat theo môn: sidebar danh sách thread (max 10/môn), khung chat streaming (`POST /qa/stream`), mỗi câu trả lời có `SourceDrawer.jsx`/`ProvenanceBadge.jsx` hiển thị trích dẫn, nút 👍/👎.
- **`CuriContextPanel.jsx`** — panel ngữ cảnh bên cạnh chat (có thể hiển thị memory/gợi ý).
- **`SelfStudySession.jsx`** — màn Pomodoro: đếm giờ, nút bắt đầu/huỷ phiên (`POST /sessions`, `/abandon`).
- **`SelfStudyReminder.jsx`** — banner/toast nhắc tự học sắp tới (poll `GET /upcoming`).
- **`StudentPractice.jsx`** — hiển thị bộ luyện tập MCQ/flashcard, gọi `POST /practice/sets` nếu chưa có bộ nào cho tuần đó.
- **`StudentReflection.jsx`** — form phản tư cuối tuần: xem preview câu hỏi (`GET /reflections/preview`), điền → xem tóm tắt preview → lưu (`POST /reflections`).
- **`SemesterSetupWizard.jsx`** — wizard nhiều bước: chọn kỳ học, môn học, khung giờ tuần, ngày nghỉ.
- **`LecturePlanPanel.jsx`** — luồng kế hoạch buổi học độc lập (không liên quan `StudentPlanner`).
- **`InstructorHome.jsx`** — dashboard GV: KPI lớp, danh sách rủi ro, click vào 1 case mở `RiskCaseDrawer.jsx` (chi tiết + ghi can thiệp).
- **`InstructorClassActivityPanel.jsx`** — bảng nhập log hoạt động lớp theo ngày/loại.
- **`InstructorPracticeQueuePanel.jsx`** — hàng đợi duyệt bộ luyện tập AI sinh (approve/reject/sửa từng câu).
- **`GuardrailReviewQueue.jsx`** (dùng chung, không nằm trong `instructor/`) — danh sách câu trả lời bị chặn, GV xem lý do + câu trả lời gốc, quyết định giữ chặn hay mở khoá.
- **`AdminAcademicPanel.jsx`** — CRUD danh mục môn, quản lý tài liệu (upload/replace/delete), cấu hình kỳ học/lịch thi.
- **`AdminConsole.jsx`** — shell cho các panel admin (users, invites, settings, guardrail rules, risk policy) — điều phối tab.
- **`SettingsScreen.jsx`** (326 dòng) — đổi theme/ngôn ngữ/font, đổi mật khẩu, MFA, quản lý phiên đăng nhập, xoá bộ nhớ AI (memory consent).
- **`LandingPage.jsx`** + `components/landing/*` — trang giới thiệu công khai: Hero, FeatureBento, GroundedQA (demo trích nguồn), Guardrail (demo chặn), LecturerHITL (demo can thiệp GV), Privacy, Sandbox (có thể là demo tương tác), Workflow, FAQ, TrustStrip, Footer.
- **`auth/*`** — LoginScreen, RequestAccessScreen (form liên hệ tổ chức), AcceptInviteScreen, DemoSelectRoleScreen (chọn vai trò để dùng thử demo instant), Forgot/ResetPassword, EmailVerificationScreen, OnboardingScreen (đăng nhập Google lần đầu qua Supabase client-side session).
- **`shared/*`** — `ApiErrorScreen`/`FatalErrorScreen`/`ErrorState`/`OfflineBanner` (xử lý lỗi mạng/server có cấu trúc rõ ràng theo nhiều trạng thái), `SeoManager`, `EmptyState`, `Skeleton` (loading state), `NotFoundPage`, `UnauthorizedPage`.

### 5.4 Luồng tương tác tiêu biểu (Q&A)
Người dùng gõ câu hỏi trong `CourseCompanionChat` → nhấn gửi → `sendCompanionMessage()`/`askQuestion()` (`lib/api.js`) gọi `POST /api/v1/qa` hoặc `/qa/stream` → hiển thị skeleton loading → nhận câu trả lời kèm mảng citation → render câu trả lời + `SourceDrawer` cho phép mở rộng xem đoạn trích gốc (`GET /qa/citations/{chunk_id}`) → người dùng có thể bấm 👍/👎 (`POST /qa/messages/{id}/feedback`).

---

## 6. Điểm mạnh / điểm yếu quan sát được

**Điểm mạnh:**
- Test coverage rất sâu cho lõi RAG/guardrail (7+ file test chỉ riêng cho `QaAnswerService`: grounding, quota, streaming, memory, diacritics, context safety) — cho thấy đây là phần được đầu tư kỹ, độ tin cậy cao để tham khảo khi merge.
- Migration timeline sạch, mỗi migration có tên mô tả rõ mục đích, theo đúng thứ tự thời gian, không thấy migration "sửa lại migration trước" kiểu vá lỗi.
- Comment code chất lượng cao, nhiều chỗ giải thích rõ **quyết định thiết kế** (vd `LlmQuotaUsage` giải thích tại sao 5/ngày, `MessageFeedback` giải thích khác biệt với `GuardrailEvent.review_status`, `recurrence_series_id` giải thích lý do tồn tại) — rất hữu ích cho việc merge vì hiểu được "tại sao", không chỉ "cái gì".
- Thiết kế privacy-by-design rõ ràng (`StudentMemoryConsent` mặc định off).
- Không có TODO/FIXME rải rác thể hiện nợ kỹ thuật bị bỏ quên — chỉ có vài chỗ dùng chuỗi `"TODO"` như một giá trị enum status hợp lệ, không phải ghi chú việc chưa làm.
- Frontend có xử lý lỗi mạng/server rất bài bản (nhiều trạng thái auth: `initializing/unauthenticated/authenticated/email_unverified/error/session_expired`, `ApiErrorScreen`, `OfflineBanner`, `ConnectionBanner`).

**Điểm yếu / rủi ro:**
- `ARCHITECTURE.md` và có thể các docs khác trong `docs/` **lỗi thời nghiêm trọng** — mô tả sai hoàn toàn mức độ hoàn thiện của RAG/guardrail/admin console. Bất kỳ ai đọc docs trước code sẽ hiểu sai bức tranh. Cần cảnh báo rõ khi dùng tài liệu này để merge.
- Model tập trung 100% vào 1 file `models.py` (1004 dòng, ~65 bảng) — không chia theo domain, dễ conflict khi merge với nhánh khác cũng sửa `models.py` (đúng như bối cảnh 141 file conflict).
- Một số route gọi thẳng `db: Session` + query ORM trực tiếp trong file API (`student.py`, `instructor.py`) thay vì luôn qua repository — không nhất quán về layering giữa các module.
- `qa_answer_service.py` rất lớn (~1300 dòng, nhiều hàm module-level lẫn method trong class) — độ phức tạp cao, rủi ro khi cần merge logic tương tự từ nhánh khác.
- Không thấy rõ RLS/tenant isolation ở tầng DB — toàn bộ dựa vào tầng ứng dụng (`ownership.py`), nếu 1 endpoint quên gọi check sẽ là lỗ hổng (không đánh giá được có xảy ra hay không trong phạm vi audit đọc code này).
- File `tests/test_api/test_instructor.py` trong git status của repo hiện tại (`P-093`, không phải worktree develop) đang bị sửa dở (`M`) — không liên quan trực tiếp worktree develop nhưng đáng lưu ý vì tên trùng.
- 2 luồng "kế hoạch" song song không liên kết với nhau (`StudentPlanner`/weekly plan dựa trên assignment vs `LecturePlanPanel`/lecture plan dựa trên buổi học) — theo đúng comment trong `App.jsx` là cố ý ("coexists... never wired into it"), nhưng có thể gây khó hiểu cho người dùng cuối và là điểm cần quyết định khi merge (giữ cả 2 hay hợp nhất).
- Mock Canvas LMS (`canvas_routes.py`) tồn tại như 1 router đầy đủ nhưng không có test riêng — không rõ mức độ được dùng thật trong luồng chính hay chỉ để seed dữ liệu.

---

## 7. Danh sách file quan trọng

### Backend — core
- `D:\VINAI_Team_093\P-093-develop-worktree\src\main.py` — khởi tạo FastAPI app, đăng ký toàn bộ router + middleware.
- `D:\VINAI_Team_093\P-093-develop-worktree\src\config.py` — Settings toàn cục (CORS, quota, secrets).
- `D:\VINAI_Team_093\P-093-develop-worktree\src\db\models.py` — TOÀN BỘ ORM model (~65 bảng), file quan trọng nhất để hiểu schema.
- `D:\VINAI_Team_093\P-093-develop-worktree\src\db\connection.py` — engine/session factory.

### Backend — API routers
- `src\api\auth.py`, `auth_schemas.py` — toàn bộ xác thực.
- `src\api\student.py`, `student_memory.py`, `self_study.py`, `semester.py`, `plans.py`, `practice.py`, `qa.py` — API dành cho SV.
- `src\api\instructor.py` — API dành cho GV.
- `src\api\admin.py`, `admin_users.py`, `admin_invitations.py`, `admin_policy.py`, `admin_settings.py`, `admin_schemas.py`, `admin_policy_schemas.py` — API dành cho Admin.
- `src\api\audit.py`, `audit_schemas.py` — audit log.
- `src\api\canvas_routes.py` — mock Canvas LMS.
- `src\api\public.py`, `invitations.py` — API công khai/mời.
- `src\api\academic_schemas.py`, `practice_schemas.py`, `semester_schemas.py` — Pydantic schema riêng theo domain.

### Backend — services trọng yếu
- `src\services\qa_answer_service.py` — lõi sinh câu trả lời Q&A (file phức tạp nhất repo).
- `src\services\qa_service.py`, `retrieval_service.py`, `rag.py`, `llm.py` — pipeline RAG.
- `src\services\guardrail_service.py`, `guardrail_rules.py` — guardrail.
- `src\services\risk_signal_service.py`, `risk_policy_service.py` — cảnh báo rủi ro.
- `src\services\weekly_plan_service.py`, `timetable_service.py`, `reflection.py`, `lecture_plan_service.py` — chu trình Plan/Do/Reflect.
- `src\services\student_memory_service.py`, `llm_quota_service.py` — bộ nhớ + quota.
- `src\services\practice_set_service.py`, `practice_generator.py` — luyện tập AI sinh.
- `src\services\auth_service.py`, `mfa_service.py`, `session_service.py`, `refresh_token_service.py` — hạ tầng auth.

### Backend — data
- `src\repositories\*.py` — 19 file repository, mỗi file tương ứng 1 aggregate (conversation, practice_set, risk_policy, student_memory, guardrail_rule, v.v.).
- `migrations\versions\*.py` — 21 file, xem bảng mục 3 để tra theo thời gian.

### Backend — tests (đối chiếu hành vi mong đợi)
- `tests\test_services\test_qa_answer_service_*.py` — 6 file test hành vi Q&A chi tiết nhất (grounding, quota, streaming, memory, diacritics, context safety).
- `tests\test_api\test_qa_module.py`, `test_qa_error_handling.py` — test API tầng HTTP cho Q&A.
- `tests\test_api\test_admin_*.py` — 7 file test cho toàn bộ admin console.
- `tests\test_api\test_instructor.py` — test dashboard/risk/guardrail-review GV.
- `tests\conftest.py`, `tests\support\api_demo_dataset.py` — fixture/dataset dùng chung cho test.

### Frontend — core
- `frontend\src\App.jsx` — routing + app shell (Sidebar/Topbar) + auth bootstrap.
- `frontend\src\lib\api.js` — toàn bộ hàm gọi API (938 dòng) — nguồn chính xác nhất để biết FE thực sự dùng endpoint nào.
- `frontend\src\context\CursusContext.jsx`, `Gate2Context.jsx` — state toàn cục.
- `frontend\src\index.css` — design token/theme system (3098 dòng).
- `frontend\src\locales\en.js`, `vi.js` — text UI thật (534 dòng mỗi file).

### Frontend — components theo persona
- `frontend\src\components\student\*.jsx` — 12 file (StudentHome, StudentPlanner, TodayPlanScreen, Timetable, CourseCompanionChat, CuriContextPanel, SelfStudySession/Reminder, StudentPractice, StudentReflection, SemesterSetupWizard, LecturePlanPanel, DeferTaskDialog).
- `frontend\src\components\instructor\*.jsx` — InstructorHome, InstructorClassActivityPanel, InstructorPracticeQueuePanel.
- `frontend\src\components\admin\*.jsx` — AdminAcademicPanel, AdminConsole.
- `frontend\src\components\GuardrailReviewQueue.jsx`, `RiskCaseDrawer.jsx` — component dùng chung nhưng gắn với luồng instructor.
- `frontend\src\components\auth\*.jsx` — 9 màn xác thực/onboarding.
- `frontend\src\components\landing\*.jsx` — 12 file trang giới thiệu công khai.
- `frontend\src\components\shared\*.jsx` — hạ tầng UI dùng chung (error states, skeleton, settings, mascot, chat launcher...).

### Docs có sẵn (đọc để lấy ngữ cảnh, không tin tuyệt đối)
- `README.md` — mô tả sản phẩm, bảng tính năng F1–F7, thông tin nhóm — khớp với code ở mức tổng quan.
- `ARCHITECTURE.md` — **LỖI THỜI**, mô tả sai mức độ hoàn thiện RAG/guardrail/admin.
- `DOCS_GUIDE.md`, `WORKLOG.md`, `JOURNAL.md`, `docs/` — chưa đọc chi tiết trong audit này do giới hạn thời gian; nên đọc `DOCS_GUIDE.md` trước nếu cần đối chiếu thêm, nhưng luôn xác nhận lại với code.
