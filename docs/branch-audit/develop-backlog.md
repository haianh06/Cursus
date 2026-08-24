# Backlog: tính năng riêng của `develop` chưa port sang `haidang2425`

Bối cảnh đầy đủ: [develop.md](develop.md) (audit kiến trúc/tính năng đầy đủ của
nhánh `develop`) và [haidang2425.md-in-progress] (agent đang ghi, xem sau).

## Vì sao không merge thẳng

`haidang2425` đưa vào kiến trúc multi-tenant (`organizations`,
`organization_id`, RLS) mà `develop` hoàn toàn không có — migration chain của
2 nhánh **fork tại `20260813_guardrail_rules`** (trùng revision id, khác
`down_revision`). Toàn bộ tầng data-layer của `develop` (repositories,
services thao tác DB) viết cho schema không-tenant, không tương thích thẳng
với DB hiện tại. Ví dụ cụ thể: file `chunks_*.json` (RAG source data) của 2
nhánh dùng 2 schema JSON khác nhau hoàn toàn.

**Quyết định (2026-08-24):** giữ kiến trúc/schema của `haidang2425` làm nền,
merge git history để không mất mốc thời gian, nhưng **loại bỏ code/data
không tương thích của `develop`** khỏi merge thay vì cố hợp nhất mù. Danh
sách dưới đây là để port lại có chủ đích sau, không phải để phục hồi nguyên
xi (cần viết lại cho tenant-aware).

## Tính năng đáng port lại (theo giá trị, ước lượng)

1. **`student_memory`** (`src/services/student_memory_service.py`,
   `repositories/student_memory_repository.py`, migration
   `20260817_student_memory.py`) — bộ nhớ hội thoại dài hạn, opt-in, dùng cho
   companion chat nhớ ngữ cảnh qua nhiều phiên. `haidang2425` hiện chưa có gì
   tương đương.
2. **`llm_quota_service`** (`src/services/llm_quota_service.py`,
   `repositories/llm_quota_repository.py`, migration
   `20260818_llm_quota_usage.py`) — giới hạn số lần gọi LLM/user, tránh lạm
   dụng chi phí Gemini API. `RateLimitMiddleware` của `develop` (xem diff bị
   revert trong lần merge này) có logic per-endpoint rate limit riêng cho
   `/qa`/`/qa/stream` dựa vào field `Settings.chat_rate_limit_requests` —
   đáng tham khảo khi làm lại.
3. **Tầng QA/RAG sâu hơn** (`qa_answer_service.py` ~1300 dòng ở `develop`,
   có test riêng cho grounding/quota/streaming/memory — 6 file
   `test_qa_answer_service_*.py`) — so với `qa_answer_service.py` hiện tại
   của `haidang2425` (`src/services/ai/qa_answer_service.py`), cần **đối
   chiếu tính năng cụ thể** (không giả định bên nào "hơn" toàn diện) trước
   khi port bất kỳ phần nào.
4. **`message_feedback`** (`repositories/message_feedback_repository.py`,
   migration `20260817_message_feedback.py`, `tests/test_api/
   test_message_feedback.py`) — thumbs up/down cho câu trả lời AI, chưa có ở
   `haidang2425`.
5. **`crisis_support.py`, `off_topic_service.py`, `query_contextualization.py`,
   `answer_format.py`, `token_budget.py`, `pomodoro.py`** — các service nhỏ,
   độc lập, rủi ro thấp khi port (không đụng schema tenant). Đáng xem xét
   sớm nếu cần.
6. **`self_study` module** (API + service + repository + migration
   `20260821_self_study_sessions.py`) — phiên tự học có nhắc nhở
   (`SelfStudyReminder.jsx`, `SelfStudySession.jsx`, `Timetable.jsx`,
   `TodayPlanScreen.jsx` ở frontend, hiện đang nằm orphaned/chưa xóa trong
   `frontend/src/components/`) — cạnh tranh chức năng với
   `src/academic/study_scheduler.py` của `haidang2425`; cần so sánh 2 cách
   tiếp cận trước khi chọn 1.
7. **`admin_invitations.py`/`admin_policy.py`/`admin_users.py`** — có thể đã
   trùng chức năng với `src/api/admin.py` của `haidang2425` (invites, user
   status, guardrail rules) — cần audit trùng lặp trước khi port, không port
   nguyên xi.

## Đã loại bỏ vĩnh viễn khỏi cây (không đáng port)

- 16 migration riêng của `develop` (conversation_subject, semester_setup,
  academic_term, practice_sets, self_study_sessions, study_task_defer_reason,
  user_onboarding_profile, user_preferences, admin_invites, admin_policy,
  risk_policy_version_required, practice_item_source_document,
  schedule_block_recurrence...) — xung đột trực tiếp với migration chain của
  `haidang2425` (đa số tính năng tương đương đã có, viết lại tenant-aware,
  trong `20260821_semester_practice.py` và các migration sau).
- 16 file `src/services/*.py` phẳng trùng tên với bản đã tổ chức lại của
  `haidang2425` dưới `academic/`, `ai/`, `core/`, `rag/` (vd
  `companion_service.py`, `risk_policy_service.py`, `semester_service.py`).
- 12 file `docs/planning/v2/data/chunks_*.json` cho môn học mới — dùng schema
  JSON khác (`{chunks: [...]}` thay vì `{meta: {...}, ...}`) không tương
  thích với parser hiện tại của `haidang2425`. Muốn thêm các môn này cần
  ingest lại qua flow upload tài liệu chuẩn của `haidang2425`
  (`POST /admin/courses/{code}/documents`), không copy JSON thô.
- `src/services/email_service.py` — trùng lặp 100% với
  `src/services/core/email_service.py`.

## Cách tra cứu nhanh code gốc của `develop` sau này

Worktree tạm `../P-093-develop-worktree` (checkout `origin/develop`) vẫn còn
trên máy tại thời điểm viết file này — dùng để đọc nguyên bản trước khi port,
đừng chỉ dựa vào file backlog này.
