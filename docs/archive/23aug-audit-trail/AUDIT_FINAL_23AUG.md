# Audit toàn diện production-readiness — 22/08/2026 (Giai đoạn 0)

> Hội đồng: Senior Product Designer, Senior Frontend Engineer, UX Researcher, SEO/Accessibility Specialist, Senior Backend Engineer. Phương pháp: đọc code thật + verify sống qua API (backend tạm trên SQLite riêng, port 8020, KHÔNG đụng Supabase) — không tin nguyên văn các dòng ✅ Verified cũ trong `docs/PROJECT_CONTEXT.md`, vì nhiều thay đổi đã chồng lên nhau qua nhiều phiên. 4 khu vực được audit song song bởi 4 agent độc lập (Student/Lecturer/Admin/Mock LMS+Public), tổng hợp lại ở đây.

---

## Tóm tắt điều hành

**Tin tốt:** không phát hiện dữ liệu giả/mock nào bị hiển thị như dữ liệu thật ở bất kỳ màn hình nào trong 4 khu vực — mọi nơi dùng mock (Curriculum badge, landing FAQ chat, Mock LMS assignment sinh giả) đều đã gắn nhãn đúng. Tất cả 3 role + Mock LMS đọc/ghi DB thật qua API thật, không tìm thấy hardcode ẩn mới. RBAC/ownership fail-closed đúng thiết kế.

**Vấn đề lớn nhất xuyên suốt, KHÔNG phải data giả mà là 2 nhóm hệ thống:**

1. **Thiếu xác nhận (confirm) cho hành động không thể hoàn tác/ảnh hưởng người khác** — lặp lại ở cả 3 role: Lecturer (đánh dấu can thiệp, publish luyện tập, guardrail review), Admin (xoá lịch thi, restore guardrail defaults, lưu học kỳ ghi đè SV), Mock LMS (sửa deadline không preview). Đây là pattern chưa từng bị audit trước đó xét tới (các đợt audit cũ tập trung data thật/giả và bug logic, không xét UX-risk của hành động 1-click).
2. **Accessibility có gap thật, tập trung nhiều nhất ở Admin và 2 trang "mồ côi" cũ của Student** — h1 tĩnh không đổi theo tab (Admin, ảnh hưởng 7 tab), tab-bar thiếu ARIA, 0 `scope="col"` toàn bộ bảng Admin, label-input mất liên kết ở `SemesterSetupWizard`/`LecturePlanPanel`, và nghiêm trọng nhất — `CourseCompanionChat.jsx` không chọn được hội thoại bằng bàn phím.

**1 phát hiện tài liệu lỗi thời quan trọng:** `PROJECT_CONTEXT.md` mục 6.3 vẫn ghi tính năng Reflect "hỏi khác nhau theo % hoàn thành" là "🔜 chưa làm" — thực tế đã code xong (`reflection_engine.py`), cần cập nhật lại để không đánh giá thấp tiến độ thật.

**1 bug đã biết, xác nhận vẫn còn (đã có quyết định không sửa từ trước):** `OnboardingScreen.jsx` không bao giờ hiển thị (bug `setUser` không bao giờ gọi + `App.jsx` hardcode `onboarded: true`) — không phát sinh mới, quyết định cũ vẫn hợp lý (dữ liệu hồ sơ đã seed sẵn server-side).

**Không tìm thấy lỗ hổng bảo mật mới** trong đợt này (khác phạm vi RLS/alembic đã biết, việc của leader).

---

## A. Khu vực Sinh viên

| Màn hình | Data thật/mock | Tính năng chưa nối thật | Vấn đề UX | Vấn đề Accessibility/SEO | Mức độ |
|---|---|---|---|---|---|
| Tổng quan (`StudentHome.jsx`) | Thật (DB) qua `GET /student/demo/state`; field `course` cấp cao vẫn ghim `SSA101` | Danh sách task không có nút Xoá/Thêm mới dù mục 6.3 mô tả có | Complete/Defer đều qua dialog xác nhận — tốt | Đúng 1 h1, heading không nhảy cấp | Thấp |
| Phản tư (`StudentReflection.jsx`) | Thật — band-based questions từ `reflection_engine.py:197` | — | Nút xác nhận disable đúng khi memory rỗng | 1 h1 duy nhất, label/checkbox đúng chuẩn | Thấp — **nhưng PROJECT_CONTEXT.md mục 6.3 đang lỗi thời: ghi "🔜 chưa làm" cho tính năng đã code xong** |
| Cài đặt (`SettingsScreen.jsx`) | Thật — xoá dữ liệu cá nhân có `window.confirm` | — | Dùng `confirm()` native, không đồng nhất với modal riêng nơi khác | 1 h1; toggle có `role="switch"`+`aria-checked` đúng | Thấp |
| Lập kế hoạch tuần (`/student/planner`) | Thật | — | `CapacityMeter` cảnh báo vượt quỹ trước khi xác nhận | 1 h1; label/progressbar đúng chuẩn | Thấp |
| Luyện tập (`/student/practice`) | Thật (LLM/fallback từ RAG chunk thật); quiz state client-side only (thiết kế có chủ đích) | — | "Tạo lại bộ luyện tập" không cảnh báo mất tiến độ đang làm dở | Kết quả đúng/sai MCQ không có `aria-live` | Trung bình |
| Trợ lý theo môn (`CourseCompanionChat.jsx`) | Thật — thread lưu server, badge mode phản ánh guardrail thật | — | Xoá hội thoại không có xác nhận | **Cao — chọn hội thoại là `<div onClick>` trần, không `role`/`tabIndex`/`onKeyDown`: không dùng được bằng bàn phím/screen reader** | **Cao** |
| Thiết lập học kỳ (`SemesterSetupWizard.jsx`) | Thật | — | Luồng 3 bước hợp lý | **Cao — nhiều `<label>` không có `htmlFor`/input không có `id`; ô lịch tuần không có `aria-label` mô tả** | **Cao** |
| Kế hoạch theo lịch học (`LecturePlanPanel.jsx`) | Thật | — | Có ghi chú rõ độc lập với Plan ở trang chủ | Cùng lỗi label/htmlFor thiếu liên kết | Trung bình |

**Top phát hiện:**
1. `CourseCompanionChat.jsx` — chọn hội thoại không dùng được bằng bàn phím (a11y nghiêm trọng nhất tìm được toàn bộ audit này).
2. Label-input mất liên kết lặp lại ở `SemesterSetupWizard.jsx`/`LecturePlanPanel.jsx` (2 trang "mồ côi" cũ) — dễ sửa hàng loạt.
3. Ô lịch tuần trong `SemesterSetupWizard.jsx` — ~30 ô trống không có `aria-label`, "hố đen" với screen reader.
4. **PROJECT_CONTEXT.md mục 6.3 lỗi thời** — tính năng Reflect "hỏi theo band hoàn thành" đã code xong, tài liệu vẫn ghi "🔜 chưa làm".
5. Xoá hội thoại Companion Chat không xác nhận — bất nhất với chuẩn xác nhận đã áp dụng nơi khác trong cùng khu vực.

---

## B. Khu vực Giảng viên

| Màn hình/Tab | Data thật/mock | Tính năng chưa nối thật | Vấn đề UX | Vấn đề Accessibility/SEO | Mức độ |
|---|---|---|---|---|---|
| Tab Tổng quan — số liệu | Thật, không còn fallback hardcode | Biểu đồ xu hướng tuần lịch sử thật vẫn chưa có (đã biết) | — | Ổn | Thấp |
| Tab Tổng quan — alert + roster | Thật, join `RiskEngine.assess()` thật | Cần verify runtime việc lọc theo course đã chọn có đồng bộ FE không | **Nút "Can thiệp" trên AlertCard không có confirm** | Input tìm kiếm roster không có `<label>`/`aria-label` | Trung bình |
| `RiskCaseDrawer.jsx` | Thật, đầy đủ (timeline/interventions/sharedNote đúng cam kết riêng tư) | — | Nút "Đánh dấu đã can thiệp" ở footer cũng không confirm | **Rất tốt** — `role="dialog"`+`aria-modal`+focus trap+ESC+focus restore đầy đủ, mẫu mực trong dự án | Thấp (chỉ thiếu confirm) |
| Tab "Nhật ký buổi học" | Thật | — | Lỗi hiện thô, không dịch, không Retry | **Xác nhận: chưa dùng `t()`, dùng `lang==='vi'?...` nội tuyến khắp nơi** — không đồng bộ kiến trúc i18n | Trung bình |
| Tab "Duyệt luyện tập" | Thật | — | **"Xuất bản"/"Từ chối" không xác nhận** — publish thẳng cho SV xem | Textarea/input nhiều trường chỉ có `placeholder`, không `<label>`; select filter không `aria-label` | **Trung bình-Cao** |
| Hàng đợi guardrail-review | Thật, đã vá lọc chéo lớp | — | "Giữ chặn"/"Mở chặn" không xác nhận, không toast feedback | Khối trích câu hỏi thiếu `<blockquote>`/`aria-label` | Trung bình |

**Top phát hiện:**
1. **Không có confirm cho mọi hành động "chốt case" quan trọng nhất khu vực Giảng viên** (can thiệp risk, publish luyện tập, guardrail review decision) — gap UX nghiêm trọng nhất, chưa từng ghi nhận.
2. Claim "2 tab mới chưa đồng bộ t()/Retry" ở PROJECT_CONTEXT.md **vẫn đúng khi verify lại**.
3. Thiếu label/aria cho input roster search và toàn bộ form luyện tập nhiều trường — mới phát hiện.
4. **Điểm sáng: `RiskCaseDrawer.jsx` là modal/drawer mẫu mực nhất dự án về accessibility.**
5. Toàn bộ data khu vực Giảng viên là DB thật, ownership fail-closed đúng — không phát hiện lỗ hổng bảo mật mới.

---

## C. Khu vực Admin (Phòng Đào tạo)

| Tab | Data thật/mock | Tính năng chưa nối thật | Vấn đề UX | Vấn đề Accessibility/SEO | Mức độ |
|---|---|---|---|---|---|
| Curriculum | Thật, đọc trực tiếp file syllabus | Chưa có upload file thật (đã biết) | Xoá môn: 2 nút inline nhỏ cạnh nhau, dễ bấm nhầm | h1 tĩnh không đổi khi chuyển tab; tab-bar không có ARIA tab semantics; bảng thiếu `scope="col"` | **Cao** (ảnh hưởng toàn bộ 7 tab) |
| Người dùng/Lời mời | Thật, org-scoping + self-lock | Lời mời giảng viên chưa có bước chọn lớp gán (đã biết) | Khoá/thu hồi đều có confirm — tốt | Modal đầy đủ ARIA, bảng thiếu `scope="col"` | Trung bình |
| Analytics | Thật, DB-backed, verify trực tiếp service | — | — | `h2 sr-only` bù heading tốt; biểu đồ không có bảng số liệu thay thế | Thấp |
| Chính sách AI | Thật, publish/rollback đúng thiết kế an toàn | Guardrail toggle không nhận `reason` (giới hạn API đã biết) | **"Restore defaults" của Guardrail không có confirm** dù là hành động phá huỷ | Validation message không gắn `aria-describedby` với input sai | Trung bình |
| Audit log | Thật | — | Chỉ đọc, không có hành động nguy hiểm | Input filter có `sr-only label` đúng chuẩn; bảng thiếu `scope="col"` | Thấp |
| Cấu hình | Thật | — | Toggle demo mode/auto-alert không confirm dù ảnh hưởng toàn hệ thống | Switch ARIA chuẩn | Thấp |
| Học kỳ & Lịch thi | Thật | UI không cảnh báo tác động ghi đè 2 chiều tới SV trước khi lưu | **Xoá lịch thi không có confirm** — bất nhất với mọi hành động xoá khác trong Admin | Bảng thiếu `scope="col"` | **Cao** |

**Top phát hiện:**
1. **h1 tĩnh không đổi khi chuyển tab + tab-bar thiếu ARIA tab semantics** — ảnh hưởng toàn bộ 7 khu vực, chưa từng ghi nhận.
2. **Xoá lịch thi không confirm** — bất nhất, ảnh hưởng dây chuyền tới task tự sinh của SV.
3. Lưu học kỳ mới không cảnh báo ghi đè lựa chọn SV — khác chuẩn "preview bắt buộc" đã áp dụng đúng ở Risk Policy.
4. **0 occurrence `scope="col"` toàn bộ khu vực Admin** — pattern lặp lại, dễ sửa hàng loạt.
5. "Restore defaults" Guardrail thiếu confirm — duy nhất trong tab Chính sách AI không có xác nhận.

---

## D. Mock LMS + Trang công khai/dùng chung

### D.1 Mock LMS (`mock-lms/`)

| Màn hình | Data thật/mock | Vấn đề UX | Vấn đề Accessibility/SEO | Mức độ |
|---|---|---|---|---|
| `/courses` danh sách môn | 36 môn thật (catalog thật) | Không tìm kiếm/lọc — chấp nhận được, app phụ trợ nhỏ | h1 không mô tả nội dung trang cụ thể; thiếu `<caption>` bảng | Thấp |
| `/courses/<code>` + form sửa deadline | Course thật; 144 assignment **sinh giả có chủ đích** (xác nhận: syllabus gốc không có due-date có cấu trúc) | **Form sửa deadline không confirm, không preview diff, không validate range** — 1 click sai là mất, không undo | Input date thiếu `<label>` riêng từng dòng | Trung bình |
| HTTP Basic Auth | — | — | Xác nhận đúng cả 3 route (list/detail/update) đều có `Depends(require_web_admin)` | Đã đóng |
| Banner "LMS mô phỏng" | — | Hiện đúng, mọi trang, không điều kiện | Contrast tốt (~7:1) | Đã đóng |
| Theme | — | — | Chỉ 1 theme sáng — chấp nhận được (app phụ trợ, ngoài phạm vi "2 theme" bắt buộc của Cursus chính) | Thấp |

### D.2 Public/Auth/Shared (`frontend/src`)

| Màn hình | Data thật/mock | Vấn đề UX | Vấn đề Accessibility/SEO | Mức độ |
|---|---|---|---|---|
| Trang chủ | Chat demo FAQ 5 câu, có nhãn rõ | — | 1 h1, skip-link, i18n 689/689 dòng khớp | Thấp |
| Đăng nhập/Quên MK/Xác thực email | Thật | — | `AuthLayout` chuẩn hoá 1 h1 sr-only mọi trang auth | Thấp |
| **Hoàn tất hồ sơ (`OnboardingScreen.jsx`)** | Form đầy đủ nhưng **KHÔNG BAO GIỜ hiển thị** — xác nhận lại: `setUser` chỉ xuất hiện 1 lần (khai báo), `App.jsx:609` hardcode `onboarded: true` | Bug đã biết, quyết định cũ "không sửa trước deadline" vẫn hợp lý | Không áp dụng được (không ai thấy UI) | Nghiêm trọng (đã biết, không phải mới) |
| Chấp nhận lời mời/Yêu cầu quyền truy cập/Chọn vai trò demo/404/403 | Thật/demo rõ nhãn | — | Mỗi trang 1 h1 riêng | Thấp |
| Khung chung (Sidebar/Topbar) | — | Ô tìm kiếm Topbar disabled vô điều kiện, không nhãn "sắp ra mắt" (đã biết) | Landmark đúng chuẩn (`aside`/`nav`/`header`/`main`) | Thấp |
| `CuriChatLauncher.jsx` | Public: FAQ script; `/student/*`: `/qa` thật | **Thiếu đóng bằng click-ra-ngoài cho panel chat chính** (ESC hoạt động đúng cả 2 cấp) | `aria-label`/`aria-expanded`/`aria-controls` đầy đủ trên nút mở/đóng | Trung bình |
| Design token (`index.css`) | — | — | Light+dark đều định nghĩa đầy đủ; lỗi contrast cũ đã vá (18/08) | Đã đóng |

**Top phát hiện D:**
1. Bug `OnboardingScreen.jsx` xác nhận còn tồn tại, không có gì mới — quyết định cũ hợp lý.
2. **Mock LMS: form sửa deadline thiếu confirm/preview** — rủi ro thật vì `mock_lms_sync_service.py` dùng chính giá trị này làm nguồn ưu tiên cao nhất (source precedence #1); 1 click sai lệch dữ liệu "sổ cái" mà Cursus tin tưởng.
3. `CuriChatLauncher.jsx` thiếu đóng bằng click-ra-ngoài cho panel chính (gap nhỏ so với chat-widget chuẩn).
4. HTTP Basic Auth trên Mock LMS xác nhận đúng, không có route nào lọt qua.
5. Không phát hiện vấn đề mới nghiêm trọng nào ngoài các mục đã biết trong `PROJECT_CONTEXT.md` — landmark/heading/i18n đạt yêu cầu toàn bộ khu vực này.

---

## Verify sống bổ sung (backend tạm SQLite port 8020, không đụng Supabase)

- Schema tạo thành công qua `Base.metadata.create_all` trên DB SQLite mới hoàn toàn (`data/audit_check.db`).
- `provision_organization.py cursus-demo ... sandbox` chạy thành công, tạo đủ 4 tài khoản demo (Admin/Student/Instructor/Admin phụ).
- `POST /auth/demo-session {"role":"student"}` trả JWT thật + user/session thật.
- `GET /student/demo/state` trả dữ liệu thật (assignment SSA101, deliverables có `provenance` gắn nhãn "Demo data" rõ ràng — đúng nguyên tắc không giấu nguồn mô phỏng).
- Xác nhận: cơ chế tự-provision demo data hoạt động đúng như tài liệu mô tả (không cần seed script riêng).
