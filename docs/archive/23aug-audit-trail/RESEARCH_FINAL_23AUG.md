# Research — Giai đoạn 1 (23/08/2026)

> Với mỗi gap tìm được ở `docs/AUDIT_FINAL_23AUG.md`: 2-3 sản phẩm SaaS/EdTech thật đang làm tốt đúng việc đó, tên + lý do cụ thể, rút nguyên tắc áp dụng được — KHÔNG copy nguyên xi, dùng đúng token có sẵn trong `frontend/src/index.css` (`--color-danger`/`--color-warning`/`--color-success`/`--color-accent`/`--color-line`...), không tạo hệ màu riêng.

---

## Gap 1 — Thiếu confirm cho hành động không hoàn tác (xuyên Lecturer/Admin/Mock LMS)

**Phạm vi:** đánh dấu can thiệp risk, publish bộ luyện tập, quyết định guardrail review, xoá lịch thi, restore guardrail defaults, lưu học kỳ ghi đè, sửa deadline Mock LMS.

| Sản phẩm | Vì sao đáng học |
|---|---|
| **Linear** | Mọi hành động archive/delete issue đều có 1 trong 2 pattern rõ ràng: (a) modal xác nhận ngắn có nút màu đỏ + phím tắt nhấn lại để xác nhận, HOẶC (b) undo toast 5-8 giây sau khi hành động đã xảy ra — không bao giờ để hành động phá huỷ chạy im lặng không có đường lùi nào. Linear chọn (b) cho hành động tần suất cao (archive), (a) cho hành động hiếm/nặng (xoá workspace). |
| **Gmail** | "Undo Send"/"Undo Archive" — toast xuất hiện ngay dưới cùng, có nút "Hoàn tác", tự biến mất sau vài giây. Nguyên tắc: hành động tần suất cao không nên chặn bằng modal (gây mệt mỏi/click-through vô thức), thay vào đó cho làm ngay + cửa sổ ngắn để sửa sai. |
| **Notion** | Xoá block/page chuyển vào Trash (không mất ngay), có thanh "Page moved to Trash — Undo". Chỉ xoá vĩnh viễn khi dọn Trash thủ công — 2 lớp bảo vệ cho hành động phá huỷ dữ liệu người dùng đã đầu tư công sức tạo ra. |
| **GitHub** | Riêng hành động cực kỳ nguy hiểm (xoá repo) bắt gõ lại đúng tên repo vào ô input mới cho phép bấm nút xoá — mức xác nhận tăng theo mức độ nghiêm trọng, không dùng 1 loại confirm cho mọi cấp độ rủi ro. |

**Nguyên tắc rút ra, áp dụng cho Cursus (không copy màu/layout, chỉ áp dụng logic):**
- Phân loại lại các hành động theo 2 nhóm, không dùng 1 kiểu xử lý cho tất cả:
  - **Nhóm A — hiếm, hậu quả nặng, khó khắc phục** (xoá lịch thi, restore guardrail defaults, lưu học kỳ ghi đè, sửa deadline Mock LMS): modal xác nhận ngắn gọn nêu rõ hậu quả cụ thể (không chỉ "Bạn có chắc?"), dùng `--color-danger`/`--color-warning` đã có sẵn cho nút xác nhận, giữ nguyên pattern `window.confirm`/modal đã dùng nơi khác trong Admin để nhất quán — không cần xây component mới.
  - **Nhóm B — tần suất cao hơn, có thể khắc phục nhanh** (đánh dấu can thiệp risk, publish luyện tập, guardrail review): modal xác nhận nhẹ HOẶC toast "Đã thực hiện — Hoàn tác" trong vài giây (nếu API đã hỗ trợ đảo trạng thái, ví dụ un-resolve risk case) — tránh gây mệt mỏi click-through cho giảng viên thao tác hàng chục case/ngày.
- Với hành động nghiêm trọng nhất về mặt học thuật (mở chặn 1 câu hỏi "nhờ AI làm hộ"), cân nhắc yêu cầu chọn 1 lý do từ danh sách có sẵn (không phải gõ tự do) trước khi xác nhận — nhẹ hơn "gõ lại tên" của GitHub nhưng vẫn tạo độ ma sát chủ đích cho quyết định academic-integrity.

---

## Gap 2 — Admin Console: h1 tĩnh không đổi theo tab, tab-bar thiếu ARIA tab semantics

| Sản phẩm | Vì sao đáng học |
|---|---|
| **GitHub (Settings trang repo/org)** | Mỗi tab settings là 1 URL riêng (`/settings/branches`, `/settings/access`...), heading đổi theo đúng nội dung tab, tab-bar dùng `role="tablist"`/`aria-selected` chuẩn WAI-ARIA APG. |
| **Vercel Dashboard (Project settings)** | Tương tự — tab điều hướng bằng URL, mỗi tab có heading riêng phản ánh đúng ngữ cảnh, back/forward trình duyệt hoạt động đúng vì tab = route thật, không phải state ẩn trong 1 component. |
| **Stripe Dashboard** | Tab nội bộ (không đổi URL) vẫn dùng đúng `role="tab"`/`aria-selected`/`aria-controls` trỏ tới đúng `id` của panel — chứng minh kể cả khi không đổi URL, ARIA semantics vẫn giữ được trải nghiệm cho screen reader. |

**Nguyên tắc áp dụng cho Cursus:** không bắt buộc đổi kiến trúc route (Admin Console giữ 1 trang nhiều tab như hiện tại là lựa chọn hợp lệ, mục 6.5 PROJECT_CONTEXT.md đã ghi rõ "không bắt buộc gộp thành đúng 1 trang"), nhưng cần 2 việc kỹ thuật nhỏ, không đổi thiết kế:
1. `<h1>` render động theo tab đang chọn (map tên tab → tiêu đề cụ thể, dùng đúng chuỗi locale đã có).
2. Tab-bar thêm `role="tablist"` (container) + `role="tab"` + `aria-selected` (mỗi nút) + `aria-controls` trỏ `id` panel tương ứng + `id` cho mỗi panel với `role="tabpanel"` — theo đúng WAI-ARIA Tabs Pattern, không cần thư viện mới, chỉ thêm attribute vào JSX có sẵn.

---

## Gap 3 — Bảng dữ liệu thiếu `scope="col"` (toàn bộ Admin)

| Sản phẩm | Vì sao đáng học |
|---|---|
| **GitHub (bảng Issues/PR list, bảng Insights)** | Mọi `<th>` đều có `scope="col"`, một số bảng phức tạp hơn (ma trận) dùng cả `scope="row"` — pattern nhất quán toàn bộ sản phẩm, không phải ngoại lệ ở vài nơi. |
| **Airtable (grid view)** | Dù UI grid phức tạp hơn `<table>` HTML thuần, Airtable vẫn expose đúng ARIA grid role (`role="grid"`, `role="columnheader"`) để đảm bảo screen reader đọc đúng tên cột khi duyệt ô — chứng minh dữ liệu dạng bảng luôn cần "neo" cột rõ ràng dù công nghệ render là gì. |

**Nguyên tắc áp dụng:** đây là fix cơ học, không cần thiết kế lại — thêm `scope="col"` vào mọi `<th>` trong 6 bảng đã xác định (Curriculum, Users/Invites, Risk Policy + history, Audit log, Academic exams). Có thể làm 1 lượt cho cả `frontend/src/components/admin/` vì cùng 1 pattern lặp lại.

---

## Gap 4 — `CourseCompanionChat.jsx`: danh sách hội thoại không dùng được bằng bàn phím

| Sản phẩm | Vì sao đáng học |
|---|---|
| **Slack (danh sách kênh/DM sidebar)** | Mỗi item là phần tử focusable thật (không phải `div onClick` trần), Tab/Arrow key di chuyển được, Enter/Space kích hoạt — đúng pattern "listbox" hoặc đơn giản hơn là `role="button"`+`tabIndex=0`+`onKeyDown` (cách `RiskCaseDrawer.jsx` trong chính dự án này đã làm đúng cho phần tử tương tự — tự tham khảo nội bộ trước, không cần học ngoài). |
| **ChatGPT (sidebar lịch sử hội thoại)** | Cùng pattern — mỗi hội thoại trong sidebar là phần tử điều hướng được bằng bàn phím, nút xoá lồng bên trong không chặn việc focus vào item cha trước đó. |

**Nguyên tắc áp dụng:** đây là lỗi đã có sẵn cách sửa mẫu ngay trong cùng codebase — `RiskCaseDrawer.jsx` (khu vực Lecturer) đã làm đúng `role="dialog"`+focus trap; áp dụng đúng tinh thần tương tự (không cần pattern mới): đổi `<div onClick>` thành `<div role="button" tabIndex={0} onKeyDown={handleEnterOrSpace} onClick={...}>` hoặc đơn giản hơn là đổi hẳn sang thẻ `<button>` (loại bỏ nhu cầu thêm role/tabIndex thủ công), giữ nút Xoá lồng bên trong nhưng đảm bảo nó không nuốt sự kiện Tab của phần tử cha.

---

## Gap 5 — Label-input mất liên kết (`SemesterSetupWizard.jsx`, `LecturePlanPanel.jsx`, Mock LMS date input)

| Sản phẩm | Vì sao đáng học |
|---|---|
| **GOV.UK Design System** | Chuẩn tham chiếu accessibility hàng đầu cho form chính phủ — mọi `<label>` bắt buộc có `for` trỏ đúng `id` input, kể cả input ẩn/phức tạp; đây là nguyên tắc nền tảng WCAG 2.1 (1.3.1 Info and Relationships), không phải tuỳ chọn thẩm mỹ. |
| **Stripe Checkout** | Form thanh toán (độ nhạy cao, bắt buộc accessible cho compliance) — mọi input đều có label liên kết đúng `htmlFor`/`id`, kể cả input ẩn hoàn toàn về mặt thị giác (dùng `sr-only` khi cần giấu label trên UI nhưng vẫn giữ cho screen reader). |

**Nguyên tắc áp dụng:** cơ học, không cần thiết kế lại — thêm `id` unique cho từng input, `htmlFor` khớp trên `<label>` tương ứng. Với ô lịch tuần (button trống không có text), thêm `aria-label` mô tả đủ ngữ cảnh (ví dụ: "Thứ 2, 07:30-09:00, chưa gán môn — bấm để gán").

---

## Gap 6 — `PROJECT_CONTEXT.md` mục 6.3 lỗi thời (Reflect band-question đã code xong, tài liệu ghi "chưa làm")

Đây không phải gap UI/UX — là gap tài liệu. Không cần research sản phẩm ngoài, chỉ cần sửa lại dòng mô tả trong `docs/PROJECT_CONTEXT.md` mục 6.3 cho khớp code thật (việc này thuộc Giai đoạn 2/3, không phải Giai đoạn 1).

---

## Gap 7 — Mock LMS: form sửa deadline không confirm/preview

| Sản phẩm | Vì sao đáng học |
|---|---|
| **Google Calendar (sửa sự kiện lặp lại)** | Khi sửa 1 trường có ảnh hưởng dây chuyền (giờ họp định kỳ), luôn hỏi lại phạm vi áp dụng trước khi lưu — không lưu âm thầm 1 click. |
| **Canvas LMS thật (sửa due date assignment)** | Có bước xác nhận + hiển thị rõ giá trị cũ/mới trước khi Save, đặc biệt vì due date ảnh hưởng trực tiếp tới sinh viên đã dựa vào deadline cũ để lên kế hoạch — đúng bối cảnh Mock LMS đang mô phỏng. |

**Nguyên tắc áp dụng:** vì Mock LMS là app phụ trợ, tối giản có chủ đích (không cần UI phức tạp) — chỉ cần 1 bước `confirm()` (JS native, không cần modal riêng, tương xứng quy mô tối giản đã chọn cho toàn bộ Mock LMS) hiển thị rõ giá trị cũ → mới trước khi submit form.

---

## Tổng kết — không nguyên tắc nào đòi hỏi hệ màu/token mới

Toàn bộ 7 gap đều giải quyết được bằng: (1) thêm ARIA attribute có sẵn chuẩn W3C, (2) thêm `confirm()`/modal dùng đúng `--color-danger`/`--color-warning` đã có trong `index.css`, (3) sửa liên kết `label`/`id` thuần HTML, (4) đổi `div onClick` thành phần tử focusable đúng chuẩn — không cần thư viện mới, không cần thiết kế lại giao diện, không tạo màu/token riêng.
