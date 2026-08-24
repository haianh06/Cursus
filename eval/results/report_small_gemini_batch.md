# P0#5 — Small real-Gemini validation batch

Generated: 2026-08-22T15:21:45.617631+00:00

**Scope note: this is a SMALL, budget-approved validation batch (<=11 real Gemini calls: 5 QA + 3 Plan + 3 Reflection), NOT a full benchmark.** Full benchmark scale is explicitly out of scope for 23/08 (mục 16.5). This batch exists to confirm the pipeline actually works against the real Gemini API, using the P0#8 trace fields to tell a genuine LLM success apart from a quota/error fallback -- not to measure quality at scale.

## QA

2/5 calls confirmed llm_success=True via qa_answer_trace log.

| question | mode | trace |
|---|---|---|
| So sánh CLO4 và CLO9 của SSA101 khác nhau thế nào? | llm | `qa_answer_trace subject_code=SSA101 mode=llm llm_attempted=True llm_success=True fallback_used=False retrieval_empty=False` |
| Phân tích mối liên hệ giữa Time Management (session 7-12) và | no_source | `qa_answer_trace subject_code=SSA101 mode=no_source llm_attempted=True llm_success=False fallback_used=True retrieval_empty=False` |
| Tại sao Information Literacy (session 22-23) lại quan trọng  | no_source | `qa_answer_trace subject_code=SSA101 mode=no_source llm_attempted=True llm_success=False fallback_used=True retrieval_empty=False` |
| So sánh Project Part 1 (session 13) và Group Project Part 3  | llm | `qa_answer_trace subject_code=SSA101 mode=llm llm_attempted=True llm_success=True fallback_used=False retrieval_empty=False` |
| Giải thích vì sao Individual Progress Test (session 52-54) đ | extractive | `qa_answer_trace subject_code=SSA101 mode=extractive llm_attempted=False llm_success=False fallback_used=False retrieval_empty=False` |

## Plan

3/3 scenarios confirmed llm_success=True.

| assignment | llm_attempted | llm_success | fallback_used | retrieval_empty | task_count |
|---|---|---|---|---|---|
| Bài tập Chapter 3: Cache Memory | True | True | False | False | 6 |
| Bài tập Chapter 8: Instruction Sets | True | True | False | False | 5 |
| Bài tập Chapter 11: Parallel Processing | True | True | False | False | 5 |

## Reflection

3/3 scenarios confirmed llm_success=True.

| week | trace |
|---|---|
| 4 | {'llm_attempted': True, 'llm_success': True, 'retrieval_empty': False} |
| 5 | {'llm_attempted': True, 'llm_success': True, 'retrieval_empty': False} |
| 6 | {'llm_attempted': True, 'llm_success': True, 'retrieval_empty': False} |
