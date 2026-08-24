> **LƯU Ý:** Nhánh cleanup/repo-audit-20260820 đề cập trong tài liệu này đã hoàn thành nhiệm vụ, được merge toàn bộ vào nhánh haidang2425 và đã bị xóa.

# Plan thi công — Giai đoạn 3 (23/08/2026)

> Giai đoạn 0-2 đã được duyệt (`AUDIT_FINAL_23AUG.md`, `RESEARCH_FINAL_23AUG.md`, `EVALUATION_FINAL_23AUG.md`). Thứ tự checkpoint dưới đây theo đúng chỉ đạo: mức độ nghiêm trọng trước, không phải effort thấp trước. Mỗi checkpoint: mô tả cụ thể, effort, cách verify, tách đủ nhỏ để commit riêng.
>
> **Quy tắc bắt buộc áp dụng cho mọi checkpoint (không lặp lại ở từng mục):** data thật đã có, không cần data mới; đủ VI/EN (đọc/sửa đúng file locale); contrast/heading không đổi ngoài phạm vi sửa; SQLite/Postgres local khi cần test, không đụng Supabase; không merge/push ngoài `cleanup/repo-audit-20260820`; pytest + `--junitxml` vào `docs/evidence/test-runs/` + ảnh 2 theme + 2 ngôn ngữ vào `docs/evidence/screenshots/` + commit riêng ngay sau khi xong, không dồn.

---

## Checkpoint 1 — Keyboard accessibility cho Companion Chat (ƯU TIÊN TUYỆT ĐỐI CAO NHẤT)

**File:** `frontend/src/components/student/CourseCompanionChat.jsx` (danh sách thread, dòng ~272-296).

**Mô tả cụ thể:**
- Đổi phần tử chọn thread từ `<div onClick={() => setActiveId(thread.id)}>` (dòng 273-278) sang phần tử focusable đúng chuẩn: cách đơn giản nhất là đổi `<div>` bọc ngoài thành `<button type="button">` full-width (loại bỏ hoàn toàn nhu cầu thêm `role`/`tabIndex`/`onKeyDown` thủ công — browser tự cấp Enter/Space activation), giữ nguyên nút Xoá (`<button>` icon Trash2) lồng bên trong dưới dạng `<button>` con — cần `event.stopPropagation()` đã có sẵn (dòng 288) để click Xoá không kích hoạt luôn nút cha.
- **Vấn đề kỹ thuật cần xử lý:** HTML không cho phép `<button>` lồng trong `<button>` (invalid nesting, browser sẽ tự "flatten" và phá vỡ hành vi). Giải pháp: bọc ngoài bằng `<div role="button" tabIndex={0} onClick={...} onKeyDown={handleKey}>` (không phải `<button>` thật) — đây là lựa chọn đúng khi cần 1 button lồng trong 1 vùng bấm được, tham khảo đúng pattern `RiskCaseDrawer.jsx` đã làm chuẩn trong dự án (focus trap thủ công, không cần ở đây vì đây không phải modal). `handleKey` xử lý `Enter`/`Space` → gọi `setActiveId(thread.id)`, `preventDefault()` cho phím Space (tránh cuộn trang).
- Thêm `aria-current="true"` (không phải `aria-selected`, vì đây không phải `listbox`/`tablist`) cho thread đang active, để screen reader biết đang ở hội thoại nào.
- Nút Xoá hiện đang `opacity-0 group-hover:opacity-100` (dòng 286) — chỉ hiện khi hover chuột, **không hiện khi focus bằng bàn phím**. Thêm `group-focus-within:opacity-100` vào cùng class để nút Xoá cũng hiện khi Tab vào thread đó.
- **Bonus rẻ, gộp chung 1 checkpoint vì cùng file/cùng nguyên nhân:** thêm xác nhận nhẹ trước khi xoá hội thoại (dùng `ConfirmDialog` mới xây ở Checkpoint 3 — nếu Checkpoint 3 chưa xây tới lúc này thì tạm dùng `window.confirm()`, quay lại thay bằng `ConfirmDialog` khi Checkpoint 3 xong để không tạo 2 kiểu confirm khác nhau trong cùng 1 khu vực).

**Effort:** Thấp (1 file, ~20-30 dòng thay đổi).

**Cách verify (bắt buộc TAB/Enter/Escape thật, không chỉ đọc code):**
1. Chạy `npm run dev` (frontend) + backend local (SQLite riêng, không Supabase) — đăng nhập demo student, vào `/student/companion`.
2. Test bàn phím thật: click vào ô input câu hỏi trước, nhấn `Shift+Tab` lùi về danh sách thread — xác nhận focus vào được từng thread bằng `Tab`, có outline focus-visible rõ ràng.
3. Với 1 thread đang focus (chưa active): nhấn `Enter` → xác nhận panel bên phải đổi sang đúng thread đó (giống hành vi click chuột).
4. Nhấn `Tab` tiếp vào nút Xoá của thread đang focus — xác nhận nút Xoá **hiện ra** dù không dùng chuột hover (verify `group-focus-within` hoạt động).
5. Nhấn `Enter` trên nút Xoá — xác nhận dialog xác nhận hiện lên (không xoá thẳng), `Escape` đóng được dialog, chọn "Huỷ" không xoá gì.
6. Ảnh chụp: 2 theme (sáng/tối) × trạng thái focus-visible rõ trên 1 thread bằng bàn phím (không phải hover chuột) — đặt tên rõ "keyboard-focus" để phân biệt ảnh thường.
7. `pytest tests/` (không có test JS/frontend trong bộ pytest — chỉ chạy để xác nhận không phá gì phía backend liên quan companion nếu có đụng `deleteCompanionThread`/API).

---

## Checkpoint 2 — Admin: h1 động theo tab + ARIA tab semantics (ảnh hưởng cả 7 tab)

**File:** `frontend/src/components/admin/AdminConsole.jsx` (h1 dòng 68, 8 nút tab dòng 74-147).

**Mô tả cụ thể:**
- `<h1>{t('admin.pageTitle')}</h1>` (dòng 68) hiện cố định 1 chuỗi bất kể tab nào đang mở. Đổi thành map `tab` → key locale cụ thể (ví dụ `admin.tabs.courses.heading`, `admin.tabs.academic.heading`... — thêm 8 key mới vào 2 file locale VI/EN, tái dùng label nút tab hiện có làm nội dung heading nếu chưa có tiêu đề riêng, không bắt buộc văn bản mới hoàn toàn khác).
- Container bọc 8 nút tab (dòng ~82 trở đi) thêm `role="tablist"` + `aria-label` mô tả nhóm (ví dụ "Admin Console sections").
- Mỗi nút tab thêm: `role="tab"`, `aria-selected={tab === 'courses'}` (theo đúng giá trị so sánh đang dùng để đổi class active), `aria-controls="admin-panel-{tabkey}"`, `id="admin-tab-{tabkey}"`.
- Mỗi khối nội dung tab (dòng 141-149, hiện là `{tab === 'academic' && <AdminAcademicPanel />}` 8 dòng tương tự) bọc thêm 1 `<div role="tabpanel" id="admin-panel-{tabkey}" aria-labelledby="admin-tab-{tabkey}">` quanh mỗi component con — không đổi logic render có/không, chỉ thêm wrapper.
- **Không đổi kiến trúc route/state** — vẫn giữ 1 trang nhiều tab như đã chốt ở mục 6.5 PROJECT_CONTEXT.md, chỉ thêm ARIA + heading động.

**Effort:** Thấp-Trung bình (1 file chính + 2 file locale, ~40-60 dòng, lặp lại đều theo 1 pattern cho cả 8 tab nên nhanh sau khi làm xong tab đầu tiên).

**Cách verify:**
1. Chuyển qua từng tab bằng chuột — xác nhận `<h1>` đổi đúng nội dung theo tab (xem DOM qua devtools hoặc đọc trực tiếp text hiển thị).
2. Dùng trình đọc màn hình (Windows Narrator, có sẵn trên máy, `Ctrl+Win+Enter` bật) hoặc tối thiểu devtools Accessibility tree (Chrome DevTools → Elements → Accessibility) — xác nhận mỗi nút tab đọc ra đúng role "tab", trạng thái "selected" đổi đúng khi chuyển tab.
3. `pytest tests/` — không đổi backend, chạy để xác nhận không có regression ngoài ý muốn (không kỳ vọng test nào liên quan trực tiếp, đây là bước xác nhận an toàn).
4. Ảnh chụp: 2 theme × 2 ngôn ngữ, mỗi ảnh chụp 1 tab bất kỳ (ví dụ "Curriculum") để xác nhận heading + active tab style không vỡ.

---

## Checkpoint 3 — Confirm dialog dùng chung cho mọi hành động không hoàn tác

**Bước 3.0 — Xây component dùng chung trước (làm 1 lần, dùng lại cho mọi call site dưới đây):**

- Tạo `frontend/src/components/shared/ConfirmDialog.jsx` — tái dùng ĐÚNG pattern focus-trap/ESC/role="dialog"/restore-focus đã có trong `DeferTaskDialog.jsx` (đọc kỹ trước khi viết, copy cấu trúc `useEffect` xử lý Tab-trap + ESC + restore focus, dòng 18-49 của file đó), tổng quát hoá thành props: `open`, `title`, `message` (string hoặc node, mô tả rõ hậu quả cụ thể — không dùng chung 1 câu "Bạn có chắc?" cho mọi nơi), `confirmLabel`, `cancelLabel`, `danger` (bool — `true` dùng `btn` với `--color-danger`/`text-danger` cho nút xác nhận, `false` dùng `btn-accent` mặc định), `onConfirm`, `onCancel`, `busy` (disable nút xác nhận + đổi label "Đang xử lý…" khi đang gọi API, giống `DeferTaskDialog` dòng 154-167).
- Không tạo màu/token mới — dùng đúng `--color-danger`/`--color-warning`/`--color-accent` đã có trong `index.css`.

**Bước 3a — Wire vào khu vực Giảng viên (4 call site, 1 commit):**
1. `InstructorHome.jsx` — nút "Đánh dấu đã can thiệp" trên `AlertCard` (dòng ~88-92, `onClick={(e) => { e.stopPropagation(); onIntervene(alert.id); }}`) → đổi thành mở `ConfirmDialog` trước, message nêu rõ "Đánh dấu đã can thiệp cho {tên SV} — hành động này sẽ ghi vào lịch sử can thiệp, không xoá được." `onConfirm` mới gọi `onIntervene(alert.id)`.
2. `RiskCaseDrawer.jsx` — nút "Đánh dấu đã can thiệp" ở footer (cùng hành động, entry point thứ 2) → dùng chung logic/message như (1), tránh viết 2 lần — cân nhắc nâng state quản lý `ConfirmDialog` lên component cha chung (`InstructorHome.jsx`) nếu cả 2 nơi cùng gọi 1 callback `onIntervene`, để không phải đồng bộ state confirm ở 2 nơi riêng biệt.
3. `InstructorPracticeQueuePanel.jsx` — nút "Xuất bản" (dòng ~186-191): message nêu rõ "Xuất bản bộ luyện tập này — sinh viên sẽ thấy ngay lập tức." Nút "Từ chối" cũng nên có confirm nhẹ hơn (không bắt buộc, effort thấp nếu còn giờ) vì reject không phải hành động nguy hiểm bằng publish.
4. Hàng đợi guardrail-review (khối trong `InstructorHome.jsx`, dòng ~390-395) — nút "Mở chặn" bắt buộc qua `ConfirmDialog` với message nhấn mạnh đây là quyết định academic-integrity ("Mở chặn nghĩa là câu hỏi này sẽ được AI trả lời bình thường trở lại"); nút "Giữ chặn" không cần confirm (giữ nguyên trạng thái an toàn hơn, không phải hành động rủi ro).

**Bước 3b — Wire vào khu vực Admin (2 call site, 1 commit riêng):**
5. `AdminAcademicPanel.jsx::handleDeleteExam` (dòng ~119-127) — hiện xoá thẳng không confirm, khác mọi hành động xoá khác trong Admin. Thêm `ConfirmDialog`, message nêu rõ "Xoá lịch thi {mã môn} — task 'Ôn thi' tự sinh cho sinh viên dựa trên lịch này có thể bị ảnh hưởng."
6. `AdminGuardrailRules.jsx` — nút "Restore defaults" (dòng ~44-51) — thêm `ConfirmDialog`, message "Khôi phục toàn bộ rule guardrail về mặc định — mọi tuỳ chỉnh hiện tại sẽ mất."
7. **Bonus nếu còn giờ (không bắt buộc, effort rất thấp):** `AdminAcademicPanel.jsx` nút "Lưu học kỳ" — thêm 1 dòng cảnh báo tĩnh (không cần dialog, chỉ text màu `--color-warning` phía trên nút Lưu) nhắc rõ việc ghi đè lựa chọn ngày của sinh viên, không chặn hành động, chỉ tăng nhận thức trước khi bấm.

**Bước 3c — Mock LMS (1 call site, 1 commit riêng — khác stack, không dùng React):**
8. `mock-lms/app/templates/course_detail.html` (form sửa deadline) — vì đây là Jinja2 + vanilla JS, không tái dùng `ConfirmDialog` React được. Thêm 1 dòng JS thuần: `onsubmit="return confirm('Đổi deadline từ {{ old_value }} sang giá trị mới?')"` trên `<form>`, đúng khuyến nghị Gap 7 (native `confirm()`, tương xứng quy mô tối giản đã chọn cho Mock LMS — không xây modal riêng cho app phụ trợ này).

**Effort tổng Checkpoint 3:** Trung bình (1 component mới dùng chung + 7 call site sửa, chia 3 commit theo 3a/3b/3c ở trên).

**Cách verify (từng bước, cho cả 3 sub-checkpoint):**
1. Với mỗi call site: bấm nút hành động → xác nhận `ConfirmDialog` (hoặc `confirm()` native cho Mock LMS) hiện lên **trước khi** API bị gọi (kiểm tra qua Network tab devtools — request chỉ xuất hiện sau khi bấm "Xác nhận", không xuất hiện ngay khi bấm nút ban đầu).
2. Bấm "Huỷ"/Cancel — xác nhận API **không được gọi**, trạng thái UI không đổi.
3. Bấm "Xác nhận" — xác nhận API được gọi đúng 1 lần (không double-submit), trạng thái UI cập nhật đúng như trước khi có confirm.
4. `ConfirmDialog` (React): test `Escape` đóng dialog, test Tab-trap không thoát ra ngoài dialog khi đang mở (giống cách `DeferTaskDialog` đã hoạt động).
5. `pytest tests/` sau mỗi sub-checkpoint — các call site này không đổi API backend, chỉ đổi thời điểm gọi ở frontend, nên kỳ vọng **không có test nào fail mới**; chạy để xác nhận.
6. Ảnh chụp: mỗi sub-checkpoint 1 bộ ảnh (dialog đang mở, 2 theme) — không cần đủ 2 ngôn ngữ cho từng dialog riêng lẻ nếu quá tốn thời gian, nhưng ít nhất 1 dialog đại diện (ví dụ can thiệp risk) chụp đủ 2 ngôn ngữ để xác nhận bản dịch không vỡ.

---

## Checkpoint 4 — Label/aria cho SemesterSetupWizard.jsx

**File:** `frontend/src/components/student/SemesterSetupWizard.jsx` (label-input dòng ~245-261, ô lịch tuần dòng ~340-357, bảng thiếu `scope` nếu có).

**Mô tả cụ thể:**
- 3 field "Tên học kỳ"/"Ngày bắt đầu"/"Ngày kết thúc" (dòng 245-261): thêm `id` duy nhất cho mỗi `<input>`, thêm `htmlFor` khớp trên `<label>` tương ứng (hiện `<label>` không trỏ `htmlFor` vào đâu).
- Ô lịch tuần (bước 2, dòng 340-357): mỗi nút ô hiện không có `aria-label` khi chưa gán môn. Thêm `aria-label` động, ví dụ: `` `${dayName}, ${startTime}-${endTime}, ${assignedCourse || (lang === 'vi' ? 'chưa gán môn' : 'unassigned')}` `` — đủ ngữ cảnh cho screen reader dù ô đang trống.
- Nếu có `<table>` trong wizard (theo ghi chú audit "thiếu scope=col/row trên th") — thêm `scope="col"`/`scope="row"` tương ứng.
- **Áp dụng luôn cho `LecturePlanPanel.jsx`** (cùng lỗi label-input, ưu tiên trung bình theo `EVALUATION_FINAL_23AUG.md` — gộp vào cùng checkpoint vì cùng nguyên nhân/cùng fix, nếu effort phát sinh thấp như dự kiến).

**Effort:** Thấp (2 file, phần lớn là thêm `id`/`htmlFor`/`aria-label`, không đổi logic).

**Cách verify:**
1. Devtools Accessibility tree hoặc Narrator: focus vào từng input "Tên học kỳ"/"Ngày bắt đầu"/"Ngày kết thúc" — xác nhận tên đọc ra đúng nhãn (không chỉ "textbox" trống).
2. Tab tới 1 ô lịch tuần chưa gán môn — xác nhận đọc ra đúng câu mô tả đầy đủ (thứ/giờ/trạng thái), không chỉ "button".
3. `pytest tests/` — không đổi backend, chạy xác nhận an toàn.
4. Ảnh chụp: 2 theme × 2 ngôn ngữ cho màn hình wizard bước 1 (label) và bước 2 (lịch tuần).

---

## Tổng effort ước lượng & thứ tự thực thi

| # | Checkpoint | Effort | Số commit dự kiến |
|---|---|---|---|
| 1 | Companion Chat keyboard a11y | Thấp | 1 |
| 2 | Admin h1/tab-ARIA | Thấp-Trung bình | 1 |
| 3.0 | `ConfirmDialog` component dùng chung | Thấp | (gộp vào 3a) |
| 3a | Wire Lecturer (4 call site) | Trung bình | 1 |
| 3b | Wire Admin (2 call site) | Thấp | 1 |
| 3c | Wire Mock LMS (1 call site) | Rất thấp | 1 |
| 4 | Label/aria SemesterSetupWizard + LecturePlanPanel | Thấp | 1 |

**Tổng: 6 commit dự kiến**, mỗi commit kèm pytest evidence + ảnh 2 theme (và 2 ngôn ngữ ở những chỗ có thay đổi text hiển thị).

**Không có quyết định kiến trúc/schema nào phát sinh** — toàn bộ Checkpoint 1-4 là sửa frontend thuần (JSX/ARIA/1 component dùng chung), không đụng migration/API contract nào.

---

**DỪNG TẠI ĐÂY — cổng chặn 2. Chờ duyệt plan trước khi bắt đầu code Checkpoint 1.**
