# Báo cáo đánh giá chất lượng AI — Cursus

> Tổng hợp có hệ thống từ toàn bộ bằng chứng thật đã có trong `eval/results/report.md`, `docs/evidence/` (test-runs/screenshots/security-findings), và `docs/PROJECT_CONTEXT.md` — đáp ứng mục 2.5 ý 4 của BTC (eval/benchmark cho phần AI, phân tích failure case, theo dõi lỗi/chi phí, nêu rõ giới hạn/rủi ro/hướng cải tiến). Đây là **tổng hợp**, không thay thế các file nguồn — mọi số liệu dưới đây trỏ ngược về file gốc để đối chiếu, không tự suy diễn thêm số liệu mới.
>
> **Cập nhật:** 22/08/2026. Toàn bộ số liệu trong báo cáo này là kết quả đo thật (test/log/ảnh chụp), không phải mô tả suông.

---

## 1. Phương pháp

Đánh giá chất lượng AI của Cursus chia làm 4 lớp độc lập, mỗi lớp đo 1 khía cạnh khác nhau:

| Lớp | Đo gì | Công cụ | Có gọi LLM thật không |
|---|---|---|---|
| **Guardrail offline** | Bộ rule chặn "làm hộ bài"/prompt injection có hoạt động đúng không | `eval/run_eval.py`, 30 case cố định (`guardrail_eval.jsonl`) | Không — rule-based, in-memory SQLite, không mạng |
| **RAG citation offline** | Câu hỏi có tìm đúng chunk nguồn không | `eval/run_eval.py`, 25 case cố định (`rag_eval.jsonl`) | Có thể có (embedding), nhưng phụ thuộc backend khả dụng lúc chạy — xem mục 3 |
| **Batch nhỏ Gemini thật** | Pipeline có thật sự gọi LLM thành công không, phân biệt được lỗi/quota khỏi chất lượng kém không | `eval/run_small_gemini_eval.py`, 11 lệnh gọi thật (5 QA + 3 Plan + 3 Reflection) | **Có** — Google Gemini thật, dùng trace `llm_success`/`fallback_used`/`retrieval_empty` (P0#8) để phân loại kết quả |
| **RBAC/IDOR sweep** | Có lỗ hổng phân quyền/truy cập chéo lớp/tổ chức không | Sweep tự động (5 agent song song) + audit thủ công, cộng `pytest tests/` toàn bộ (461 test) làm regression net | Không liên quan LLM — đây là an toàn hệ thống, không phải chất lượng câu trả lời AI, nhưng nằm chung yêu cầu PLO6/2.5 ý 4 nên gộp vào báo cáo này |

**Nguyên tắc reproducibility áp dụng cho lớp offline (guardrail/RAG):** mỗi lần chạy ghi lại `guardrail_ruleset_version`, fingerprint SHA1 của từng dataset JSONL, và 1 canary check `embedding_backend_reachable` (gọi thật, không chỉ kiểm tra có API key hay không) — để biết chắc số liệu đo dưới điều kiện nào, tránh so sánh nhầm 2 lần chạy khác điều kiện backend.

---

## 2. Kết quả

### 2.1 Guardrail (offline, 30 case)

**30/30 passed (100%)** — không có case fail. Ruleset version `guardrail_rules_v3`.

**Giới hạn cần nói rõ khi trích số liệu này:** đây là bộ case cố định, không phải adversarial/red-team mở rộng — chỉ chứng minh rule khớp đúng với chính bộ case đã viết, không chứng minh không thể bypass bằng cách diễn đạt khác (mục 4 bên dưới nói rõ hơn về gap này).

### 2.2 RAG citation (offline, 25 case)

**24/25 passed (96%)** — 1 case fail: `rag_019`, kỳ vọng chunk `SSA101-CLO4` nhưng hệ thống trả về 3 chunk session khác (không nằm trong top-k đúng như kỳ vọng).

**Điều kiện chạy quan trọng cần biết trước khi tin số này:** lần chạy gần nhất, canary `embedding_backend_reachable = False` — nghĩa là **toàn bộ 25 case này chạy trên lexical-only fallback**, không phải semantic embedding. Số liệu 24/25 không đo được chất lượng của signal embedding, chỉ đo được lexical scoring. Đây không phải lỗi — đúng theo cơ chế fail-closed đã thiết kế (không có embedding thì không regress, không crash) — nhưng cần nói đúng khi trình bày, tránh ngộ nhận "RAG đã test đủ cả 2 signal".

### 2.3 Batch nhỏ Gemini thật (11 lệnh gọi, không phải full benchmark)

**Tổng: 8/11 xác nhận `llm_success=True` thật, 2/11 LLM được gọi thật nhưng từ chối trả lời trung thực (`insufficient_context`, không phải lỗi), 1/11 đúng thiết kế route sang extractive (không cần gọi LLM).**

| Nhóm | Kết quả | Chi tiết |
|---|---|---|
| QA | 2/5 `llm_success=True` | 2 câu hỏi LLM tự nhận không đủ căn cứ trong nguồn (hành vi đúng, không bịa); 1 câu route sang extractive |
| Plan | 3/3 `llm_success=True` | Cả 3 assignment thật (CEA201) đều sinh task list qua LLM thành công, có `source_refs` đúng |
| Reflection | 3/3 `llm_success=True` | Cả 3 kịch bản đều có tóm tắt do LLM thật viết, không rơi về template tất định |

**Phát hiện quan trọng khi chạy batch này (không phải kết quả đo, mà là 1 bug thật):** lần chạy đầu tiên, cả 11/11 lệnh gọi generative thất bại — không phải quota, mà `model_name` mặc định (`gemini-2.5-flash`) đã bị Google khai tử (404). Phát hiện được **chính nhờ trace P0#8** — nếu không có trace, lỗi này sẽ trông giống 1 "fallback bình thường" và không ai biết model đã chết. Đã đổi sang `gemini-3.6-flash`, chạy lại cho ra số liệu ở trên. Đây là lần thứ 3 trong dự án 1 tên model Gemini hardcode bị khai tử âm thầm (embedding 20/08, generative 22/08, `model_fallbacks` phát hiện cùng lúc cũng chứa 2 tên đã chết) — xem mục 4.

**Quy mô đã duyệt, không mở rộng tự ý:** batch này CHỈ 11 lệnh gọi, đã được duyệt đúng quy mô này. Không suy rộng thành kết luận về chất lượng AI ở quy mô production — mục đích duy nhất là xác nhận pipeline gọi được LLM thật và trace phân loại đúng.

### 2.4 An ninh RBAC/IDOR

- **2 lỗ hổng IDOR thật tìm thấy và vá cùng ngày phát hiện:**
  - `GET /instructor/guardrail-reviews` không lọc theo lớp giảng viên (phát hiện 21/08, vá cùng ngày, test `test_ownership_module.py`).
  - `GET /admin/class-activities` thiếu đúng ownership check mà route ghi (`POST`) sibling đã có (phát hiện 22/08 qua sweep 39+24 route, vá cùng ngày, chi tiết đầy đủ: `docs/evidence/security-findings/2026-08-22_idor-admin-class-activities.md`).
- **1 lỗ hổng cross-tenant thật tìm thấy và vá cùng ngày:** `AuditLog` không có `organization_id` — bất kỳ Admin nào xem được audit log của mọi tổ chức khác. Vá đầy đủ (code + migration + SQL đã chạy trên Supabase thật) — verify 420/446 dòng có `organization_id`, 26 dòng NULL còn lại đúng thiết kế (login thất bại không xác định danh tính). Chi tiết: `docs/evidence/security-findings/2026-08-22_audit-log-not-org-scoped.md`.
- **Sweep có phạm vi ghi rõ, không tuyên bố "đã quét hết":** 39/39 route ở `instructor.py`/`student.py`/`companion.py`/`plans.py` xác nhận an toàn, cộng ~24 route khác trong `src/api/`. Không phải 100% route trong toàn bộ codebase.
- `pytest tests/` cuối cùng: **461 passed, 7 skipped, 0 failed** — bộ test này là lưới an toàn hồi quy cho toàn bộ hệ thống (không riêng AI), chạy lại sau mỗi thay đổi có ý nghĩa.

---

## 3. Failure case — phân tích cụ thể, không chỉ liệt kê số

### 3.1 `rag_019` — chunk kỳ vọng không nằm trong top-k

Câu hỏi kỳ vọng trả về `SSA101-CLO4` nhưng hệ thống trả 3 chunk `session-7/8/10`. Nguyên nhân khả dĩ (chưa điều tra sâu, ghi nhận là hướng cần làm — mục 5): lexical scoring (khi chạy fallback, không có embedding) có thể không đủ mạnh để phân biệt CLO cấp môn khỏi các session cụ thể khi câu hỏi dùng từ ngữ gần với nội dung session hơn là văn bản CLO gốc.

### 3.2 Retrieval không có ngưỡng liên quan ngữ nghĩa — phát hiện 20/08, chưa vá

`RetrievalService.retrieve()` không có ngưỡng điểm tối thiểu đủ chặt cho câu hỏi **ngoài phạm vi hoàn toàn** — verify bằng test trực tiếp: hỏi "Đồ án tốt nghiệp SSA101/CSI106 nộp khi nào?" (không có trong syllabus của cả 2 môn) vẫn trả về 3-5 chunk điểm thấp thay vì rỗng, khi không có LLM để tự nhận "không đủ căn cứ". Vi phạm nguyên tắc "không tìm thấy → nói không tìm thấy, không trình bày như liên quan". Đây là gap thật, không phải lý thuyết — cần thêm ngưỡng + case out-of-scope vào bộ eval khi mở rộng quy mô.

### 3.3 Model Gemini bị khai tử âm thầm — 3 lần trong lịch sử dự án

1. `GEMINI_EMBED_MODEL` (`text-embedding-004`) — phát hiện + vá 20/08.
2. `model_name` mặc định (`gemini-2.5-flash`) — phát hiện + vá 22/08 (đúng lúc chạy batch eval này, xem mục 2.3).
3. `model_fallbacks` (`src/config.py`) — phát hiện 22/08, cả 2 tên model liệt kê trong đó **cũng đã không còn hợp lệ**, nhưng bản thân field này là dead config (`get_llm()` không đọc), nên chưa từng thực sự gây lỗi runtime — chỉ là 1 phát hiện phụ khi rà soát.

**Điểm chung của cả 3 lần:** mọi service đều có `try/except` tự fallback về extractive/template — nên model chết **không crash app**, chỉ âm thầm ngừng dùng LLM. Chỉ phát hiện được nhờ có trace (P0#8) hoặc gọi `client.models.list()` chủ động kiểm tra. Đây là lớp bug "trông như bình thường, thực ra đang âm thầm hỏng" đã lặp lại nhiều lần nhất trong dự án (cùng họ với bug identity giảng viên demo qua restart, mục 20 `ARCHITECTURE.md`).

---

## 4. Giới hạn — nói thẳng, không tuyên bố quá mức

- **Batch Gemini thật (11 case) không phải benchmark** — quy mô đủ để xác nhận pipeline hoạt động, không đủ để kết luận chất lượng câu trả lời AI ở quy mô production. Mở rộng quy mô là việc P1 chưa làm (mục 16.5 `PROJECT_CONTEXT.md` đã tách theo tầng dev-smoke/pre-demo/pilot, chưa chạy tầng lớn hơn).
- **RAG offline 24/25 chạy trên lexical-only fallback**, không phải embedding thật — không thể dùng số này để tuyên bố "semantic RAG đã được kiểm chứng".
- **Guardrail 30/30 là bộ case cố định**, không phải red-team/adversarial mở rộng — chưa đo được khả năng bypass bằng cách diễn đạt khác ngoài bộ case đã viết. `docs/PROJECT_CONTEXT.md` mục 9 ý4 đã ghi nhận: "vẫn là regex, chưa chắc bắt được biến thể diễn đạt khác".
- **Kiến trúc RAG thật KHÔNG dùng pgvector/reranker** như tài liệu cũ (README/ARCHITECTURE.md/ADR-004 bản gốc) từng mô tả — là lexical + cosine similarity thuần Python. Đã sửa lại tài liệu cho đúng (xem `ARCHITECTURE.md`, cập nhật 22/08) — nhưng cần biết khi trình bày PLO3, tránh trích dẫn nhầm cơ chế không tồn tại.
- **RLS đa tổ chức chưa bật thật ở tầng DB** — cách ly tổ chức hiện dựa hoàn toàn vào filter tầng ứng dụng, chưa có lớp phòng thủ thứ 2 ở DB. Đây là gap an ninh lớn nhất còn tồn tại tính đến 22/08 (xem `docs/PROJECT_CONTEXT.md` mục 9 ý1, cần xử lý trên Supabase Dashboard).
- **Sweep RBAC/IDOR có phạm vi, không phải toàn bộ codebase** — 39+24 route đã quét, không phải 100%.
- **Load test 2.500 kết nối đồng thời chưa chạy** — không có số liệu về hành vi dưới tải để đưa vào báo cáo này.

---

## 5. Hướng cải tiến

1. **Mở rộng batch Gemini thật lên quy mô benchmark thật sự** (theo 3 tầng đã định nghĩa ở mục 16.5 `PROJECT_CONTEXT.md`: dev smoke → pre-demo regression → pilot), có ngân sách API rõ ràng theo từng tầng.
2. **Thêm ngưỡng liên quan ngữ nghĩa + case out-of-scope vào bộ eval RAG** — vá gap mục 3.2 (câu hỏi ngoài phạm vi vẫn trả về chunk điểm thấp thay vì rỗng).
3. **Mở rộng bộ case guardrail sang adversarial/red-team** — không chỉ case cố định đã viết, để đo được khả năng bypass bằng diễn đạt khác.
4. **Rà toàn bộ tên model Gemini hardcode trước deploy thật** — đã ghi nhận ở `docs/PENDING_DECISIONS.md` #3, chưa làm (không urgent cho 23/08 vì 2 model đang dùng đã xác nhận hoạt động). Cân nhắc thêm 1 canary check tự động (gọi `client.models.list()` định kỳ hoặc lúc khởi động) thay vì chỉ phát hiện thủ công khi có sự cố — đúng bài học rút ra từ 3 lần model chết âm thầm.
5. **Hoàn thiện RLS đa tổ chức ở tầng DB thật** — việc chặn deadline lớn nhất còn lại, cần người có quyền Supabase Dashboard xử lý trước (mục 9 ý1).
6. **Chạy load test 2.500 kết nối đồng thời** — theo đúng workload model đã định nghĩa (mục 9 ý9), bổ sung số liệu p95/error rate còn thiếu vào báo cáo này ở lần cập nhật sau.
7. **Cập nhật lại ADR-004** cho khớp kiến trúc RAG thật (lexical+embedding, không pgvector/reranker) — hiện chỉ mới sửa ARCHITECTURE.md/README, ADR-004 gốc vẫn giữ nguyên mô tả cũ theo đúng quy tắc "chỉ thêm ADR mới, không sửa ADR cũ" (xem ADR-016 đến ADR-019 mới thêm 22/08 cho các quyết định khác — cân nhắc thêm 1 ADR mới ghi nhận riêng việc "RAG thật khác định hướng ADR-004 ban đầu" thay vì chỉ sửa trong ARCHITECTURE.md).

---

## Nguồn dữ liệu đầy đủ (để đối chiếu, không chép lại nguyên văn ở đây)

- `eval/results/report.md` — báo cáo gốc, số liệu chi tiết từng case.
- `docs/evidence/test-runs/*.xml` — toàn bộ kết quả `pytest` dạng JUnit XML theo từng lần sửa.
- `docs/evidence/screenshots/*/` — ảnh chụp UI thật (không phải mockup) cho từng tính năng có giao diện.
- `docs/evidence/security-findings/*.md` — 2 lỗ hổng IDOR + 1 audit log org-scoping, đầy đủ root cause/repro/fix.
- `docs/PENDING_DECISIONS.md` — quyết định kiến trúc còn treo liên quan tới eval (trace wiring Option B, model_fallbacks dead config).
- `docs/PROJECT_CONTEXT.md` mục 9, 9.5, 16.5 — bối cảnh đầy đủ, tiêu chí P0/P1, cách phân tầng quy mô eval.
