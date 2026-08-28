# Checklist đồng bộ 3 role — trạng thái 28/08/2026 (sau khi gộp `origin/develop`)

> Mọi ô đã kiểm bằng code trên nhánh gộp, không dựa vào trí nhớ hay bản trước.
> Plan chi tiết kèm code: `docs/superpowers/plans/2026-08-26-dong-bo-3-role.md`
> Ledger thực thi: `.superpowers/sdd/2026-08-26-dong-bo-3-role/progress.md`
> Bản trước chụp tại `cc74d64` (11.5/14) — đã lỗi thời **theo hai chiều ngược nhau**:
> nó đánh ✅ cho việc merge vừa làm hỏng lại, và đánh ⬜ cho việc đã cố ý đóng phạm vi.

**Tiến độ: 12.5/14 — nhưng 2 task đã ✅ bị merge làm đứt lại, xem cảnh báo dưới.**
Ba task còn lại (10, 11, 12) **không phải việc còn treo** — đã quyết định không làm,
lý do ở ADR-021 và mục Known Limitations trong `README.md`.

| | |
|---|---|
| Nhánh | `merge/develop-openai-27aug` — `chung` + `origin/develop` |
| Thay đổi lớn | develop đổi cấu trúc (`src/` → `backend/src/`), gộp ai-service thành `ai_engine`, **đổi LLM từ Gemini sang gateway OpenAI** |
| Test | **620 passed · 7 skipped · 0 failed** (6 phút 18) |

> ### ⚠️ Con số "620 xanh" ở trên yếu hơn vẻ ngoài
> `.env` **không có `OPENAI_API_KEY`**, nên `has_configured_llm()` trả `False` và
> **mọi đường LLM đang chạy nhánh dự phòng tất định**. Test xanh chứng minh merge
> không gãy, **không** chứng minh đường AI chạy được. Cụ thể chưa được kiểm lần nào:
> bộ đo chi phí mới ở `ai_engine`, và `test_gate2_flow` (xanh chỉ vì không có hệ số
> nhân từ LLM — lỗi 225-vs-165 đang **ngủ**, không phải đã sửa).
>
> ### ⚠️ Hệ thống hiện cần **HAI** khoá, không phải một
> LLM sinh câu trả lời dùng **OpenAI** (`ai_engine`), nhưng **embedding vẫn dùng
> Gemini** (`embedding_service.py:22`, `models/gemini-embedding-001`, đọc
> `settings.google_api_key`). Bỏ `GOOGLE_API_KEY` **không làm hỏng gì lộ liễu** —
> `has_embedding_backend()` trả `False` và retrieval **âm thầm tụt về chỉ-từ-khoá**.
> Đó đúng là "naive RAG" mà PLO3 yêu cầu phải vượt qua. Xoay khoá Google thì phải
> thay khoá mới vào, đừng bỏ trống.

### Vừa làm xong 26/08 cuối ngày

| Việc | Nội dung | Test mới |
|---|---|---|
| **B5** | Chọn lớp ngay khi mời giảng viên. `OrgInvite.section_id` + migration `20260911_invite_section`; route mời kiểm lớp theo tổ chức (404) và chặn role không phải INSTRUCTOR (400); `AuthService.register` gán lớp ngay khi tài khoản được tạo, **chỉ khi lớp còn trống** | 5 |
| **D1+D2** | Bảng `ai_usage` + migration `20260912_ai_usage`; `AIUsageCallback` gắn vào `get_llm()`; 11 chỗ gọi LLM đều gắn nhãn `feature`; org/user lấy từ ngữ cảnh request | 16 |

---

## Phase 1 — Nối lại mạch đứt · 5/5 ✅

- [x] **Task 1 — Gắn `section_id` cho hội thoại** · `d012c40` `e5ad7f6`
  Hội thoại nay gắn vào lớp sinh viên đang học (ENROLLED). Điều kiện bắt buộc của Task 2/3.
- [~] **Task 2 — Ghi `GuardrailEvent` khi companion chat chặn** · `28ea303` → ⚠️ **ĐỨT LẠI 28/08**
- [~] **Task 3 — Ghi `GuardrailEvent` khi `/qa` chặn** · `215a8c5` → ⚠️ **ĐỨT LẠI 28/08**

  > 🔴 **Hồi quy do gộp `origin/develop`.** develop xoá hẳn tính năng chat cũ
  > (migration `20260910_remove_chatbot_feature`), kéo theo `qa_service.py`,
  > `companion_service.py` và `guardrail_event_recorder.py` — nơi `record_block()`
  > ghi `GuardrailEvent`. Kiểm trên nhánh gộp: `grep "GuardrailEvent(" src/` **không
  > còn kết quả nào**, trong khi ba nơi vẫn đọc nó (`instructor.py:704`,
  > `admin_overview_service.py:223`, `ownership_repository.py`).
  >
  > **Guardrail vẫn chặn đúng** — `cursus_chat.py:281` gọi `GuardrailService.evaluate()`
  > và ghi lại khi chặn, nhưng ghi vào **`AuditEvent`** (`GUARDRAIL_DECISION`), không
  > phải `GuardrailEvent`. Hậu quả: **hàng đợi duyệt guardrail của giảng viên (F5 HITL)
  > rỗng vĩnh viễn**, và Work Queue của Admin mất một nguồn.
  >
  > **Không thể chữa bằng cách cho hàng đợi đọc `AuditEvent`:** (a) audit không có
  > `section_id` nên không định tuyến được ca tới đúng GV đang dạy lớp đó;
  > (b) `review_status` cần sửa được (`PENDING`→`APPROVED`), mà audit log là bất biến
  > có chủ đích. Phải ghi `GuardrailEvent` thật trong nhánh `if decision.blocked:`.
  > Trở ngại duy nhất: helper `section_id_for()` đã bị xoá cùng các service cũ, phải
  > viết lại (tra `Enrollment` theo `enrolled_at` mới nhất). **Ước tính ~1 giờ.**
  > Chạm cả 3 role: màn hình của Bình (F5), file của Hải Anh (`cursus_chat.py`),
  > Work Queue của Chung — **báo cả nhóm, đừng ai lặng lẽ vá.**
- [x] **Task 4 — Chỉ tài liệu `PUBLISHED` mới vào RAG** · `99a2ade`
  Kiểm lại: `chunk_repository.py:89` đã là `!= "PUBLISHED": continue`.
- [x] **Task 5 — Ghi nhật ký 3 hành động đang mất dấu** · `e306184`
  - [x] GV mở chặn guardrail → `GUARDRAIL_REVIEW_DECIDED` (`instructor.py:779`)
  - [x] GV can thiệp lẻ
  - [x] SV tự xoá dữ liệu cá nhân (`student.py:789`)
- [x] **Đợt sửa sau review tổng** · `6428205` — ngoài kế hoạch, phát sinh từ review
  Bản ghi guardrail sống sót khi SV xoá thread · hàng đợi sắp theo `created_at` · thread
  "Hỏi nhanh" không bị xoá đầu tiên · `section_id_for` theo `enrolled_at` mới nhất

---

## Phase 2 — Admin cấp phát lớp học · 4/4 ✅ *(gốc của "3 role không đồng bộ")*

- [x] **Task 6 — Backend CRUD `CourseSection` + gán giảng viên** · `24013a0`
  `src/api/admin_sections.py` (238 dòng, 8 route). Migration `20260909_section_instructor_nullable`
  đổi `CourseSection.instructor_id` thành nullable — reviewer dựng lại DB NOT-NULL cũ để
  chứng minh `ALTER` chạy được (DB test dựng từ `models.py` nên test migration đơn thuần
  không chứng minh gì).
- [x] **Task 7 — Quản lý danh sách sinh viên trong lớp** · `8e61490`
  **Quyết định sản phẩm (user, 26/08):** bỏ SV khỏi lớp là **soft-delete**
  (`Enrollment.status = DROPPED`), giữ `enrolled_at`/`grade`. Đây là lần đầu `DROPPED`
  trở thành giá trị sống → đã vá 2 cổng truy cập: `chunk_repository.student_enrolled_in_course`
  và `quiz_repository.is_enrolled`.
- [x] **Task 8 — Bỏ `first_instructor_id()`** · `7aedc71`
  Hàm đã **xoá hẳn**. Lớp do wizard SV tạo giờ không gán ai, nổi lên Work Queue dạng
  `UNASSIGNED_SECTION`. Tác dụng phụ tốt: tổ chức có **0 giảng viên** trước đây không
  hoàn tất được semester setup (`LookupError`), giờ chạy được.
- [x] **Task 9 — Màn hình "Lớp học" + đặt lại mật khẩu** · `bfd2ff0` `058bc20`
  `AdminSections.jsx` (638 dòng): CRUD + modal roster + tìm kiếm. `POST /admin/users/{id}/reset-password`
  + nút trong `AdminUsers.jsx`. Link `UNASSIGNED_SECTION` → `/admin/governance/sections` giờ đã sống.

---

## Phase 3 — Admin nhìn thấy nhiều hơn · 0/3 🚫 **ĐÃ ĐÓNG PHẠM VI**

> Ba task dưới đây **không còn là việc treo**. Quyết định không làm, ghi ở **ADR-021**
> và mục **Known Limitations** (`README.md`). Giữ lại nguyên văn để biết đã cân nhắc
> những gì, không phải để ai đó nhặt lên làm tiếp.

- 🚫 **Task 10 — Instructor 360: bổ sung 4 mảng hoạt động của giảng viên** — *không làm: công lớn, không phục vụ F6/F7*
  Kiểm `cc74d64`: `admin_instructor360.py` vẫn **1 route** duy nhất (`/summary`),
  trong khi Student 360 có 15. Cần thêm 4 route:
  - `GET /admin/instructors/{id}/class-activities` — nhật ký buổi học
  - `GET /admin/instructors/{id}/quizzes` — quiz đã tạo/publish
  - `GET /admin/instructors/{id}/practice-reviews` — duyệt bộ luyện tập
  - `GET /admin/instructors/{id}/guardrail-decisions` — đã mở chặn câu nào
  Files: `admin_instructor360.py` · `AdminInstructor360.jsx` · `lib/api.js` · locales
  · test mới `test_admin_instructor360_activity.py`. **Cỡ: vừa.**

- 🚫 **Task 11 — Student 360: bộ nhớ AI, quiz, luyện tập** — *không làm. Lý do gốc "cần cho Task 12" đã tan vì Task 12 bị đóng*
  Kiểm `cc74d64`: `StudentMemoryEntry` **0** lần xuất hiện trong `admin_student360.py`.
  `StudentMemoryEntry` là dữ liệu cá nhân AI ghi nhớ về SV — **làm mảng này trước**,
  vì không có nó thì không xử lý được yêu cầu trích xuất dữ liệu (Task 12).
  - `GET /admin/students/{id}/memory` (qua `_audited_read`)
  - `GET /admin/students/{id}/quizzes`
  - `GET /admin/students/{id}/practice-sets`
  **Cỡ: vừa.** Phụ thuộc: nên làm **trước** Task 12.

- 🚫 **Task 12 — Đường vào DSAR: người dùng tự gửi yêu cầu dữ liệu** — *không làm. Tab đã gỡ khỏi nav (ADR-021). ⚠️ Không đồng nghĩa FR-1.3 đã xong — phạm vi xoá self-service vẫn thiếu `WeeklyPlan`/`StudyTask`/`GuardrailEvent` so với spec*
  Kiểm `cc74d64`: `grep "DataRequest(" src/` → chỉ có định nghĩa class ở `models.py:1085`.
  6 route admin (`list`/`process`/`reject`/`complete`/`delete-preview`/`delete-confirm`)
  đều là bên tiêu thụ → tab "Yêu cầu dữ liệu" **rỗng vĩnh viễn**, chỉ chạy nếu insert tay vào DB.
  - Tạo `src/api/data_requests.py`: `POST /me/data-requests` `{kind: EXPORT|DELETE, note}` → 201
  - `GET /me/data-requests`
  - Nút gửi yêu cầu trong `SettingsScreen.jsx`
  **Cỡ: nhỏ–vừa.** Giá trị demo cao: gỡ được một màn hình rỗng.

---

## Phase 4 — Đo chi phí/độ trễ AI · dữ liệu ✅ · màn hình ✅ **XONG**

- [x] **Task 13 Step 1-2 — Bảng `ai_usage` + ghi token/độ trễ mỗi lần gọi LLM** ✅ **XONG 26/08**
- [x] **Task 13 Step 3 — màn hình Admin đọc số** ✅ **XONG 27/08**
  `GET /api/v1/admin/ai-usage?days=` (`src/api/admin_ai_usage.py`) + panel `AdminAiUsage.jsx`
  (hàng tổng, bảng theo tính năng, biểu đồ cột theo ngày), nav nhóm Theo dõi, 12 test.
  Đặc tả đầy đủ: `docs/FEATURE_ADMIN_AI_USAGE.md`.
  ⚠️ Sau khi gộp develop, bộ ghi đã **viết lại** cho `ai_engine` (`record_llm_call()` bọc
  2 chỗ gọi `chat.completions.create`) vì `get_llm()` không còn. Đơn giá hai model gateway
  `pro/gpt-5.6-terra` / `pro/gpt-5.6-luna` **chưa có** — không nằm trên trang giá công khai
  nào, phải hỏi bên cấp gateway; tới lúc đó cột chi phí báo "chưa có đơn giá".

<details><summary>Ghi chú lúc thực thi D1+D2 (mở ra nếu cần sửa tiếp)</summary>

  **Cái bẫy đã tránh được:** 8/11 chỗ gọi dùng `.with_structured_output(...)`, cách gọi
  này trả về object đã parse nên `usage_metadata` phía người gọi là **mất**. Đọc ở phía
  người gọi thì 8/11 chỗ ghi ra 0 token mà không báo lỗi gì. Giải bằng callback của
  LangChain (nhận `LLMResult` thô ở tầng dưới, trước parser). Giả định "callback gắn lúc
  tạo client vẫn bắn qua `with_structured_output`" đã được ghim bằng test chạy model thật
  của langchain-core, không phải suy luận.

  **Org/user không luồn qua chữ ký hàm:** cả 11 chỗ gọi đều nằm trong helper không cầm
  `user` (`_from_llm`, `_generate_with_llm`...). Dùng `actor_org_id_var`/`actor_user_id_var`
  đặt tại `AuthService.get_current_user` — chốt chặn duy nhất mọi route xác thực đi qua.
  Không có bước này thì `organization_id` luôn NULL và bảng mới lặp lại đúng số phận
  `LLMUsageEvent`: có cột, không ai điền.

  **Phát hiện ngoài phạm vi:** `.env` đang bật `LANGCHAIN_TRACING_V2=true` với
  `LANGCHAIN_API_KEY=your-langsmith-key-here` (key giả). Mỗi lần gọi LLM thật đều POST
  hụt sang `api.smith.langchain.com` và nhận 403 — thêm độ trễ và rác log vào đúng thứ
  D1 đang đo. Chưa sửa: đây là quyết định cấu hình (bật LangSmith thật hay tắt hẳn).

</details>

  Kiểm trước khi làm (`cc74d64`): `grep -rn "ai_usage\|AIUsage" src/ migrations/` → **0 kết quả**.
  Đây là **vế duy nhất của PLO 5 đang trống** ("giám sát cơ bản: độ trễ/lỗi/chi phí"):

  | Vế | Trạng thái |
  |---|---|
  | lỗi | ✅ structured logging, ingest job status, cờ `degraded`, 4 field trace Option B |
  | độ trễ | ✅ `ai_usage.latency_ms` — đo riêng phần gọi LLM, không lẫn thời gian HTTP |
  | chi phí | ✅ `ai_usage.input_tokens`/`output_tokens`, tách theo `feature` và `organization_id` |

  Cả ba vế của PLO 5 nay đều có dữ liệu. Còn thiếu **màn hình** đọc số — nhưng đúng theo
  nguyên tắc "dữ liệu trước, UI sau", một câu SQL đã đủ trả lời khi bảo vệ:

  ```sql
  SELECT feature, COUNT(*) AS calls, SUM(input_tokens + output_tokens) AS tokens,
         ROUND(AVG(latency_ms)) AS avg_ms,
         SUM(CASE WHEN success THEN 0 ELSE 1 END) AS failures
  FROM ai_usage WHERE created_at >= NOW() - INTERVAL '30 days'
  GROUP BY feature ORDER BY tokens DESC;
  ```

  Việc nhỏ hơn tưởng: `ChatGoogleGenerativeAI` **đã trả sẵn `usage_metadata`** trên mỗi
  response, hiện bị vứt ngay tại chỗ nhận. Chỉ cần bọc `get_llm()` bằng callback +
  `perf_counter`, và một bảng mới.
  - Tạo `migrations/versions/20260908_ai_usage.py`, model `AIUsage`
    (`id, created_at, organization_id, user_id, feature, model, input_tokens,
    output_tokens, latency_ms, success`)
  - Tạo `src/services/core/ai_usage_recorder.py` → `record_usage(...)`
  - `GET /admin/ai-usage?days=30` → `{totals, byFeature, byDay}`

  > ⚠️ **Không tái dùng `RAGTrace`/`LLMUsageEvent`.** ADR-017 đã đóng 2 bảng đó có lý do:
  > FK `message_id` NOT NULL không khớp với `plan_builder`/`reflection_engine`, và
  > `LLMUsageEvent` **không có cột thời gian** nên không chia được theo kỳ. Bảng mới
  > phải có `created_at`, `organization_id`, và `message_id` nullable.

  **Ưu tiên có dữ liệu trước, màn hình sau** — có dữ liệu rồi thì kể cả chưa kịp dựng UI,
  một câu SQL cũng đủ trả lời khi bảo vệ. **Cỡ: vừa.**

---

## Phase 5 — Dọn dẹp · 2/2 ✅

- [x] **Task 14 Step 1-2 — Sửa 4 test đỏ** · `99a2ade`
  Xử lý theo hướng **khác và đúng hơn** so với plan: thay vì đổi 12 file sang schema `meta`,
  làm chặt bộ nhận diện trong `real_curriculum_service.py` — một file chỉ là syllabus chính
  thức khi có `meta` *và* ≥1 chunk `Session ...` không rỗng. Số môn giữ nguyên 34.
- [x] **Task 14 Step 3-6** · `138f1de`
  - [x] Dịch 6 nhãn sidebar giảng viên — kiểm lại `App.jsx`: **6/6** dùng `t()`
  - [x] Route Admin ghi `AdminAnnouncement`
        *(ngoài brief: bảng thiếu `organization_id` → thêm cột + migration `20260910_announcement_org`,
        lọc cả 2 đầu. Không có nó thì thêm route ghi = rò rỉ chéo tổ chức)*
  - [x] Lọc `failed_jobs` theo tổ chức *(phải `func.upper` hai vế vì `start_job` lưu mã hoa
        còn catalog thật có mã đuôi chữ thường)*

---

# Còn những nhiệm vụ gì — danh sách đầy đủ

## A. Trong plan — 4 task

| # | Task | Cỡ | Giá trị |
|---|---|---|---|
| 13 | ~~Đo chi phí/độ trễ AI~~ → chỉ còn **màn hình đọc số** | nhỏ | Dữ liệu đã có; SQL trả lời được, UI là để demo cho đẹp |
| 12 | Đường vào DSAR | nhỏ–vừa | Gỡ một màn hình rỗng khi demo |
| ~~11~~ | ~~Student 360 + bộ nhớ AI~~ | — | 🚫 đã đóng phạm vi (ADR-021) |
| ~~10~~ | ~~Instructor 360 đầy đủ~~ | — | 🚫 đã đóng phạm vi (ADR-021) |

## A-bis. Phát sinh sau khi gộp `origin/develop` (28/08) — **việc mới, chưa có trong plan gốc**

| # | Việc | Cỡ | Ai | Ghi chú |
|---|---|---|---|---|
| M1 | 🔴 **Nối lại `GuardrailEvent`** — ghi 1 hàng trong nhánh `if decision.blocked:` của `cursus_chat.py`, viết lại helper `section_id_for()` | ~1h | Bình (F5) + Hải Anh (file) | Chặn hàng đợi HITL của GV. Chi tiết ở Task 2/3 phía trên |
| M2 | 🔴 **Khoá `OPENAI_API_KEY` + `OPENAI_BASE_URL`** | — | Đăng | Không có thì mọi đường AI im lặng rơi vào nhánh dự phòng, **và test vẫn xanh** |
| M3 | **Giữ `GOOGLE_API_KEY` sống** — embedding vẫn dùng Gemini | — | Chung | Bỏ trống thì retrieval âm thầm tụt về chỉ-từ-khoá = naive RAG, đúng thứ PLO3 bắt phải vượt |
| M4 | **Viết ADR-022** — lật ADR-002 (Gemini → OpenAI) | 30' | Hải Anh nêu lý do, ai cũng viết được | Quyết định kiến trúc lớn nhất tuần này, hiện **không tồn tại trên giấy tờ** |
| M5 | **Đơn giá gateway** cho `pro/gpt-5.6-terra` / `pro/gpt-5.6-luna` | 5' | Đăng hỏi bên cấp gateway | Điền vào `src/services/core/ai_pricing.py`, cột chi phí sáng lên ngay |
| M6 | `test_gate2_flow` — lỗi 225-vs-165 **đang ngủ**, không phải đã sửa | 30' | Hải Anh | Xanh chỉ vì không có LLM nên không có hệ số nhân |

---

## B. Cố ý để ngoài plan — cần **quyết định** trước khi code

| Việc | Vì sao chưa làm |
|---|---|
| **RLS đa tổ chức (P0#3)** | `grep tenant_scope src/` → **0 kết quả**. `tenant_scope.py` viết xong nhưng chưa nối route nào; policy trong migration inert vì `app.current_org_id` không nơi nào set. Cách ly tổ chức hiện **100% dựa vào filter Python** — chạy đúng, nhưng một chỗ quên lọc là rò. Cần thao tác Supabase Dashboard + đổi `Depends(get_db)` → `get_scoped_db` trên 40+ endpoint. Kế hoạch riêng: `docs/decisions/rls-migration-plan.md` |
| **Báo cho SV biết đã được can thiệp** | **Quyết định sản phẩm:** có nên cho SV biết mình đang bị đánh dấu rủi ro không? `InstructorIntervention` chỉ được đọc ở 1 nơi (`gate2_demo.py:764`), không route SV nào đọc |
| **Admin xem ghi chú riêng của GV về SV** (`InstructorStudentNote`) | 🚫 **Đã quyết định KHÔNG mở** (ADR-021) — ghi chú riêng tư trong quan hệ dạy–học; có quyền kỹ thuật để đọc không có nghĩa là nên đọc |
| **5 bảng chết trong schema** (`ResourceAccessEvent`, `ReplanProposal`, `LearningGoal`, `ReminderDelivery`, `Rubric`) | Không đọc/ghi ở đâu. Xoá hay dùng đều cần quyết định riêng |
| **12 file `chunks_*.json` bị hệ thống bỏ qua** | Đã track trong git (`6ba3a17`) nhưng `real_curriculum_service` loại ra vì không phải syllabus thật (7 chunk, 0 section `Session`). SWT301, PEN, TMI_ELE... đều là **mã môn thật** — nếu định thêm 12 môn này thì đây là **hoãn lại, không phải xong**. Cần hỏi người tạo ra 12 file |

## C. Nợ kỹ thuật đã ghi nhận

| Việc | Mức |
|---|---|
| **20 chỗ query `Enrollment` chưa lọc `DROPPED`** (Task 7 deferred) — không cái nào là cổng truy cập hay rò chéo role: `student.py:62,186` + `timetable_service.py:287,517` tự-scope; `risk_engine.py:237,427` chấm điểm cũ trong chính lớp của SV; `admin_student360.py:147` + `admin_data_requests.py:148,208` cố ý lấy full-history; còn lại là mock/demo. Chỉ sai sau khi admin **chủ động** bỏ SV khỏi lớp | 🟠 |
| `admin_sections.serialize()` chạy 2 query thừa mỗi section dù `list_sections` đã join `Course` — N+1 trên endpoint list | 🟢 |
| `build_work_queue` query User theo từng dòng (N+1, có chặn trên) | 🟢 |
| `companion_service` truyền câu hỏi **đã chuẩn hoá** vào `record_block`, `qa_service` truyền **nguyên văn** — nên thống nhất về nguyên văn | 🟢 |
| `_visible_guardrail_events` `.limit(200)` **trước** khi lọc theo lớp | 🟢 |
| `semester_service` cho phép nhiều dòng ENROLLED cùng môn qua các kỳ | 🟢 |

## D. Rủi ro vận hành — **không phải task code, nhưng nghiêm trọng hơn**

| # | Việc | Mức |
|---|---|---|
| 1 | **`.env.bak` vẫn nằm trong lịch sử git, repo public trên GitHub.** Cả 2 nhánh đã gỡ file khỏi tree (`9650bfd`, `cf523b7`) nhưng credential **Google / Postgres / Redis / SMTP chưa được xoay**. Xoá file không giải quyết được gì khi lịch sử còn đó | 🔴 **cao nhất** |
| 2 | `scripts/seed_curriculum.py:281` gọi `path.unlink()` — chạy seeder trong repo chính sẽ **xoá 8 file `chunks_*.json` đang được git theo dõi** (COV111, COV121, COV131, DTR103, EXE401, PRN212, PRU221m, SBA301) | 🟠 |
| 3 | Merge `develop → haidang2425` mới chỉ xác minh trên **SQLite**. Chưa chạy lại trên Postgres | 🟠 |
| 4 | Chưa thử **SSO sang EduSync** — `mock_lms_sso.py` tự merge êm, nhưng develop sửa CSRF/cookie mà SSO phụ thuộc cookie. Đây là chỗ đáng nghi nhất còn lại | 🟠 |
| 5 | Chưa thử **đăng nhập Google** thật — chỉ test được đường demo không mật khẩu | 🟠 |
| 6 | `CursusContext.jsx` — file duy nhất giải conflict bằng tay, là **quyết định kiến trúc** chứ không phải lỗi merge. Cần rà cùng haianh06 | 🟢 |

## E. Việc về nhánh — merge còn treo

| Nhánh | Commit chưa có ở HEAD | Conflict (merge khô) | Ghi chú |
|---|---|---|---|
| `origin/main` | 2 (đều là merge commit) | **0 — sạch** | HEAD đi trước 324 commit; main chưa cập nhật từ 16/08. **Nên mở PR sớm** |
| `origin/thanhbinh` | 13 | 35 | Frontend instructor/student, nhiều modify/delete |
| `origin/chung` | 96 | 111 | Admin cũ (tab) vs admin mới (route), nhiều add/add |
| `origin/haianh` | 8 | 321 | Nhánh này đổi tên `src/` → `backend/` → gần như mọi file thành "file location" conflict. **Chốt sớm với haianh06** trước khi phân kỳ thêm |

---

## Thứ tự đề nghị

| Bước | Việc | Vì sao xếp ở đây |
|---|---|---|
| **0** | **Xoay credential** (mục D.1) | Không phải code, nhưng là rủi ro thật đang mở. Làm ngay |
| **1** | **PR `haidang2425` → `main`** | 0 conflict, mà main đang tụt 10 ngày. Rẻ nhất trong danh sách |
| **2** | ~~**Task 13**~~ ✅ xong phần dữ liệu — còn màn hình, hạ xuống cuối |
| **3** | **Task 11 → 12** | Làm 11 trước: bộ nhớ AI là thứ Task 12 cần để trả lời yêu cầu trích xuất |
| **4** | **Task 10** | Hoàn thiện quan sát. Thiếu vẫn bảo vệ được |
| **5** | Xác minh Postgres + SSO + Google (D.3-5) | Trước lúc demo, không phải bây giờ |
| **6** | Chốt 3 quyết định ở mục B | Cần người quyết, không cần lập trình viên |

**Nếu thời gian rất hẹp:** bước 0 (xoay credential) → 1 (PR lên main) rồi dừng.
Tiêu chí chấm điểm (PLO 5) nay đã có đủ dữ liệu; Task 10/11/12 và màn hình `ai-usage`
là phần hoàn thiện, thiếu vẫn bảo vệ được.

> **Việc mới phát sinh, chưa có trong bảng nào ở trên:** đợt B5 + D1/D2 hiện **chưa commit**.
> Xem mục D.1 — cùng một bài học: thứ chưa vào git là thứ có thể mất.
