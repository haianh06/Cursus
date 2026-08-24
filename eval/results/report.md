# Cursus Gate-2 evaluation report

Generated: 2026-08-22T15:22:28.719923+00:00

Guardrail suite runs with no network (DB-backed rule toggles, in-memory SQLite only). RAG suite attempts real semantic embedding when a `GOOGLE_API_KEY` is configured and falls back to lexical-only scoring on any failure — see Reproducibility below for which path this run actually took.

## Reproducibility

- Guardrail ruleset version: `guardrail_rules_v3`
- `guardrail_eval.jsonl` fingerprint: `b74866c409df`
- `rag_eval.jsonl` fingerprint: `d611bfd4c74b`
- Semantic embedding backend reachable this run: **False** — RAG suite above ran on lexical-only fallback, not semantic embedding

### Guardrail

**30/30 passed (100%)**

No failures.

### RAG / retrieval citation

**24/25 passed (96%)**

| case | expected | actual | note |
|---|---|---|---|
| rag_019 | SSA101-CLO4 | SSA101-session-7,SSA101-session-8,SSA101-session-10 | expected chunk not in top-k |

---

# P0#5 — Small real-Gemini validation batch [ADDED 22/08, đêm muộn]

Generated: 2026-08-22T15:21:45.617631+00:00 (`eval/run_small_gemini_eval.py`)

**⚠️ Scope note, đọc trước khi trích số liệu bất kỳ chỗ nào: đây là bộ eval NHỎ (≤11 lần gọi Gemini thật: 5 QA + 3 Plan + 3 Reflection), ĐÃ được duyệt ngân sách với đúng quy mô này — KHÔNG PHẢI full benchmark.** Quy mô full benchmark nằm ngoài phạm vi 23/08 có chủ đích (mục 16.5). Mục đích duy nhất của bộ này: xác nhận pipeline thật sự gọi được Gemini thật và phân biệt đúng "gọi thành công" với "fallback do lỗi/quota" qua trace field vừa nối ở P0#8 — không phải đo chất lượng ở quy mô lớn.

**Phát hiện quan trọng khi chạy (không phải kết quả eval, mà là 1 bug thật chặn cả batch lúc đầu):** lần chạy đầu tiên, cả 11/11 lệnh gọi generative đều thất bại — không phải do quota, mà do `model_name` mặc định (`gemini-2.5-flash`, `src/config.py`) đã bị Google khai tử ("no longer available to new users", lỗi 404 rõ ràng, không phải 429). Đã xác nhận qua `client.models.list()` với đúng API key đang cấu hình và đổi sang `gemini-3.6-flash` (model Google trực tiếp khuyến nghị trong thông báo lỗi, xác nhận có hỗ trợ `generateContent`). Cùng họ lỗi với bug `GEMINI_EMBED_MODEL` đã vá 20/08 — model bị khai tử âm thầm, không crash app (mọi service đều tự fallback), chỉ phát hiện được nhờ P0#8's trace field, đúng như mục đích P0#5 này được lập ra để làm. **Phát hiện phụ, CHƯA vá (ghi nhận, không mở rộng phạm vi thêm):** `model_fallbacks` (`src/config.py`) là 1 field cấu hình chết — `get_llm()` không hề đọc field này, không có logic fallback-retry nào thật sự tồn tại; 2 model liệt kê trong đó cũng không còn hợp lệ với API key hiện tại.

Sau khi vá model, chạy lại đúng 11 lệnh (không retry thêm, không tính lần chạy lỗi đầu vào kết quả vì đó là lỗi cấu hình, không phải hành vi AI thật cần đo):

## QA — 2/5 llm_success=True

| question | mode | trace |
|---|---|---|
| So sánh CLO4 và CLO9 của SSA101 khác nhau thế nào? | llm | `llm_attempted=True llm_success=True fallback_used=False retrieval_empty=False` |
| Phân tích mối liên hệ giữa Time Management (session 7-12) và Critical Thinking (session 43-45) | no_source | `llm_attempted=True llm_success=False fallback_used=True retrieval_empty=False` — LLM được gọi thật, tự nhận `insufficient_context` (không bịa), không phải lỗi |
| Tại sao Information Literacy (session 22-23) lại quan trọng trước AI Hallucination (session 27) | no_source | `llm_attempted=True llm_success=False fallback_used=True retrieval_empty=False` — tương tự, LLM từ chối trả lời vì không đủ căn cứ trong nguồn |
| So sánh Project Part 1 (session 13) và Group Project Part 3 (session 55-59) | llm | `llm_attempted=True llm_success=True fallback_used=False retrieval_empty=False` |
| Giải thích vì sao Individual Progress Test (session 52-54) được xếp sau Metacognition (session 49) | extractive | `llm_attempted=False` — câu hỏi không khớp pattern "cần LLM" của `_needs_llm()`, tự động dùng đường rẻ hơn (extractive), đúng thiết kế, không phải lỗi |

## Plan — 3/3 llm_success=True

Cả 3 assignment thật (CEA201, nội dung Chapter 3/8/11) đều tạo task list qua LLM thật thành công, có `source_refs` trích đúng chunk đã retrieve, không assignment nào phải rơi về template tĩnh.

## Reflection — 3/3 llm_success=True

Cả 3 kịch bản (tuần hoàn thành tốt/tuần bị gián đoạn/tuần hoàn thành 100%) đều có bản tóm tắt do LLM thật viết, không kịch bản nào rơi về `build_summary` tất định.

**Tổng: 8/11 xác nhận `llm_success=True` thật qua trace, 2/11 LLM được gọi thật nhưng từ chối trả lời trung thực (không phải lỗi), 1/11 đúng thiết kế không cần gọi LLM.** Không có lỗi quota nào ở tầng generative (chat) — quota `embed_content_free_tier_requests` (tầng embedding, dùng cho retrieval) bị cạn trong lúc chạy, khiến retrieval rơi về lexical-only đúng cơ chế fail-closed đã có sẵn — không ảnh hưởng tới các lệnh gọi generative đang được đo ở đây, chỉ ảnh hưởng chất lượng retrieval (không phải trọng tâm batch này).
