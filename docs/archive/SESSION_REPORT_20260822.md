> **LƯU Ý:** Nhánh cleanup/repo-audit-20260820 đề cập trong tài liệu này đã hoàn thành nhiệm vụ, được merge toàn bộ vào nhánh haidang2425 và đã bị xóa.

# Báo cáo phiên làm việc — 22/08/2026 ("Build toàn bộ phần còn lại")

## 🚪 BÀN GIAO CHO PHIÊN MỚI [MỚI NHẤT, ~23:30 — đọc đoạn này trước bất kỳ đoạn nào khác trong file, kể cả đoạn "Trạng thái khi kết thúc phiên" ngay bên dưới (đoạn đó viết sớm hơn trong đêm, trước khi P0#8/LLM08/P0#5 xong)]

Viết để đóng phiên sạch — context sắp hết, không auto-compact. Đọc xong đoạn này là đủ để tiếp tục ngay, không cần đọc lại toàn bộ lịch sử phía dưới trừ khi cần chi tiết 1 việc cụ thể.

**Tóm tắt 1 câu: toàn bộ P0 trong khả năng tự làm của phiên này đã xong. Chỉ còn đúng 2 việc chặn deadline, cả 2 đều cần bạn tự vào Supabase Dashboard — không còn việc code nào khác đang treo.**

**Bao nhiêu P0 đã xong:** 7/8 mục P0 gốc (#1, #2, #4, #5, #6, #7, #8) đã ✅ hoàn toàn, có bằng chứng (test/ảnh/log) cho từng mục — xem bảng đầy đủ ở `docs/PROJECT_CONTEXT.md`, section "TRẠNG THÁI HIỆN TẠI" ngay đầu file (đã ghi đè, không cộng dồn, phản ánh đúng lúc kết thúc phiên). `pytest tests/`: **461 passed, 7 skipped, 0 failed**.

**Còn đúng 2 việc, cả 2 cần Supabase Dashboard (không phải AI tự làm được):**
1. **RLS đa tổ chức (P0#3)** — vẫn 0%. SQL/migration/`tenant_scope.py` đã chuẩn bị sẵn, chờ bạn tự chạy SQL trước.
2. **`alembic_version` trên Supabase lệch chain** — không chặn app chạy, nhưng chặn migration mới sau này. Cần người có quyền Dashboard tự đối chiếu.

**Không còn việc code nào khác đang treo trừ khi phát sinh mới.** 1 ghi chú phụ không urgent: `PENDING_DECISIONS.md` #3 mới (đêm nay) — `model_fallbacks` là config chết + đề xuất rà toàn bộ tên model Gemini hardcode trước khi deploy thật (đã gặp 3 lần model bị khai tử âm thầm) — không cần làm trước 23/08.

**3 việc lớn nhất làm xong sau báo cáo "Trạng thái khi kết thúc phiên" cũ hơn ngay bên dưới** (đoạn đó đã lỗi thời ở phần P0#5/P0#8/LLM08 — đọc đoạn BÀN GIAO này thay vì đoạn đó cho các mục này):
- **P0#8** (trace `llm_success`/`fallback_used`/`retrieval_empty`) — Option B do bạn chọn, JSON column cho Plan/Reflection, structured log cho QA. `PENDING_DECISIONS.md` #1 ✅ RESOLVED.
- **LLM08** (validate nội dung tài liệu trước khi embed) — rule-based, flag không reject, 0 false positive/44 môn thật sau khi loại pattern "api key" gây nhầm.
- **P0#5** (eval Gemini thật, bộ nhỏ 11 case đã duyệt) — 8/11 `llm_success=True` xác nhận thật. Phát hiện + vá luôn 1 bug thật chặn cả batch (model bị khai tử, không phải quota) và 1 test trước đó chỉ pass nhờ bug đó (`test_gate2_flow.py`, đã sửa đúng ý định thật).

**Commit đêm nay đã push đủ, `cleanup/repo-audit-20260820`, mới nhất `9c49c6b`.** Không đụng `main`.

---

## 🌙 Trạng thái khi kết thúc phiên đêm 22/08 [Cũ hơn — giữ làm lịch sử, đọc đoạn BÀN GIAO ở trên trước]

Viết cho 1 người/AI hoàn toàn mới mở phiên chat mới, không cần hỏi lại gì thêm. Branch: `cleanup/repo-audit-20260820`, đã push đầy đủ lên `origin` (không đụng `main`). Deadline: 23/08/2026.

**Đã xong, có bằng chứng đầy đủ (đêm nay, phần cuối cùng):**
- 5 việc "chủ động chưa làm" đã hoãn từ đầu đêm, sau đó bạn quyết định đảo lại và làm hết: Admin Config tab, mục 14.1 insufficient-data, Lecturer class picker, Audit log org-scoping (đủ cả code + migration + SQL đã tự chạy), Cursus Assistant widget nổi trả lời thật trên `/student/*`.
- Port frontend pin cứng 5173 (`strictPort: true`) — hết drift sang 5174 gây vỡ CORS.
- Mock LMS: vá lỗ hổng bảo mật thật (2 trang sửa deadline trước đó không có xác thực nào) bằng HTTP Basic Auth — verify: không đăng nhập → 401, đúng `admin`/`mocklms-admin` → 200, sửa deadline qua UI hoạt động đúng, API OAuth (Cursus thật sự gọi) không bị ảnh hưởng.
- Admin Console: màn chi tiết Curriculum (CLO + Session) mới, đọc thật từ 44 file syllabus đã parse — đã điều tra trước khi code, xác nhận KHÔNG có field "LO" theo session hay bảng trọng số điểm tách dòng trong dữ liệu thật, nên UI không bịa 2 thứ đó. Verify 2 môn khác nhau (SSA101, CEA201).
- **Phát hiện + vá 1 bug nghiêm trọng ngoài dự kiến:** verify sống phát hiện thiếu cột `organization_id` không chỉ làm sai Audit log — nó khiến MỌI lần đăng nhập trên Supabase dev crash 500 (vì `AuditService.log_event(commit=True)` chạy ngay sau khi tạo session, insert lỗi kéo sập cả request). Đã vá để audit-log write failure không bao giờ được phép sập flow chính nữa (`AuditRepository.add()`), độc lập với việc chạy SQL.
- Bạn đã tự chạy `scripts/sql/add_audit_log_org_scoping_22aug.sql` trên Supabase Dashboard. Kết quả xác nhận: 420/446 dòng có `organization_id`, 26 dòng NULL còn lại đều là `LOGIN_FAILED` không xác định được actor (đúng thiết kế, không phải lỗi), 0 Admin thiếu tổ chức.
- Verify sống toàn diện sau khi chạy SQL: đăng nhập cả 3 role thật (Student/Lecturer/Admin, tài khoản demo `*.demo@example.test` / `password123`) — 0 lỗi 500 ở bất kỳ đâu; tab Audit log Admin Console hiện đúng dữ liệu thật (100 dòng, dòng đầu khớp đúng lần đăng nhập vừa test); `pytest tests/`: **445 passed, 7 skipped, 0 failed**, chạy lại 2 lần để chắc chắn, không đổi trước/sau SQL (đúng kỳ vọng — bộ test dùng SQLite riêng). Ảnh + log đầy đủ: `docs/evidence/screenshots/2026-08-22_late-night-verification/`, `docs/evidence/test-runs/20260822-2200-late-night-final-verification.xml`.
- Toàn bộ 12 commit đêm nay (từ lúc "đảo lại làm 5 việc" tới verify cuối) đã push lên `origin/cleanup/repo-audit-20260820`.

**Còn treo, cần bạn quyết định/hành động — KHÔNG phải AI tự làm được:**
1. **RLS đa tổ chức (P0#3) — vẫn 0%.** Đã chuẩn bị sẵn SQL + migration + `tenant_scope.py`, nhưng cần bạn tự chạy trên Supabase Dashboard + gắn vào route + test bằng Postgres thật. Rủi ro bảo mật thật lớn nhất còn lại.
2. **P0#8 trace wiring — chưa code**, chờ bạn chọn 1 trong 3 hướng ở `PENDING_DECISIONS.md` #1 (đều là quyết định schema).
3. **`alembic_version` trên Supabase vẫn lệch chain** — cả 2 script SQL đã chạy đêm nay (audit-log + fix_missing_tables) đều né bảng này có chủ đích. Không chặn app chạy runtime, nhưng sẽ chặn `alembic upgrade head` sau này.
4. **P0#5 (eval Gemini thật)** vẫn chờ duyệt ngân sách API.
5. **LLM08** (validate nội dung trước khi embed) chưa làm.

**Ưu tiên tiếp theo khi mở phiên mới (đề xuất, không phải quyết định thay bạn):** RLS nếu còn thời gian và bạn muốn ưu tiên bảo mật thật (cần bạn tự chạy SQL trước khi AI làm phần code); nếu không, polish UI/UX thêm hoặc chuẩn bị demo script là lựa chọn an toàn hơn với quỹ thời gian còn lại trước 23/08.

**Sẵn sàng bàn giao:** `docs/PROJECT_CONTEXT.md` (mục "TRẠNG THÁI HIỆN TẠI" ở đầu file), `docs/PENDING_DECISIONS.md`, và đoạn này đều đã cập nhật đồng bộ — đủ để mở phiên chat mới ngay lập tức mà không mất context, không cần hỏi lại.

---

## ✅ [MỚI NHẤT, tối 22/08] Audit UI/UX toàn diện — 4 giai đoạn, 10 checkpoint, đã xong + đã commit

Mandate riêng, tách khỏi phần "ĐỌC TRƯỚC TIÊN" bên dưới (phần đó là 2 việc khẩn đã xử lý xong từ trước, giữ nguyên làm hồ sơ lịch sử). Quy trình: **Audit** toàn bộ màn hình/vai trò theo đúng mục 6/13-14/16 PROJECT_CONTEXT.md → **Research** tham khảo sản phẩm thật → **Evaluation** xếp ưu tiên, 4 câu hỏi cần quyết định → **cổng chặn 1, chờ duyệt** → **Plan** 10 checkpoint chi tiết → **cổng chặn 2, chờ duyệt** → **Execute** từng checkpoint (1 commit + evidence riêng/checkpoint). Toàn bộ đã được duyệt và thực thi xong trong đêm nay.

**4 file chi tiết đầy đủ (đọc ở đây nếu cần bằng chứng/lý do cho từng quyết định):** `docs/archive/23aug-audit-trail/AUDIT_0_HIENTRANG.md`, `docs/archive/23aug-audit-trail/RESEARCH_1_THAMKHAO.md`, `docs/archive/23aug-audit-trail/EVALUATION_2_KETLUAN.md`, `docs/archive/23aug-audit-trail/PLAN_3_THUCTHI.md`.

**2 phát hiện nghiêm trọng nhất của Audit** (trước đó không ai biết, không có trong bất kỳ báo cáo nào khác của dự án):
1. Biểu đồ "tiến độ lớp theo tuần" ở Bảng điều khiển Giảng viên là **4 số hardcode trong code**, khiến cảnh báo "xu hướng giảm" hiện **vĩnh viễn cho mọi giảng viên** bất kể thực tế — đã vá (Checkpoint 10).
2. "Cursus Assistant" hoá ra là **3 hệ thống rời rạc** — bản "nổi mọi trang" chỉ là kịch bản FAQ cứng, không gọi AI thật, và biến mất hoàn toàn sau khi đăng nhập — **chưa vá** (quyết định C1: sửa tài liệu cho khớp thực tế, để việc hợp nhất kiến trúc lại cho sau 23/08, vì rủi ro cao hơn giá trị đêm nay).

**10 checkpoint đã thực thi (mỗi cái 1 commit riêng, xem `git log`, prefix "Checkpoint N:"):**

| # | Việc | Trạng thái |
|---|---|---|
| 1 | `constants/roles.js` thêm bản tiếng Anh (sửa 4 màn hình kẹt tiếng Việt) | ✅ Verified — puppeteer live |
| 2 | `AuthLayout.jsx` sửa h1 thiếu/trùng ở 5+ màn auth | ✅ Verified — đếm h1 thật ở 375px+1440px |
| 3 | Nút Google login — disable trung thực thay vì luôn báo lỗi | ✅ Verified — cả 2 theme |
| 4 | Tooltip định nghĩa "nguy cơ" (mục 14.1) | ✅ Verified phần Overview; RiskCaseDrawer coded cùng pattern, chưa click-verify (lớp demo hiện không có case để mở) |
| 5 | Badge risk contrast WCAG AA (light theme) | ✅ Verified — đo lại đúng công thức, 5.1-5.5:1 |
| 6 | Modal xác nhận thời gian thực khi Hoàn thành task (mục 13.2) | ✅ Verified — hoàn thành 2 task thật, backend lưu đúng giá trị nhập |
| 7 | Nav link cho 2 trang mồ côi (semester-setup, lecture-plan) | ✅ Verified — cả 2 ngôn ngữ |
| 8 | Dedupe magic string `lecture_plan` + thông báo khi bị đè | ✅ Verified qua pytest (2 test mới); phát hiện phụ: route mang thông báo hiện chưa được frontend gọi — ghi rõ trong `docs/archive/23aug-audit-trail/AUDIT_0_HIENTRANG.md` mục 7.6b |
| 9 | Bảng danh sách sinh viên Lecturer (mục 6.4) | ✅ Verified — dữ liệu thật 5 sinh viên, tìm kiếm hoạt động đúng |
| 10 | Biểu đồ Lecturer: bỏ số liệu bịa, hiện số thật trung thực | ✅ Verified — cảnh báo giả xác nhận đã biến mất khỏi DOM |

**`pytest tests/` cuối cùng sau cả 10 checkpoint: 408 passed, 7 skipped, 0 failed.** `npm run build`/`npm run lint` sạch (chỉ còn cảnh báo có từ trước, không liên quan). Toàn bộ ảnh chụp bằng chứng ở `docs/evidence/screenshots/2026-08-22_cp{1-10}-*/`.

**Chưa làm, có chủ đích (đã ghi trong `EVALUATION_2_KETLUAN.md`, không phải bỏ sót):** hợp nhất kiến trúc Cursus Assistant (C1), vá org-scoping Audit log (C3, đã escalate từ trước ở `PENDING_DECISIONS.md` #2), tab Admin "Cấu hình" (C4), bộ chọn lớp Lecturer, trạng thái "chưa đủ dữ liệu" (mục 14.1), xây lịch sử hoàn thành thật theo từng tuần cho biểu đồ Lecturer.

---

## ⏰ ĐỌC TRƯỚC TIÊN — 2 việc khẩn, điều tra xong trong đêm, chờ bạn quyết định

### 1. ✅ Instructor Dashboard 500 — ĐÃ VÁ THẬT, đã verify lại bằng browser thật (22/08)

**Xác nhận nguyên nhân bằng traceback đầy đủ (không chỉ đoán):**
```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedColumn)
column risk_signals.policy_version does not exist
```
Đây **đúng là gap đã biết từ 21/08** (mục 9 ý8 — migration chain của Supabase dev bị lệch nhánh), **không phải lỗi mới phát sinh đêm nay**.

**Nhưng phạm vi THỰC TẾ rộng hơn ban đầu tưởng.** So sánh trực tiếp toàn bộ danh sách bảng giữa code hiện tại và Supabase dev thật (`information_schema.tables`), không chỉ 1 cột bị thiếu — **cả 2 bảng chưa từng được tạo trên Supabase**:
- `risk_policies` — toàn bộ tính năng "Chính sách AI → Risk Policy" (đã tự đánh giá ✅ Verified 21/08, nhưng verify đó chạy trên SQLite/test DB, **chưa từng verify trên chính Supabase dev này**) sẽ **cũng lỗi 500** y hệt nếu ai đó mở tab đó lên Supabase dev thật.
- `mock_lms_sync_versions` — đã biết từ trước (ghi trong mục 9 ý8), verify Mock LMS Checkpoint 4 đã né bằng cách chạy tạm trên SQLite riêng port 8010 — không phải phát hiện mới, nhưng liên quan tới cùng gap này.
- Cột `risk_signals.policy_version` — đúng cột gây lỗi 500 nhìn thấy được.
- Bảng `admin_settings` — chưa có màn UI nào dùng tới nên chưa ai thấy lỗi, nhưng cũng thiếu.

**Đã chuẩn bị sẵn, CHƯA chạy (đúng rào chắn):** `scripts/sql/fix_missing_tables_22aug.sql` — 1 file SQL thuần, an toàn chạy lại nhiều lần (mọi bước đều tự kiểm tra "đã có chưa" trước khi tạo), tạo đúng 2 bảng + 1 cột thiếu ở trên, seed đúng 1 dòng policy mặc định (y hệt giá trị hardcode cũ trong `risk_engine.py`, để hành vi tính điểm rủi ro không đổi ngay sau khi chạy). File có ghi sẵn hướng dẫn từng bước bằng tiếng Việt ngay trong đó (mở Supabase Dashboard → SQL Editor → dán → Run → cách xác nhận đã thành công), không cần biết SQL để làm theo. Script **không** đụng tới bảng `alembic_version` — gap đó (alembic đang trỏ nhầm nhánh) là vấn đề khác, lớn hơn, chưa xử lý ở đây.

**Việc bạn cần làm (không phải AI làm được):** mở Supabase Dashboard, chạy file SQL trên, xác nhận Instructor Dashboard load lại đúng.

**[Cập nhật — bạn đã tự chạy script, đã verify lại đủ]** Xác nhận cả 3 bảng + cột đã tồn tại thật trên Supabase (`information_schema` query trực tiếp), policy version 1 đã seed đúng. Khởi động sạch backend+frontend (kill process cũ theo đúng thói quen), verify bằng cả `curl` lẫn browser thật (Edge qua puppeteer-core):
- `curl` trực tiếp `/instructor/dashboard` + `/instructor/alerts`: `200` (trước đó `500`).
- Instructor Dashboard (tài khoản `instructor.demo` thật): load đúng, không lỗi, biểu đồ tiến độ tuần hiện đúng. Ảnh: `docs/evidence/screenshots/2026-08-22_supabase-schema-fix-verified/1-instructor-dashboard.png`.
- Tab "AI Policy" (Risk Policy): hiện đúng "Current version: 1", đủ 5 tín hiệu weight/threshold khớp giá trị vừa seed. Ảnh: `.../2-risk-policy-admin.png`.
- Tab "Mock LMS": hiện đúng "Last synced: never synced yet" — bảng rỗng nhưng KHÔNG lỗi, **lần đầu tiên chạy được trên chính Supabase thật** (trước đó phải né bằng SQLite tạm port 8010). Ảnh: `.../3-mock-lms-admin.png`.

**[✅ Đã điều tra + vá xong — quan sát phụ ở trên hoá ra là 1 bug thật, cùng họ "silent fallback" đã ám ảnh dự án (PROMPT_PATH, embedding model, score threshold), lần này ở tầng identity giảng viên demo, không phải thiếu dữ liệu.]**

**Nguyên nhân:** `gate2_demo.py::_ensure_instructor()` fallback sang "bất kỳ INSTRUCTOR/ADMIN nào, `.first()`" khi không thấy đúng email `DEMO_INSTRUCTOR_EMAIL`, và nhánh tạo-mới tạo nhầm email khác — nên không bao giờ tự sửa lại đúng. `_ensure_class_section()` ghi đè `instructor_id` của lớp SSA101 vô điều kiện mỗi khi `_CLASS_CACHE` rỗng (mỗi lần restart backend). Kết quả: tài khoản `instructor.demo@example.test` (dùng test xuyên đêm nay, KHÔNG phải giảng viên demo chuẩn) từng "chiếm" lớp qua 1 lần restart, mất lại ở lần sau — API vẫn `200`, chỉ số liệu về 0, không có gì báo lỗi.

**Quyết định của bạn:** `demo.instructor@cursusdemo.local` ("Cô Hương") là tài khoản giảng viên demo chuẩn duy nhất — đúng persona đã ghi sẵn ở mục 18 PROJECT_CONTEXT.md, không cần sửa tài liệu đó (đã đúng từ trước, lỗi nằm ở việc test nhầm tài khoản, không phải lỗi tài liệu).

**Đã vá:** `_ensure_instructor()` bỏ hẳn fallback, tự tạo đúng tài khoản chuẩn nếu thiếu; `_ensure_class_section()` không ghi đè `instructor_id` khi section đã tồn tại (phòng thủ kép). 2 test mới (1 SQLite cô lập tái hiện đúng điều kiện lỗi cũ, 1 Supabase thật mô phỏng 3 lần restart). Verify tay thật: mint token trực tiếp cho "Cô Hương" (không cần/không đụng mật khẩu thật), kill+restart backend 3 lần liên tiếp, `classSize` luôn đúng `5`. `pytest` toàn bộ: 424 passed, 0 failed, chạy 2 lần liên tiếp để loại flaky.

Chi tiết đầy đủ: PROJECT_CONTEXT.md mục 9 ý8 (đoạn cuối). **Giới hạn thành thật:** chưa có ảnh chụp UI trình duyệt cho đúng tài khoản "Cô Hương" (không có mật khẩu thật, không tự ý reset) — verify bằng API/token trực tiếp thay vào đó.

**Còn nguyên, CHƯA vá (không phải lỗi chặn app chạy):** `alembic_version` trên Supabase vẫn trỏ sai nhánh (`20260821_self_study_sessions`, không tồn tại trong chain nhánh này) — script vừa chạy là SQL trực tiếp, không đụng bảng này, nên `alembic current`/`alembic upgrade head` từ terminal vẫn sẽ báo lỗi y hệt trước. Không ảnh hưởng app chạy thật (app không dùng Alembic lúc runtime), nhưng cần biết trước khi ai đó chạy migration mới trong tương lai — vẫn cần người có quyền Supabase Dashboard tự tay đối chiếu.

Đã cập nhật PROJECT_CONTEXT.md mục 9 ý8 với đầy đủ bằng chứng trên.

---

### 2. 15 file uncommitted "real curriculum retrieval" — XÁC NHẬN LÀ GÌ, chưa commit

**Kết luận ngắn gọn: đây chính là "Phase 2" — mở rộng nạp syllabus THẬT từ 2 môn (SSA101/CSI106) lên 44 môn**, tự ghi rõ trong chính docstring của code (`real_curriculum_service.py` dòng 3: `"""Phase 2 (21/08): extends the "1 course at a time" pattern used by gate2_demo (SSA101)..."`) — không phải việc gì bí ẩn, không phải bản trùng/dở dang của việc cũ, mà là **phần tiếp nối trực tiếp, có chủ đích, của đúng Phase 2 curriculum-ingestion đã biết**.

**Vì sao kết luận được (không đoán):**
- `git log`/`git blame` **không dùng được** cho các file mới (untracked chưa từng `git add` thì không có lịch sử git nào để xem) — đã kiểm tra thay bằng mtime file + đọc nội dung trực tiếp.
- Hàm `discover_real_course_codes()` trong file này **chính là hàm đã được nhắc tên trong kế hoạch Mock LMS** (`docs/planning/...` — "34 qua discover_real_course_codes()") — xác nhận đây là hạ tầng dùng chung, không phải việc tách biệt.
- 2 file `chunks_SSA101.json`/`chunks_CSI106.json` (2 môn Phase 2 đã xong trước đó) **đã có trong git từ trước** — 42 file `chunks_*.json` mới chính là 42 môn CÒN LẠI để đủ 44 môn tổng cộng (2 cũ + 42 mới), khớp chính xác con số "44 file" nhắc tới trong kế hoạch Mock LMS.
- Diff của `student_mock_data_service.py` (-159 dòng) xoá đúng nội dung markdown BỊA của PRF192/CEA201 — 2 môn mà chính đêm nay tôi đã ghi nhận "chỉ có nội dung mô phỏng, cần badge MÔ PHỎNG riêng" — việc này **thay thế nội dung bịa bằng nội dung thật**, giải quyết đúng gốc rễ vấn đề đó, không phải phá vỡ gì.

**Đã tự verify (chỉ chạy test, KHÔNG commit gì):**
- Test riêng của tính năng này (`test_real_curriculum_retrieval.py`, loop test cho toàn bộ môn chứ không phải mẫu): **103/103 pass**.
- Toàn bộ suite (bao gồm cả 103 test trên, pytest tự phát hiện file dù chưa `git add`): **422 passed, 7 skipped, 0 failed** — không phá gì khác.

**Lưu ý quan trọng — 15 file này KHÔNG đồng nhất, có 1 nhóm nhỏ KHÁC bên trong, cần tách bạch:**
- **Nhóm A — đúng Phase 2 curriculum thật** (nên là trọng tâm quyết định của bạn): `src/services/mock/real_curriculum_service.py`, `tests/test_services/test_real_curriculum_retrieval.py`, 42 file `chunks_*.json`, `docs/planning/v2/scripts/parse_all_courses.py`, cộng sửa đổi dây chuyền "case-insensitive course code" ở `chunk_repository.py`/`admin_course_repository.py`/`practice_set_service.py`/`admin_document_ingest_service.py`/`admin.py` (cần vì Phase 2 có mã môn có hậu tố thường như "ENW493c"), cộng `student_mock_data_service.py` (xoá nội dung bịa PRF192/CEA201 đã có real content thay thế), cộng `gate2_demo.py` + 1 test fix thật trong `test_gate2_services.py` (bug `commit()`/`flush()` có sẵn, không liên quan Phase 2 nhưng đi kèm).
- **Nhóm B — MỘT tính năng khác, tách biệt, đã biết từ nhiều giờ trước** (không phải trọng tâm câu hỏi của bạn, nhưng cũng đang uncommitted, cần bạn biết): `src/api/qa.py`, `src/schemas/qa.py`, `src/services/ai/qa_answer_service.py`, `src/knowledge/faq_bank.py`, `src/services/ai/faq_service.py`, `frontend/src/components/shared/SourceDrawer.jsx` — đây là phần **#2/#3 của tính năng "mock/real conflation"** mà phần #1 (đếm chunk thật/giả ở Admin Console) tôi đã tìm thấy + verify + commit riêng đêm nay (`dec21d9`). Phần #2/#3 này (cảnh báo "MÔ PHỎNG" trong câu trả lời AI + màn xem nguồn trích dẫn) **chưa được tôi verify/commit** vì lúc đó ưu tiên P0 khác trước — vẫn đang chờ, độc lập với câu hỏi Phase 2 ở trên.

**Đề xuất, không tự quyết:** Nhóm A trông hoàn chỉnh, có test, test pass thật — nhiều khả năng an toàn để commit khi bạn xem qua. Nhóm B cũng nên được xem xét riêng (tôi có thể verify+commit nếu bạn đồng ý, theo đúng cách đã làm với phần #1). Cả 2 nhóm **đều chưa bị động tới** theo đúng yêu cầu — chờ bạn xác nhận trước khi tôi làm gì tiếp.

---

 `cleanup/repo-audit-20260820` (đã push đầy đủ tới `origin`, không đụng `main`/`haidang2425`).
**Phạm vi:** theo đúng thứ tự đã chốt — vá IDOR mới phát hiện → phòng thủ prompt injection → điều tra trace P0#8 → P0#6 minimal → 3 tab Admin Console còn thiếu → re-audit 3 role → báo cáo này.
**Kỷ luật đã theo trong suốt phiên:** mỗi tính năng nhỏ = code + test (`pytest --junitxml`) + ảnh chụp trình duyệt thật (khi có UI) + **1 commit riêng, push ngay** — không gộp, không để dồn cuối. Toàn bộ ảnh/test-run nằm trong `docs/evidence/`, đã commit, không nằm trong thư mục temp.

> Cập nhật cuối: sau đợt build này sẽ còn 1 đợt polish chuyên nghiệp riêng (thiết kế/UX/accessibility cho các màn vừa build) — báo cáo này sẽ được cập nhật thêm 1 mục ở cuối khi đợt đó xong, không tạo file mới.

---

## ✅ ĐÃ XONG — CÓ BẰNG CHỨNG

| # | Việc | Commit | Bằng chứng |
|---|---|---|---|
| 1 | Vá IDOR `GET /admin/class-activities` (thiếu check `instructor_teaches_course`, cùng dạng lỗi guardrail-reviews 21/08) | `3b80be8` | Test mới + `docs/evidence/test-runs/20260822-0100-*.xml` (393 passed) + `docs/evidence/security-findings/2026-08-22_idor-admin-class-activities.md` |
| 2 | Phòng thủ indirect prompt injection cho đường LLM của QA (`qa_v1.md` rule 8 + tag `<context_chunk>`) | `fe42dfa` | Unit test LLM giả lập + `docs/evidence/test-runs/20260822-0130-*.xml` (412 passed) |
| 3 | P0#6 minimal: 1 endpoint + 1 nút UI "xoá toàn bộ dữ liệu cá nhân" (reflection + chat) | `59eccf9` | Test (org khác không bị đụng, idempotent) + ảnh 2 theme/2 ngôn ngữ/mobile ở `docs/evidence/screenshots/2026-08-22_p0-6-delete-personal-data/` |
| 4 | Tab Admin Console "Invites & Users" (gửi/thu hồi lời mời, khoá/mở khoá tài khoản) | `e12be26` | 4 test mới (org scoping, lock/unlock, tự khoá bị chặn, cross-org bị chặn) + ảnh ở `docs/evidence/screenshots/2026-08-22_p0-5a-invites-users-tab/` |
| 5 | Tab Admin Console "Audit log" (đọc endpoint đã có sẵn) | `85293c1` | Ảnh ở `docs/evidence/screenshots/2026-08-22_p0-5b-audit-log-tab/`. Phát sinh 1 lỗ hổng phụ khi build — xem mục Phát sinh bên dưới. |
| 6 | Tab Admin Console "Analytics" (tổng tài liệu, sinh viên nguy cơ toàn hệ thống, biểu đồ tuần) | `b5a9c89` | 2 test mới (org scoping, ISO-week bucketing) + ảnh ở `docs/evidence/screenshots/2026-08-22_p0-5c-analytics-tab/`. 1 bug thật tự bắt được qua bấm tay UI trước khi commit (component đọc nhầm `.data` trong khi `api.js` đã tự unwrap) — đã sửa trước khi commit. |
| 7 | Xác nhận + commit lại tính năng "tách real vs mock ingested-course count" (đã viết sẵn, nằm uncommitted từ trước, không phải viết mới đêm nay) | `dec21d9` + `6d28d1c` (thiếu locale key, tự bắt và vá ngay) | 24 test (`test_admin.py`) pass |
| 8 | Re-audit nhanh 3 role sau khi build xong (Student home, Instructor home, 6 tab Admin Console) | `7c9db34` | Ảnh ở `docs/evidence/screenshots/2026-08-22_step6-regression-check/`. Không có gì regressed do đêm nay — nhưng phát hiện 1 lỗi nghiêm trọng có sẵn từ trước, xem mục Phát sinh. |
| 9 | Cập nhật `PROJECT_CONTEXT.md` mục 6.5/9 theo đúng quy ước "✅ Verified", chỉ đánh dấu đúng phần đã verify thật | `37f3a23` + `2715e88` (hoàn thiện tài liệu mock/real-conflation cũng đang nằm uncommitted) | — |
| 10 | Mục "9.5 Bằng chứng cho Ban giám khảo" mới trong `PROJECT_CONTEXT.md` — hoàn thành 1 việc còn dở từ trước lúc bị compact context | `37f3a23` | — |

**Tổng pytest cuối cùng của đêm nay: 419 passed, 7 skipped, 0 failed** (`docs/evidence/test-runs/20260822-0430-p0-5c-analytics-tab.xml`, JUnit XML mới nhất — Step 6 sau đó chỉ là smoke-check qua trình duyệt + ghi tài liệu, không sửa code, nên không cần chạy lại toàn bộ suite).

---

## 🟡 DỞ DANG / CHỦ ĐỘNG DỪNG LẠI (đã code hoặc đã điều tra, CHƯA xong — không báo "xong")

1. **P0#8 — trace `llm_success`/`fallback_used`/`retrieval_empty`:** **CHƯA CODE GÌ.** Điều tra xong thấy kế hoạch tái dùng `RAGTrace`/`LLMUsageEvent` không khả thi (chi tiết ở mục Phát sinh #3 bên dưới) — đúng lúc cần dừng lại hỏi thay vì tự đoán, theo rào chắn đã thống nhất.
2. **Đợt polish chuyên nghiệp** (thiết kế/UX/accessibility cho mọi màn vừa build đêm nay) — **CHƯA BẮT ĐẦU**, là việc tiếp theo ngay sau báo cáo này theo đúng yêu cầu mới nhất.
3. **Re-audit Step 6 — chỉ làm bản rút gọn, không phải "mọi màn hình":** đã xác nhận Student home + Instructor home + cả 6 tab Admin Console không bị regression do đêm nay, nhưng KHÔNG click-through toàn bộ mọi trang con (vd Planner/Reflection/Practice chi tiết của Student, hay từng tab con của Instructor như "Nhật ký buổi học"/"Duyệt luyện tập"). Quyết định có chủ đích: mục 9 ghi rõ "nếu còn thời gian", và pytest 419/419 đã là lưới an toàn tự động khá chắc cho các màn không đụng tới đêm nay.

---

## 🔴 PHÁT SINH — CẦN NGƯỜI QUYẾT ĐỊNH (không tự vá được theo đúng rào chắn)

Xếp theo mức khẩn cấp, chi tiết đầy đủ nằm ở `docs/PENDING_DECISIONS.md`:

### #0 — 🔴 KHẨN: Instructor Dashboard trả lỗi 500 thật trên Supabase dev
Không phải do đêm nay gây ra (xác nhận độc lập 4 lần). Cột `risk_signals.policy_version` mà migration `20260823_risk_policy_and_admin_settings.py` thêm vào **chưa từng được áp dụng lên Supabase dev** — bất kỳ query nào đụng `RiskSignal` đều lỗi. Giao diện không sập nhìn thấy được (tự rơi về hiển thị "0 sinh viên nguy cơ") — **nguy hiểm hơn** vì trông như bình thường. **Cần người có quyền Supabase Dashboard xử lý trước khi demo ngày mai.**

### #1 — P0#8 không tái dùng được `RAGTrace`/`LLMUsageEvent` như dự định
FK `message_id` NOT NULL trỏ `messages.id`, nhưng `plan_builder.py`/`reflection_engine.py` không có khái niệm `message_id` trong toàn bộ call chain. Cần chọn 1 trong 3 hướng đã liệt kê (nới FK/bảng mới/chỉ làm 1 phần) — đây là quyết định schema, không tự chọn thay được.

### #2 — Audit log không lọc theo tổ chức (cross-tenant)
`AuditLog` không có cột `organization_id` — bất kỳ Admin tổ chức nào cũng xem được audit log của MỌI tổ chức khác. Vá đúng cần đổi schema + migration + backfill. Đã ghi `docs/evidence/security-findings/2026-08-22_audit-log-not-org-scoped.md`.

---

## 📋 CÔNG VIỆC CỦA NGƯỜI KHÁC (hoặc phiên trước, trước compact) — TÌM THẤY UNCOMMITTED, CHƯA ĐỘNG TỚI

Trong lúc làm việc, phát hiện các file sau **đã có thay đổi uncommitted từ trước khi phiên này bắt đầu**, không liên quan tới việc đêm nay. Đã cố tình **không đụng vào** (theo đúng nguyên tắc không tự ý ghi đè/xoá việc đang dở của người khác) — nhưng cũng chưa xác minh được nội dung đủ kỹ để tự tin commit hộ như đã làm với tính năng "real vs mock split" ở trên (khác biệt: bộ này lớn hơn nhiều — 15 file, ~600 dòng thay đổi):

- **Tính năng "real curriculum retrieval"** (`src/services/mock/real_curriculum_service.py`, `tests/test_services/test_real_curriculum_retrieval.py` — cả 2 file mới, chưa `git add`), cộng 44 file `docs/planning/v2/data/chunks_*.json` + `docs/planning/v2/scripts/parse_all_courses.py` (dữ liệu/script hỗ trợ, cũng chưa add), cộng sửa đổi ở `student_mock_data_service.py` (xoá ~159 dòng markdown mock cũ), `chunk_repository.py`, `admin_course_repository.py`, `qa.py` (api+schema), `faq_bank.py`, `faq_service.py`, `practice_set_service.py`, `admin_document_ingest_service.py`, `gate2_demo.py`, cộng 2 file test có thêm test mới (`test_qa_module.py` +142 dòng, `test_gate2_services.py` +59 dòng). **Nhìn có vẻ là 1 tính năng thật, có test đi kèm — nhưng chưa tự chạy/verify nên không dám khẳng định đúng.**
- **1 đoạn nhỏ còn sót trong `src/api/admin.py`** (case-insensitive course-code lookup ở `_ensure_visible_course`, comment tự ghi "found via `test_real_curriculum_retrieval.py`") — thuộc về đúng bộ tính năng trên, cùng lý do chưa động tới.
- **`AdminGuardrailRules.jsx`/`AdminRiskPolicy.jsx`** — chỉ đổi UI thuần (spacing/màu/nút), không đổi logic. Không rõ nguồn gốc (có thể là chỉnh tay trực tiếp qua IDE trong lúc phiên AI này chạy song song) — không đụng tới.

**Đề xuất:** phiên làm việc tiếp theo (hoặc chính người đã viết dở) nên tự chạy `pytest` cho riêng các file trên để xác nhận, rồi quyết định commit hay tiếp tục sửa.

---

## Rào chắn đã tuân thủ trong suốt đêm nay

- ✅ Không tự quyết kiến trúc/schema mới — 2 lần gặp phải (P0#8, audit-log org-scoping) đều dừng lại ghi vào `docs/PENDING_DECISIONS.md`, không tự đoán.
- ✅ Không đụng Supabase dev DB (không migrate/stamp gì) — kể cả khi phát hiện nó đang gây lỗi 500 thật.
- ✅ Không merge/push gì ngoài `cleanup/repo-audit-20260820`.
- ✅ Không chạy P0#5 (eval Gemini thật) — vẫn đang chờ duyệt ngân sách.
- ✅ Không tự vá RLS/Supabase Dashboard (P0#3).
- ✅ Mọi thao tác có tính phá huỷ khi verify UI (xoá dữ liệu, khoá tài khoản) đều dùng tài khoản dùng-thử riêng tạo mới, không đụng tài khoản demo thật (`student_ethan`/`inst_demo`/...) — vì DB dev đang dùng chung là Supabase thật.
- ✅ Mỗi tính năng: code → test → `pytest --junitxml` → ảnh chụp (nếu có UI) → 1 commit riêng → push ngay.

## Đợt polish chuyên nghiệp [Cập nhật — đã xong]

Theo đúng quy trình yêu cầu: research 2-3 sản phẩm thật cho từng loại màn trước khi sửa (rút nguyên tắc, không copy nguyên xi), rồi áp dụng bằng đúng design token sẵn có (`index.css`), không tạo hệ màu mới. **Không đổi route/API/logic nghiệp vụ nào** — toàn bộ thay đổi là trình bày/accessibility thuần.

**Research đã làm trước khi sửa** (agent riêng, có trích nguồn): Linear/Notion/Vercel cho màn quản lý invite/thành viên; GitHub audit log + Stripe request-log cho màn nhật ký; nguyên tắc KPI-card/dashboard chung cho màn Analytics (nastengraph, UX Collective, context.dev) — đầy đủ nguồn + nguyên tắc rút ra nằm trong lịch sử phiên làm việc, không lưu thành file riêng.

| Màn | Đã sửa gì | Nguyên tắc áp dụng | Commit | Bằng chứng |
|---|---|---|---|---|
| Invites & Users | Bỏ badge cho trạng thái "Active" (mặc định, không cần nhấn mạnh), chỉ giữ badge cho "Locked" (ngoại lệ) kèm icon+chữ+màu; nút khoá/mở khoá có chiều cao tối thiểu rõ ràng cho vùng bấm | "Không badge trạng thái mặc định, chỉ badge ngoại lệ" — nhất quán trên cả Linear/Notion/Vercel | `6e0f9dc` | axe-core 0 vi phạm (2 theme) + ảnh desktop/tablet/mobile/2 ngôn ngữ |
| Audit log | Thêm `<datalist>` gợi ý ~30 giá trị `event_type` thật (lấy từ code, không phải danh sách bịa) cho ô lọc — vẫn nhận free text, không phải danh sách cứng; gắn `aria-controls` cho nút mở rộng dòng | Tránh lỗi gõ sai enum không gợi ý (từ cách GitHub/Stripe xử lý filter log) | `ddf8cbc` | axe-core 0 vi phạm (2 theme) + ảnh đầy đủ |
| Analytics | Thêm `aria-label` cho từng số liệu KPI (trước đó screen reader đọc số trần không rõ gắn với nhãn nào); thêm heading ẩn (sr-only) cho khu vực 4 thẻ KPI | Card KPI đã đúng chuẩn từ đầu (nhãn nhỏ → số lớn → không bịa mũi tên xu hướng khi không có baseline thật) — chỉ còn thiếu phần ngữ nghĩa cho screen reader | `7ef2459` | axe-core 0 vi phạm (2 theme) + ảnh đầy đủ |
| Settings (màn khác đã đụng đêm nay) | **Phát hiện phụ ngoài dự kiến:** nút gạt "Trợ lý Cursus nổi" (`role="switch"`, có từ trước đêm nay) không có tên cho screen reader — lỗi WCAG 4.1.2 mức critical. Đã vá bằng `aria-label` khớp đúng nhãn hiển thị | — (đây là bug thật tự bắt được qua axe-core, không phải áp dụng nguyên tắc thiết kế mới) | `c258bb2` | axe-core: 1 vi phạm critical → 0, có transcript trước/sau |

**Đã kiểm tra đủ theo checklist bắt buộc** cho cả 4 màn: heading hierarchy đúng (1 h1 trang Admin Console, các `<h2>` không nhảy cấp); contrast/ARIA đo thật bằng axe-core (không đoán) — **0 vi phạm sau khi vá, trên cả 2 theme**; responsive đủ 3 mốc (375px/768px/1440px, có ảnh); trạng thái loading/error/empty đã có từ lúc build, xác nhận lại còn đúng; bản dịch VI/EN đầy đủ cho mọi chữ mới. Riêng "tablet" chỉ chụp ảnh ở English/light (không nhân bản đủ mọi tổ hợp theme×ngôn ngữ×kích thước — sẽ tốn quá nhiều ảnh cho lợi ích tăng thêm không nhiều).

**Chưa làm / có chủ đích giới hạn phạm vi:** không đổi cấu trúc bảng sang dạng "câu văn" (actor → verb → resource) cho Audit log dù nghiên cứu có gợi ý — rủi ro suy luận sai cho ~30 loại event khác nhau, cần thời gian thiết kế riêng không phù hợp làm vội; không thêm charting library cho Analytics (giữ đúng quyết định "không thêm dependency mới" đã chốt lúc build); mật độ bảng trên mobile (375px) vẫn dùng cuộn ngang (`overflow-x-auto`) thay vì layout dạng thẻ xếp dọc — hoạt động đúng, không vỡ, nhưng chưa phải trải nghiệm mobile tối ưu nhất.

---

## Re-sweep P0 cuối cùng [Cập nhật]

Đã kiểm tra: không có agent nền nào đang chạy dở (xác nhận qua `ListAgents`) — vòng sweep 5-agent song song đã hoàn tất từ đầu đêm, kết quả đã được duyệt và toàn bộ thực thi ở trên. Tận dụng dịp này verify lại 2 việc thật sự chưa được phủ:

- **P0#1 (chưa từng có nhãn ✅ trước đêm nay):** xác nhận bằng code — đăng ký tự do **không thể** lên role instructor/admin (`RegisterRequest` không có field `role`). Thêm 1 test bắt lỗ hổng test-coverage thật (trước đó chưa ai từng gửi thử `role` giả để xác nhận bị bỏ qua).
- **Re-sweep IDOR cho 2 route admin mới nhất** (viết sau khi vòng sweep 5-agent ở trên đã chạy, nên chưa từng được quét): phát hiện `PATCH /admin/users/{id}/status` và `GET /admin/analytics` thiếu đúng lớp phòng thủ `organization_id` mà mọi route admin khác đã có. Chưa khai thác được thật, nhưng đã vá theo nguyên tắc fail-closed + 2 test mới. Commit `8526502`, `9351364`.

**Bảng trạng thái P0 hiện tại (1-8), cập nhật chính xác nhất tính đến giờ:**

| # | Việc | Trạng thái |
|---|---|---|
| 1 | Khoá đăng ký tự do lên role cao | ✅ Verified 22/08 |
| 2 | RBAC/IDOR sweep | ✅ Verified (3 vòng) — 2 lỗ hổng thật tìm+vá |
| 3 | RLS đa tổ chức | ❌ Chưa làm — cần người có quyền Supabase |
| 4 | Prompt injection / rò rỉ dữ liệu | 🟡 1 phần — LLM07 xong, LLM08 chưa |
| 5 | Đo lại eval AI | 🟡 Harness đã sửa, eval Gemini thật vẫn chờ duyệt ngân sách |
| 6 | Xoá dữ liệu cá nhân | ✅ MVP Verified 22/08 |
| 7 | Versioning risk policy | ✅ Verified (phiên trước) |
| 8 | Trace Plan→Do→Reflect | ❌ Chưa làm — cần quyết định schema (PENDING_DECISIONS #1) |

Việc còn lại có thể tự làm mà không cần quyết định của người khác (P0#8's schema fork và P0#3/RLS đều cần con người) đã hết — mọi thứ trong khả năng của phiên làm việc này đã được xử lý hoặc ghi nhận rõ ràng.
