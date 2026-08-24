# AUDIT 0 — Hiện trạng toàn bộ màn hình/chức năng (Giai đoạn 0)

**Ngày:** 22/08/2026. **Phạm vi:** đối chiếu toàn bộ mục 6 (trang/chức năng theo vai trò), mục 13-14 (business rules), mục 16 (data contract) của `docs/PROJECT_CONTEXT.md` với code thật (`src/`, `frontend/src/`) và app đang chạy thật (backend `:8000`, frontend `:5173`).

**Phương pháp:** đọc trực tiếp component/route + đối chiếu 7 tiêu chí UI/UX chuẩn dưới đây cho từng màn hình; phần cần khảo sát rộng được giao cho 4 agent song song (Public+Shell, Student Reflect/Settings/Companion, Lecturer Dashboard phần còn lại, cụm Semester/Practice/Companion chưa tài liệu hoá); phần đã có bằng chứng dày đặc từ trước (Admin, Mock LMS, Student Tổng quan, phần lõi Lecturer Dashboard) viết trực tiếp từ evidence đã verify + spot-check bổ sung tối nay.

**7 tiêu chí UI/UX chuẩn (áp cho mọi màn hình):** (1) heading hierarchy đúng thứ bậc · (2) typography scale nhất quán · (3) tương phản WCAG AA cả 2 theme · (4) responsive thật 375px/tablet/desktop · (5) đủ 3 trạng thái loading/error/empty · (6) dịch đủ Việt/Anh (không hardcode) · (7) spacing nhất quán với `index.css`.

**Chú thích ký hiệu:** ✅ ĐÃ ĐÚNG CHUẨN · ⚠️ CÒN THIẾU GÌ CỤ THỂ · 🚨 GIẢ VỜ CÓ (trông như xong nhưng không thật).

---

## 0. Phát hiện nổi bật nhất — đọc trước

Trước khi vào từng màn hình: mục 6 hiện tại của `PROJECT_CONTEXT.md` (Student 3 trang, Lecturer 1 trang, Admin 6 nhóm chức năng) **không phản ánh đủ số màn hình thật sự tồn tại trong code**. Đối chiếu router thật (`frontend/src/App.jsx`) + điều tra sâu (mục 7) phát hiện thêm — **đã xác minh dứt khoát, không còn nghi vấn:**

- **Student** có thêm 6 route chưa tài liệu hoá ở mục 6.3, nhưng KHÔNG cùng một loại:
  - `planner` (`StudentPlanner`), `practice` (`StudentPractice`), `companion` (`StudentCompanionPage`) — **có link Sidebar thật**, chỉ là thiếu tài liệu, không mồ côi.
  - `semester-setup` (`SemesterSetupWizard`), `lecture-plan` (`LecturePlanPanel`) — **mồ côi thật sự**: 0 link Sidebar/Topbar nào trỏ tới, chỉ vào được bằng gõ thẳng URL hoặc qua 1 link nội bộ giữa 2 trang này với nhau. Code tự thừa nhận điều này trong comment (`SemesterSetupWizard.jsx:42-44`, `LecturePlanPanel.jsx:13-16`).
- **Lecturer** có thêm 2 tab chưa tài liệu hoá trong Bảng điều khiển, **không mồ côi** (bấm được thật từ `InstructorHome.jsx:148-165`): `InstructorPracticeQueuePanel.jsx` (hàng đợi duyệt bộ luyện tập AI sinh), `InstructorClassActivityPanel.jsx` (nhật ký buổi học).
- **Admin** có thêm 1 tab chưa tài liệu hoá, không mồ côi: `AdminAcademicPanel.jsx` (tab `academic` — "Học kỳ hiện hành" + "Lịch thi theo môn"); cộng 1 mục đã liệt kê trong mục 6.5 ("Cấu hình") nhưng **hoàn toàn chưa có UI** dù backend đã xong (xem mục 4.6).

`docs/PROJECT_CONTEXT.md` mục 23 đã ghi nhận từ 21/08 rằng cụm "Semester setup + Timetable + Practice Sets" (~5100 dòng, từ code đồng đội tích hợp vào) **chưa được kết luận, cố ý dừng điều tra do hết thời gian**, kèm quyết định tường minh: *"nếu audit màn hình (mục 6) phát hiện gap cụ thể ở khu vực semester/timetable/practice, quay lại nhóm này trước khi viết mới từ đầu."* Audit này chính là lần phát hiện đó — **câu trả lời dứt khoát ở mục 7**: toàn bộ cụm dùng **dữ liệu thật 100%** (không fixture/hardcode), là 1 hệ thống Plan **song song thật sự** với Gate2Demo (dùng chung bảng `WeeklyPlan`/`DailyPlan`/`ScheduleBlock`/`StudyTask`, phân biệt bằng tag `source="lecture_plan"`), có cơ chế chống đụng độ THẬT nhưng **dựa trên magic string lặp lại ở 5 nơi khác nhau, không có hằng số dùng chung, và đụng độ được xử lý ÂM THẦM** (Gate2 plan luôn thắng, sinh viên không được báo lecture-plan của mình vừa bị đè). Đây là **quyết định kiến trúc cần escalate** (xem mục 7.6), không phải chỉ thiếu tài liệu.

**Vì sao phát hiện này quan trọng hơn phần lớn các mục ⚠️ khác trong file:** cụm tính năng này thật sự hoạt động, dữ liệu thật, có giá trị — đây là phần lớn phạm vi "Nâng cao" (mục 2.4, timetable/semester) đã bị bỏ sót hoàn toàn khỏi mọi báo cáo/thuyết trình cho tới nay, ảnh hưởng trực tiếp tới điểm Sản phẩm/Kinh doanh (mục 10) — nhưng đi kèm 1 rủi ro dữ liệu-im-lặng cùng họ với các bug "silent fallback" đã gặp nhiều lần trong dự án.

### 0.1. Phát hiện nghiêm trọng thứ hai — "Cursus Assistant" (mục 6.2) thực chất là 3 hệ thống khác nhau, và bản "nổi trên mọi trang" là kịch bản giả

Mục 6.2 mô tả: *"khung chat nổi hỏi trợ lý Cursus Assistant bất cứ lúc nào (luôn trả lời kèm trích nguồn, không tự làm bài hộ)"*. Đối chiếu code thật (Agent audit Student, độc lập xác nhận lại bằng cách đọc trực tiếp cả 3 file) cho thấy có **3 component hoàn toàn tách biệt**, không cái nào khớp đúng mô tả:

1. **`CuriChatLauncher.jsx`** — component "nổi" DUY NHẤT thật sự (position fixed). Nhưng: (a) tự nhận trong comment ngay trong code (dòng 283-286) là *"a scripted FAQ menu wearing chat clothing, not a real LLM backend"* — 5 câu trả lời cứng, độ trễ "đang suy nghĩ" là `setTimeout` giả, "trích dẫn" chỉ là nhãn text tĩnh (vd `"Cursus Core Pillars"`), không phải link/nguồn thật; (b) chỉ hiện trên **6 route công khai** (`/`, `/login`, `/accept-invite`, `/request-access`, `/demo/select-role`, `/forgot-password`) — comment dòng 14-17 xác nhận chủ đích: *"Dashboards get no floating launcher yet."* **Kết luận: sau khi đăng nhập, không có bong bóng chat nổi nào trên bất kỳ trang `/student/*` nào cả** — trực tiếp trái với câu "nổi trên mọi trang" của spec.
2. **`CuriContextPanel.jsx`** — bản gọi RAG/backend thật (trích dẫn thật, guardrail Socratic thật), nhưng chỉ **nhúng tĩnh** trong 1 section của trang Tổng quan, không nổi, không xuất hiện ở Phản tư/Cài đặt/Luyện tập/Planner. Phiên chat cũng không lưu — mất khi rời trang.
3. **`CourseCompanionChat.jsx`** (`/student/companion`) — bản đầy đủ nhất (chọn môn động, đa thread có lưu trữ thật), nhưng lại là 1 TRANG riêng, không phải widget nổi.

**Vì sao đây là "GIẢ VỜ CÓ" điển hình nhất của toàn bộ audit:** đúng thứ trông "hoàn thiện nhất" (nổi mọi lúc, có mascot, có hiệu ứng gõ chữ) lại là thứ ít thật nhất (kịch bản cứng, không LLM, không trích dẫn thật); còn 2 bản có backend/trích dẫn thật thì người dùng phải tự tìm đúng ngữ cảnh (đang ở Tổng quan, hoặc biết vào `/student/companion`) mới thấy. Xem đầy đủ bằng chứng file:line ở mục 2.3.

### 0.2. Phát hiện nghiêm trọng nhất của TOÀN BỘ audit — biểu đồ tiến độ lớp của Giảng viên là số liệu bịa cứng, tạo cảnh báo sai vĩnh viễn

**File:** `frontend/src/components/instructor/InstructorHome.jsx:12` (`DASH_DATA.class_avg = [0.9, 0.79, 0.73, 0.70]`), dùng ở dòng 29-66 (component `BarChart`) và 179-186 (nơi gọi).

Đây không phải "chưa đủ dữ liệu thật" — đây là **1 mảng 4 số hardcode trong source, không hề đọc từ `classInfo`/API**. Backend (`src/api/instructor.py:361-381`) xác nhận **thậm chí chưa có trường trả về theo tuần** — chỉ có `weeklyCompletionRate` là 1 con số trung bình duy nhất, không phải mảng. Hệ quả trực tiếp: điều kiện cảnh báo "xu hướng giảm" (`InstructorHome.jsx:58`: `data[last] < data[0]`) **luôn luôn đúng** với mảng `[0.9, 0.79, 0.73, 0.70]` — nghĩa là **mọi giảng viên, mọi lớp, mọi thời điểm đăng nhập đều thấy banner cảnh báo "lớp đang giảm tiến độ"**, bất kể lớp đó thực tế đang tiến bộ tốt hay không.

**Vì sao đây được xếp là phát hiện nghiêm trọng nhất, hơn cả mục 0.1:** mục 6.4 mô tả đây là 1 trong 4 khối dữ liệu cốt lõi của bảng điều khiển giảng viên ("biểu đồ... tự cảnh báo nếu có xu hướng giảm"), và mục 19.1 (kịch bản demo 6 phút) dùng chính bảng điều khiển này làm cao trào phần "Lecturer HITL". Nếu giám khảo hỏi "cảnh báo xu hướng giảm này tính từ đâu", câu trả lời trung thực hiện tại là "không tính từ đâu cả, luôn hiện". Khác các phát hiện "thiếu tính năng" khác trong audit này, đây là trường hợp **activelly hiển thị SAI cho mọi người dùng**, không chỉ là thiếu — đúng định nghĩa "GIẢ VỜ CÓ" ở mức nghiêm trọng nhất.

Cùng file còn 1 hiện tượng cùng họ (mức độ nhẹ hơn): `classSize` mặc định về `DASH_DATA.class_size = 12` (dòng 11, 115) khi đang tải hoặc lỗi API — hiện thị y hệt định dạng số thật, không có skeleton, giảng viên không thể phân biệt.

### 0.3. Xác nhận thêm 2 phát hiện "GIẢ VỜ CÓ" ở mảng công khai/xác thực (Agent Public+Shell)

- **"Hoàn tất hồ sơ" (mục 6.1) — form thật 100% không thể hiển thị cho bất kỳ ai:** `OnboardingScreen.jsx:20` khai báo `const [user, setUser] = useState(null)` nhưng `setUser` **không bao giờ được gọi lại** ở nơi nào khác trong file — nên `if (!user) return <Loading>` (dòng 161-168) luôn đúng, form thu thập họ tên/ngành học/MSSV (dòng 170-296) **là dead code không ai từng thấy**. Đồng thời route `/onboarding` gần như không thể/không cần tới được: cờ gate `user.onboarded` bị hardcode `true` cho mọi session thật ở `App.jsx:588` (backend không có field này). Và với người đăng nhập Google, `runGoogleSync()` tự động điều hướng thẳng sang dashboard sau 1 giây, bỏ qua bước này hoàn toàn. **Kết luận: yêu cầu "thu thập họ tên/ngành học/MSSV sau lần đăng nhập Google đầu tiên" của spec 6.1 không xảy ra ở bất kỳ đường nào trong hệ thống hiện tại** — không phải vì thiếu, mà vì code đã viết xong nhưng bị ngắt kết nối khỏi luồng thật.
- **Đăng nhập Google — nút bấm luôn báo lỗi, không phải thỉnh thoảng lỗi:** `LoginScreen.jsx:118-125` (`handleGoogleLogin`) hiện lỗi tĩnh "tạm thời bị vô hiệu hoá" **vô điều kiện**, mọi lần bấm, không có nhánh thành công nào; `supabase` import ở đầu file không được dùng trong handler. Lưu ý: mục 19.3 (thứ tự cắt giảm khi trễ giờ demo) đã liệt "Login Google thật" là mục có thể cắt — cho thấy team có thể đã biết đường này không ổn định, nhưng chưa có tài liệu nào xác nhận rõ nó là **vô hiệu hoá hoàn toàn, 100% số lần**, không phải "chưa ổn định".

---

## 1. Các trang công khai (mục 6.1) + Khung chung (mục 6.2)

### 1.1. Trang chủ (Landing)

✅ **ĐÃ ĐÚNG CHUẨN:** heading hierarchy sạch toàn trang (1 h1 → h2 mỗi section → h3 card con); skip-link + `role="banner"` + `main` có `tabIndex`; tương phản 2 theme đã được audit kỹ trước đây, có ghi chú tỉ lệ đo được ngay trong code; responsive thật (mobile bỏ hẳn video, dùng ảnh tĩnh; accordion riêng cho mobile thay vì thu nhỏ tab desktop); sandbox demo tự dán nhãn rõ dữ liệu minh hoạ; backend xác nhận chặn tự đăng ký đúng như FAQ landing page nói.
⚠️ **CÒN THIẾU:** CTA phụ "yêu cầu quyền truy cập" (`/request-access`) bị chôn thành 1 link chữ nhỏ ở copyright bar cuối trang — cả 2 vị trí CTA chính (Hero, Final CTA) đều dùng CTA phụ là "xem cách hoạt động" (anchor scroll) thay vì dẫn tới `/request-access` như spec 6.1 mô tả; type-scale bị phân mảnh (hơn chục class `!important` cỡ chữ riêng lẻ ngoài 2 scale chính thức).
🚨 **GIẢ VỜ CÓ:** Không phát hiện.

### 1.2. Đăng nhập, Quên mật khẩu, Đặt lại mật khẩu, Xác thực email, Chấp nhận lời mời, Yêu cầu quyền truy cập (đều qua `AuthLayout.jsx`)

⚠️ **CÒN THIẾU — lỗi hệ thống dùng chung, ảnh hưởng ĐỒNG THỜI ít nhất 5 màn hình qua 1 layout chung:** `AuthLayout.jsx` bọc h1 trong `hidden lg:flex` (dòng 58-59) → **dưới 1024px, không màn hình nào trong nhóm này có h1 nào cả** (kể cả cho screen reader). Đồng thời `ForgotPasswordScreen.jsx` (dòng 82-84) và `ResetPasswordScreen.jsx` (dòng 136) mỗi file tự thêm 1 h1 RIÊNG, gây ra **2 thẻ h1 cùng lúc ở desktop** (≥1024px) cho 2 màn này. Đây là lỗi tiêu chí 1 rộng nhất tìm được sau sidebar (mục 2.5) — 1 chỗ sửa ở `AuthLayout` (đổi hidden→ẩn bằng cách khác không dùng `display:none` cho riêng h1, hoặc bỏ h1 trùng ở 2 file con) khắc phục được cả nhóm.
- Google login luôn báo lỗi 100% số lần (xem mục 0.3) — nằm ở `LoginScreen.jsx`.
- `ForgotPasswordScreen.jsx`: placeholder email hardcode tiếng Việt (`"ten.msv@truong.edu.vn"`) không đổi theo `lang`, trong khi `LoginScreen` liền kề đã dùng đúng key dịch.
- `ResetPasswordScreen.jsx`: placeholder trùng label ("Xác nhận mật khẩu"), không hướng dẫn thêm.
- `EmailVerificationScreen.jsx`: chuỗi fallback `'đang tải...'` hardcode tiếng Việt khi chưa có email để hiện.
- `AcceptInviteScreen.jsx`: màu đo độ mạnh mật khẩu (`S_COLORS`) là 2 mã hex rời, chưa qua audit tương phản như phần còn lại của `index.css`; có 1 bộ `ROLE_LABEL_VI/EN` viết tay riêng, trùng lặp với `roles.*` trong locale (cùng họ vấn đề với mục 2.5 — xem gốc rễ `constants/roles.js` ở mục 1.4).
- `RequestAccessScreen.jsx`: nút submit không đổi nội dung/spinner khi đang gửi (mọi form khác trong nhóm này đều có).

✅ **ĐÃ ĐÚNG CHUẨN (đáng ghi nhận):** `AcceptInviteScreen.jsx` có xử lý trạng thái mẫu mực nhất cả audit (4 trạng thái no-token/loading/invalid/valid, tách riêng submitting/success/lỗi field); tất cả 6 màn đều đủ loading/error/success cơ bản; `ResetPasswordScreen` có hẳn trạng thái riêng cho token hết hạn.
🚨 **GIẢ VỜ CÓ:** Google login (mục 0.3).

### 1.3. Chọn vai trò demo, Trang lỗi 404, Trang "Không có quyền truy cập"

✅ **ĐÃ ĐÚNG CHUẨN:** "Chọn vai trò demo" khớp 100% với spec (đã xác nhận cả code backend: không tạo `User` mới, chỉ tra cứu 1 trong 3 email demo cố định, bắt buộc đúng tổ chức demo). **404 (`NotFoundPage.jsx`) là màn hình chuẩn nhất toàn bộ audit** — 1 h1 luôn hiển thị mọi viewport, dùng đúng hệ thống dịch `t()`, không hardcode gì — nên dùng làm mẫu tham chiếu khi sửa các màn khác.
⚠️ **CÒN THIẾU:**
- "Chọn vai trò demo": thanh trên cùng không có `flex-wrap`, ước tính có nguy cơ tràn ngang ở đúng mốc 375px (cần verify trực quan).
- "Không có quyền truy cập": **hoàn toàn không có namespace dịch riêng** (`unauthorized.*` không tồn tại trong locale) — mọi text hardcode ternary, trái ngược hẳn 404 liền kề; bản tiếng Anh hiện tên role thô ("student") thay vì nhãn đẹp vì `ROLE_LABEL` chỉ có tiếng Việt (cùng gốc rễ mục 1.4/2.5).
🚨 **GIẢ VỜ CÓ:** Không phát hiện.

### 1.4. Khung chung sau đăng nhập (mục 6.2) — xác nhận độc lập lần thứ 2 (đã được Agent Student xác nhận lần 1, xem mục 2.5), cộng thêm phát hiện mới

✅ **ĐÃ ĐÚNG CHUẨN:** Sidebar đổi đúng nav theo vai trò + `aria-current`; Topbar đủ tìm kiếm/thông báo/ngôn ngữ/theme/đăng xuất; `NotificationsBell` phân biệt đọc/chưa đọc, đóng bằng Escape/click-outside, có empty state.

🚨 **GIẢ VỜ CÓ (xác nhận từ nguồn độc lập thứ 2 — mức tin cậy cao):**
- **Sidebar hardcode tiếng Việt hoàn toàn**, đúng như mục 2.5 đã nêu — Agent này bổ sung thêm: `"KHÔNG GIAN LÀM VIỆC"` (`App.jsx:158-160`) hardcode dù key dịch `common.workspaceLabel` (bản "WORKSPACE") **đã tồn tại sẵn nhưng không được gọi**; nút chuyển theme chỉ đổi nhãn theo `theme`, không theo `lang` (luôn tiếng Việt dù đang ở English); 2 `aria-label` khác cũng hardcode tiếng Việt.
- **Gốc rễ xác định chính xác:** `frontend/src/constants/roles.js:1-7` — `ROLE_LABEL`/`ROLE_DESC` **chỉ có bản tiếng Việt**, không có bản tiếng Anh nào cả; `App.jsx:146,149` dùng thẳng 2 object này cho hộp vai trò trong Sidebar. Đây là gap đã được ghi nhận từ trước (biết là vấn đề thật, nay có bằng chứng file:line đầy đủ và xác nhận phạm vi ảnh hưởng rộng hơn tưởng — lan sang cả `UnauthorizedPage` và `AcceptInviteScreen`, xem mục 1.2/1.3).
- **Banner "đang ở chế độ demo" (mục 6.2) hoàn toàn không tồn tại** — chỉ có 1 dòng comment rỗng `/* ── DEMO MODE BANNER ── */` (`App.jsx:419`), không JSX nào theo sau. Đã grep toàn bộ `frontend/src`, không tìm thấy component nào khác đảm nhiệm việc này.
- **Khung chat nổi biến mất sau đăng nhập** — xác nhận lần 2, đúng mục 0.1 (`CuriChatLauncher.jsx` chỉ hiện trên 6 route công khai, comment code tự thừa nhận "Dashboards get no floating launcher yet").
- Ô tìm kiếm ở Topbar `disabled` vô điều kiện, không có chỉ báo "sắp ra mắt" — trông như bị lỗi hơn là tính năng chưa làm.

**Route/tính năng có trong code nhưng KHÔNG có trong spec 6.1-6.2:** `/privacy`, `/terms` (trang pháp lý, link từ footer); cụm API MFA đầy đủ ở backend (`/auth/mfa/status`, `/mfa/totp/setup|enable`, `/mfa/recovery-codes/regenerate`, `/mfa/disable`) + quản lý phiên (`/auth/sessions`, `/auth/logout-all`, `src/api/auth.py:518-660,922-987`) — Agent Student đã audit `SettingsScreen.jsx` chi tiết và **không thấy** UI nào cho các API này, nên đây nhiều khả năng là "backend xong, frontend chưa" cùng họ với mục 4.6, cần xác nhận thêm nếu có thời gian; đổi email tại chỗ (`/auth/email/change`); phím tắt Alt+C bật/tắt mascot.

---

## 2. Khu vực Sinh viên (mục 6.3)

### 2.1. Trang Tổng quan (đã audit rất kỹ trước đây — tóm tắt lại, không audit lại từ đầu)

**File:** `frontend/src/components/student/StudentHome.jsx` (qua `Gate2Context.jsx`), backend `GET /student/demo/state` (`src/api/student.py:552-645`).

✅ **ĐÃ ĐÚNG CHUẨN:**
- Đủ các khối theo spec: lời chào theo buổi, "việc nên làm tiếp theo" kèm lý do, 4 điểm số liệu nhanh, task hôm nay (đánh dấu xong/xoá/thêm), hạn chót sắp tới, vòng Plan→Do→Reflect, gợi ý cải thiện, tiến độ từng môn.
- Dữ liệu task/tiến độ là **DB thật đa môn** (4 môn: SSA101/PRF192/CEA201/CSI106, `Enrollment`/`CourseSection`/`StudyTask` thật) — không phải JSON bịa trong frontend (verify bằng screenshot Playwright 21/08).
- Cảnh báo "MÔ PHỎNG" khi hỏi Cursus Assistant về CEA201/PRF192 (2 môn chỉ có nội dung bịa) — verify thật qua `/student/companion` (dùng chung `QaAnswerService`).

⚠️ **CÒN THIẾU GÌ CỤ THỂ:**
- Tập hợp "4 môn" là fixture **cố định giống nhau cho mọi sinh viên demo**, chưa phải "mỗi sinh viên 1 bộ môn theo enrollment thật của riêng họ" — tiêu chí (6)/business-flow: dữ liệu đã là thật nhưng chưa cá nhân hoá đúng nghĩa.
- Field `"course"` cấp cao nhất trong response (`student.py:610-616`) vẫn ghim cứng `gate2_demo.SSA101_CODE`, chưa đổi theo môn của task đang xem.
- Widget "Hỏi Trợ lý Cursus" nổi trên trang này (`CuriContextPanel.jsx`) vẫn ghim cứng `subjectCode='SSA101'` — **cần Agent 2 xác nhận lại trạng thái mới nhất** (xem mục 2.3 dưới).
- 2 endpoint cạnh tranh vẫn tồn tại: `GET /student/dashboard` (generic, đọc đúng enrollment thật, đa môn tự động) là **dead code phía frontend** (`getStudentDashboard()` không được gọi ở đâu) — quyết định giữ nguyên đã chốt 20/08, ghi lại ở đây để không lặp lại điều tra.

🚨 **GIẢ VỜ CÓ — phát hiện mới tối nay, đối chiếu trực diện mục 13.2, chưa từng bị bắt lỗi trước đây:**
- Mục 13.2 chốt rõ: bấm "Hoàn thành" phải hiện **modal hỏi "Bạn học khoảng bao lâu?"** (mặc định = estimate, sinh viên tự chỉnh tay), để `actual_minutes` phản ánh đúng thời gian thật — lý do nêu rõ trong chính tài liệu: tránh timer tự động sai lệch, nhưng KHÔNG được phép mặc nhiên coi actual = estimate.
- Code thật (`frontend/src/components/student/StudentHome.jsx:467-468`): `const handleComplete = (task) => run(() => completeTask(task.id, task.estimatedMinutes));` — gọi thẳng `completeTask` với **`task.estimatedMinutes`**, không hề có modal, không hỏi gì cả. Xác nhận `run()` (dòng 458-465) chỉ là wrapper try/catch cho loading state, không chứa modal nào.
- **Hậu quả cụ thể:** `actualMinutes` sau khi hoàn thành **luôn luôn bằng hệt** `estimatedMinutes` cho mọi task, với mọi sinh viên, mọi lúc — vì giá trị được gán cứng tại lúc gọi, không phải do sinh viên nhập. Toàn bộ logic so sánh "thực tế vs ước tính" đang hiển thị ở 2 nơi (`StudentHome.jsx:248`: `task.actualMinutes > task.estimatedMinutes ? 'text-warning' : 'text-success'`; `StudentReflection.jsx:55`: cùng phép so sánh) **không thể nào ra kết quả khác "đúng như ước tính" (màu xanh success)** — đây là dữ liệu **trông như** self-reported thật (có màu sắc cảnh báo/thành công như thể phản ánh hành vi thật) nhưng về mặt toán học **không thể** phản ánh gì khác ngoài việc lặp lại số đã ước tính từ trước.
- **Vì sao đây đúng lớp "GIẢ VỜ CÓ" nghiêm trọng:** dữ liệu `actual_minutes` này còn được dùng làm input cho Reflect (`facts.actual_minutes`, mục 16.2) — nếu tính risk score hay reflection summary có tham chiếu tới độ lệch actual/estimate trong tương lai, toàn bộ tín hiệu đó sẽ vô nghĩa vì không có phương sai thật nào được ghi nhận. Sinh viên học 3 tiếng cho task ước tính 30 phút vẫn được ghi nhận "đúng 30 phút, đúng kế hoạch."
- **Đối chiếu để thấy đây là thiếu sót cụ thể, không phải giới hạn kỹ thuật:** hành động "Dời" (defer) trên CÙNG màn hình này làm ĐÚNG mẫu — `DeferTaskDialog.jsx` (import ở dòng 22, dùng ở dòng 665) bắt buộc chọn `reasonCode` + nhập `note` trước khi gọi `deferTask(id, reasonCode, note)` (dòng 471). Team rõ ràng đã biết cách làm đúng pattern "dialog xác nhận trước khi ghi nhận hành động", chỉ đơn giản là chưa áp dụng lại đúng pattern đó cho nút "Hoàn thành" — sửa không khó, đây là việc thiếu sót cụ thể (concrete gap), không phải giới hạn kiến trúc.

### 2.2. Trang Phản tư (`StudentReflection.jsx`)

✅ **ĐÃ ĐÚNG CHUẨN:** heading hierarchy đúng (1 h1 → h2 con, không nhảy cấp); đủ loading/error(kèm Retry)/empty; responsive mobile-first (`grid-cols-2 sm:grid-cols-4`); dịch đủ VI/EN; gọi API thật (`getReflectionPreview`/`submitReflection`/`buildNextWeekPlan`), không phải dữ liệu tĩnh.

⚠️ **CÒN THIẾU GÌ CỤ THỂ:**
- **Typography scale hỗn loạn:** 9 giá trị pixel tuỳ ý khác nhau trong cùng 1 file (`text-[9px]`, `[10px]`, `[11px]`, `[12px]`, `[13px]`, `[14px]`, `[15px]`) — không có token `--text-*` nào trong `index.css` để đối chiếu.
- **Contrast dưới chuẩn AA ở theme sáng (định lượng được, không phải áng chừng):** `text-fg-muted` (`#64748b`) đặt trực tiếp trên `bg-surface-elevated` (`#F1EFEA`) tại các ô thống kê (dòng 78-81) = **4.14:1**, dưới ngưỡng AA 4.5:1. Cùng cặp token này trên nền trắng thuần đạt 4.76:1 (an toàn) — vấn đề chỉ phát sinh khi 2 token cụ thể này bị ghép với nhau, và cặp ghép này **lặp lại ở nhiều màn hình khác** (xem dưới).
- Locale key `reflection.*` trong `frontend/src/locales/en.js`/`vi.js` (dòng ~261-277) là **nội dung chết, lỗi thời** (nói "Week 4", "AI feedback" — không khớp UI thật) — 0 nơi trong code gọi các key này; nếu ai sửa file locale tưởng sẽ đổi được nội dung trang này thì sẽ không có tác dụng gì.

🚨 **GIẢ VỜ CÓ:** Không phát hiện.

### 2.2b. Trang Cài đặt (`frontend/src/components/shared/SettingsScreen.jsx`)

✅ **ĐÃ ĐÚNG CHUẨN:** đủ chức năng theo spec (hồ sơ, theme, ngôn ngữ, toggle Cursus Assistant nổi với đúng `role="switch"`+`aria-checked`, thông báo, đăng xuất); nút "Yêu cầu xoá dữ liệu" (thêm 22/08) có `window.confirm`, hiện rõ kết quả/lỗi, gọi API thật `deleteMyPersonalData()` — không phải nút trang trí; dịch đủ VI/EN, không có chuỗi hardcode một chiều.
⚠️ **CÒN THIẾU:** Không phát hiện gì đáng kể — đây là màn hình chất lượng tốt nhất trong nhóm được audit lần này.
🚨 **GIẢ VỜ CÓ:** Không phát hiện.

### 2.3. "Cursus Assistant" — 3 hiện thân riêng biệt, không component nào khớp đúng spec 6.2 (chi tiết đầy đủ của phát hiện mục 0.1)

**a) `frontend/src/components/shared/CuriChatLauncher.jsx` — widget nổi thật (duy nhất), nhưng nội dung là kịch bản cứng**
✅ ĐÃ ĐÚNG CHUẨN: responsive tốt nhất scope (bottom-sheet full-screen dưới breakpoint `sm`), focus trap + Escape + khôi phục focus đúng chuẩn accessibility.
⚠️ CÒN THIẾU: 3 chỗ `aria-label` hardcode 1 ngôn ngữ dù có `lang` trong scope — đáng chú ý nhất là **nút mascot chính** (dòng 508) chỉ có nhãn tiếng Việt cho screen reader dù UI đang ở chế độ English; panel chat không có heading ngữ nghĩa (`<span>` thay vì `<h2>`), không có `role="dialog"`.
🚨 GIẢ VỜ CÓ: **có, nghiêm trọng** — xem mục 0.1. Đây là widget "nổi" nhưng (1) không gọi backend nào, 5 câu trả lời cứng + trích dẫn là nhãn text tĩnh không phải nguồn thật, (2) chỉ hiện trên 6 route công khai, **biến mất hoàn toàn sau khi đăng nhập** (comment code tự thừa nhận "Dashboards get no floating launcher yet").

**b) `frontend/src/components/student/CuriContextPanel.jsx` — nhúng trong Tổng quan, backend RAG thật**
✅ ĐÃ ĐÚNG CHUẨN: trích dẫn thật qua `CitationChip`, badge minh bạch nguồn trả lời (tiền định vs LLM), guardrail Socratic thật (không làm hộ), đủ loading/error(giữ lại câu hỏi để thử lại)/empty(gợi ý mẫu).
⚠️ CÒN THIẾU: `subjectCode='SSA101'` (dòng 122) **vẫn còn trong source như default parameter**, nhưng nơi gọi duy nhất (`StudentHome.jsx:608`) đã sửa thành `course?.code ?? 'SSA101'` — tức **đã sửa một phần**: không còn ghim cứng vô điều kiện trong luồng dùng thật, chỉ còn là giá trị dự phòng im lặng khi thiếu `course` (nên hiện trạng thái rõ ràng hơn thay vì fallback âm thầm). Cùng vấn đề contrast 4.14:1 ở badge nguồn trả lời. Phiên chat không lưu (ephemeral, tự nhận trong docstring) — mất khi rời trang/reload.
🚨 GIẢ VỜ CÓ: không phát hiện ở phần lõi Q&A.

**c) `frontend/src/components/student/CourseCompanionChat.jsx` (route `/student/companion`, có link sidebar "Trợ lý theo môn") — đầy đủ nhất, nhưng là trang riêng chứ không phải widget nổi**
✅ ĐÃ ĐÚNG CHUẨN: chọn môn hoàn toàn động (không hardcode), đa thread lưu trữ thật (tạo/xem/xoá), badge minh bạch chế độ trả lời, đủ empty state, heading đúng thứ bậc.
⚠️ CÒN THIẾU: lỗi tải/gửi hiện text đỏ trần, không có nút Retry, không dùng component `ErrorState` chung (thiếu nhất quán với Reflect/Planner); layout 2 cột (danh sách thread `w-48` + khung chat) không có breakpoint thu gọn — nguy cơ chật ở 375px, đặc biệt khi header + dropdown chọn môn (`w-52` cố định) không `flex-wrap`.
🚨 GIẢ VỜ CÓ: không phát hiện — nối backend thật hoàn toàn.

**Khuyến nghị tổng hợp cho Giai đoạn sau:** đây là ứng viên hàng đầu cho Giai đoạn 1 (Research) + Giai đoạn 2 (Evaluation) — cần quyết định kiến trúc rõ ràng: hợp nhất 3 hiện thân thành 1 trải nghiệm nhất quán (ví dụ: widget nổi thật sự gọi `CuriContextPanel`/`CourseCompanionChat` pipeline thay vì kịch bản cứng, và làm nó xuất hiện trên mọi trang `/student/*` đúng như spec), hoặc sửa lại mục 6.2 cho khớp thực tế nếu quyết định giữ nguyên kiến trúc hiện tại. Đây KHÔNG phải việc chỉ code thêm vài dòng — ảnh hưởng trực tiếp tới câu trả lời demo "AI luôn trả lời kèm trích nguồn" (mục 19.1) nếu giám khảo tự thử bong bóng chat nổi trên dashboard thật.

### 2.4. Cụm route chưa tài liệu hoá (`planner`, `practice`, `semester-setup`, `lecture-plan`)

Đã điều tra kỹ bằng 2 nguồn độc lập (1 agent kiến trúc/data, 1 agent UI/UX) — kết quả hội tụ, xem đầy đủ ở **mục 7**. Tóm tắt nhanh riêng phần Student:
- `planner` (`StudentPlanner.jsx`) — **không thuộc cụm "lạ"**, đây chính là bước Plan của Gate2Demo tách route riêng, có link sidebar, chất lượng UI tốt (dùng đúng `ErrorState` chung, responsive tốt) — chỉ là thiếu tài liệu ở mục 6.3.
- `practice` (`StudentPractice.jsx`) — tính năng thật, hoàn chỉnh, có link sidebar "Luyện tập", nối backend+LLM thật, có UI duyệt phía giảng viên đi kèm — vắng mặt hoàn toàn khỏi mục 6.
- `semester-setup`/`lecture-plan` — **mồ côi thật sự** (0 link nav), nhưng chất lượng code/UI không hề dở dang — xem mục 7 để biết đầy đủ quan hệ dữ liệu với Gate2Demo và khuyến nghị escalate kiến trúc.

### 2.5. Phát hiện xuyên suốt mọi trang Student (khung chung, mục 6.2) — sidebar hardcode tiếng Việt hoàn toàn

🚨 **GIẢ VỜ CÓ — vi phạm tiêu chí 6 rộng nhất tìm được trong toàn bộ audit này:** toàn bộ nhãn điều hướng chính trong Sidebar (`frontend/src/App.jsx`) bị hardcode tiếng Việt, **không hề dùng biến `lang`** dù component có sẵn `lang` từ `useLanguage()` (dòng 86): "KHÔNG GIAN LÀM VIỆC" (159), "Tổng quan" (171), "Lập kế hoạch tuần" (181), "Kế hoạch hôm nay" (191), "Phản tư" (201), "Luyện tập" (211), "Trợ lý theo môn" (221), và `aria-label="Đóng menu"` (136). Nút gạt VI/EN nằm ngay trong sidebar đó (253-262) nhưng bấm sang English thì **toàn bộ menu điều hướng chính vẫn hiện tiếng Việt** — đây là hạng mục "chuyển ngôn ngữ" (bắt buộc theo thang điểm BTC, mục 9/10) bị lỗi ở đúng nơi dễ bị giám khảo nhìn thấy nhất (menu bên trái, luôn hiển thị). **Đã xác nhận độc lập lần 2 bởi Agent Public+Shell, cùng gốc rễ chính xác** (`constants/roles.js` chỉ có bản tiếng Việt) — xem đầy đủ ở mục 1.4, phạm vi ảnh hưởng lan rộng hơn ban đầu tưởng (cả `UnauthorizedPage`, `AcceptInviteScreen`, banner demo-mode không tồn tại, khung chat nổi biến mất sau đăng nhập).

---

## 3. Khu vực Giảng viên (mục 6.4)

**Phạm vi thật đã xác nhận:** route duy nhất `/instructor` (đúng "1 trang" như mục 6.4 mô tả), nhưng bên trong có **3 tab nội bộ**: Overview (`InstructorHome.jsx`) + "Nhật ký buổi học" (`InstructorClassActivityPanel.jsx`, không có trong spec) + "Duyệt luyện tập" (`InstructorPracticeQueuePanel.jsx`, không có trong spec) — cần cập nhật mục 6.4 để phản ánh đúng 3 tab này.

### 3.1. Header lớp + Class picker + 3 ô KPI (file: `InstructorHome.jsx`)

✅ **ĐÃ ĐÚNG CHUẨN:** h1 đúng cấp, badge "FERPA Compliant"; sĩ số nhúng đúng subtitle; grid 3 ô KPI an toàn tuyệt đối ở 375px (`grid-cols-1 md:grid-cols-3`); màu số liệu lớn đạt AA cho chữ lớn đậm (3.19-4.83:1, ngưỡng 3:1); dịch đủ qua `t()` cho 3 nhãn KPI; pattern chống tràn chữ tốt (`flex-1 min-w-0` + `shrink-0`) ở phần AlertCard — nên dùng làm mẫu tham chiếu nội bộ.

🚨 **GIẢ VỜ CÓ — xác nhận dứt khoát cả 2 câu hỏi mục 14.1 nêu ở bản audit trước, cộng 2 phát hiện mới nghiêm trọng hơn:**
- **Class picker HOÀN TOÀN KHÔNG TỒN TẠI** (0 kết quả grep `classPicker|assignedClasses|selectClass` toàn `frontend/src`), dù dữ liệu multi-class là thật (backend `_sections_for()` không giới hạn 1 section; `InstructorClassActivityPanel.jsx` tự dựng dropdown chọn môn riêng cho tab của nó, chứng minh multi-class có thật). Toàn bộ tab Overview gộp chung dữ liệu **tất cả** lớp giảng viên phụ trách, không có cách nào xem riêng "lớp đang xem" như spec yêu cầu.
- **Biểu đồ tiến độ theo tuần dùng dữ liệu bịa cứng, cảnh báo xu hướng giảm hiện vĩnh viễn cho mọi giảng viên** — xem chi tiết đầy đủ ở mục 0.2 (phát hiện nghiêm trọng nhất toàn bộ audit).
- **`classSize` rơi về số giả cứng `12`** khi đang tải/lỗi API (`DASH_DATA.class_size`, dòng 11,115), hiển thị y hệt định dạng số thật, không skeleton dù component `Skeleton.jsx` có sẵn trong app.
- Mục 14.1 "Outcome definition" (tooltip giải thích "nguy cơ" nghĩa là gì) và "Missingness" (trạng thái "chưa đủ dữ liệu" tách riêng khỏi "0-2 bình thường") — **xác nhận dứt khoát: cả hai đều KHÔNG tồn tại**, đã đọc kỹ toàn bộ logic hiển thị badge trong cả 4 file thuộc phạm vi Lecturer, không chỉ dựa vào từ khoá.

⚠️ **CÒN THIẾU thêm:** "FERPA Compliant" hardcode tiếng Anh không qua `t()`; header không có `flex-wrap`, khối tiêu đề thiếu `flex-1 min-w-0` — rủi ro lệch layout ở 375px với tiêu đề tiếng Việt dài (so sánh: `AlertCard` cùng file lại làm đúng pattern này — thiếu nhất quán nội bộ, không phải giới hạn kỹ thuật).

### 3.2. Danh sách sinh viên + tìm kiếm theo tên — 🚨 phát hiện "xác chết tính năng" rõ nhất toàn bộ audit

**Không tồn tại trong UI, dù đã được thiết kế xong rồi bỏ dở — bằng chứng rất mạnh, không phải suy đoán:**
- Backend đã xây đủ: `src/api/instructor.py:315-346` dựng `roster` gồm đúng field cần (`studentId`, `displayName`, `completionRate`, `score`, `severity`, `riskLevel`) và trả về trong response `/instructor/dashboard` (dòng 375) — nhưng `classInfo.roster` **không được đọc ở bất kỳ đâu** trong `InstructorHome.jsx` (0 match grep `roster` ngoài backend/test).
- Locale đã có sẵn nguyên bộ khoá dịch cho đúng tính năng này: `vi.js`/`en.js` dòng 285-290 — `studentListTitle`, `colName`, `colCourse`, `colProgress`, `colRisk`, `colAction`, `markIntervenedBtn` — **không key nào trong số này được `t()` gọi ở bất kỳ component nào** (đã grep toàn `frontend/src`).
- **Kết luận:** đây không phải "chưa làm" thông thường — đây là dấu vết của 1 tính năng ĐÃ được thiết kế đủ (backend + locale keys đặt tên chính xác khớp UI dự kiến) rồi bị gỡ bỏ hoặc bỏ dở giữa chừng ở đúng bước ráp UI cuối cùng. Ưu tiên cao cho Giai đoạn 3 (Plan) vì chi phí hoàn thiện thấp — phần khó (data + dịch) đã xong sẵn.

### 3.3. Danh sách cảnh báo sinh viên nguy cơ (thẻ), Hàng đợi duyệt guardrail — chất lượng UI (không audit lại phân quyền, đã đúng)

✅ **ĐÃ ĐÚNG CHUẨN:** mỗi thẻ cảnh báo nêu lý do + hành động cụ thể, bàn phím tiếp cận tốt (`role="button"`, `onKeyDown`); hàng đợi guardrail có 2 hành động rõ ràng, badge trạng thái đã xử lý phân biệt màu, câu hỏi hiển thị dạng monospace dễ đọc, có empty state đúng chuẩn khi trống thật.

⚠️ **CÒN THIẾU:**
- Thẻ cảnh báo: **hoàn toàn không có empty state** khi 0 alert (so sánh: khối Guardrail Queue ngay bên dưới CÙNG FILE lại có empty state đúng chuẩn — thiếu nhất quán cục bộ, không phải giới hạn kỹ thuật); badge "Đã can thiệp" (`badge-success`) ở light theme ≈3.60:1, dưới AA cho chữ nhỏ.
- Hàng đợi guardrail: thiếu hiển thị `blockReason` dù backend đã trả field này — giảng viên chỉ thấy câu hỏi bị chặn, không biết AI đánh giá lý do chặn là gì; không có nhãn lớp/môn trên từng item dù multi-class là thật — case của nhiều lớp bị trộn lẫn không phân biệt được.

🚨 **GIẢ VỜ CÓ:** hàng đợi guardrail hiện **"trống"** ngay khi trang vừa mount (do `loading` không được kiểm tra, `queue` mặc định là mảng rỗng) — **trước khi** dữ liệu thật kịp tải xong, tạo cảm giác sai "không có gì cần duyệt" trong khoảnh khắc đầu.

### 3.4. RiskCaseDrawer — chỉ audit UI/UX (chức năng/phân quyền đã verify đúng từ trước)

✅ **ĐÃ ĐÚNG CHUẨN:** loading/error(Retry)/empty đầy đủ và tinh tế nhất scope Lecturer; 100% qua `t()`, không hardcode; responsive an toàn (`w-full sm:w-[420px]`); focus trap/Escape/khoá scroll nền/trả focus — chất lượng a11y cao nhất scope.
⚠️ **CÒN THIẾU:** **Badge mức rủi ro (HIGH/MEDIUM/LOW) fail hoặc cận-fail WCAG AA ở theme sáng** (tính tay theo công thức WCAG chuẩn: danger 4.41:1 cận-fail, success 3.60:1 fail, warning 3.07:1 fail nặng nhất — cả 3 đều đạt tốt ở theme tối 4.6-7.7:1) — cùng họ token với badge "Đã can thiệp" ở mục 3.3; lỗi API hiển thị thẳng `err.message` tiếng Anh kỹ thuật, chưa qua bản dịch thân thiện.
🚨 **GIẢ VỜ CÓ:** Không phát hiện — đây là phần được xây kỹ nhất toàn bộ khu vực Lecturer.

### 3.5. 2 tab chưa tài liệu hoá — "Nhật ký buổi học", "Duyệt luyện tập"

✅ **ĐÃ ĐÚNG CHUẨN (cả 2 tab):** tính năng thật, dữ liệu thật (ghi nhận buổi học đã dạy/huỷ/dạy bù; duyệt bộ câu hỏi luyện tập AI sinh trước khi publish cho sinh viên), heading đúng cấp, có empty state cơ bản, grid responsive an toàn.
⚠️ **CÒN THIẾU (lặp lại ở cả 2 tab — 1 pattern hệ thống, không phải 2 lỗi riêng lẻ):** lỗi hiển thị thô `error.message`, không dịch, không nút Retry (khác hẳn `RiskCaseDrawer` liền kề); toàn bộ chuỗi UI dùng ternary `lang===` trực tiếp thay vì `t()` — lệch kiến trúc dịch chung; vài chỗ rò rỉ enum kỹ thuật thô chưa dịch ra UI (`item.kind`, `s.status`, dropdown lọc trạng thái); cỡ chữ vi mô (9-11px) rải rác không theo scale.
🚨 **GIẢ VỜ CÓ:** "Nhật ký buổi học" — badge lịch sử hiển thị thẳng enum thô backend (`"LECTURE_HELD"`) dù ngay dòng trước đã có `KIND_LABEL` để hiện nhãn thân thiện nhưng bị bỏ sót khi render badge.

**Quan sát xuyên suốt cả 3.3/3.5:** mọi phần là "tab nội bộ mới thêm" đều lệch kiến trúc dịch (`t()` → ternary cục bộ) và error-handling (có Retry → text đỏ trần) so với phần lõi Overview/RiskCaseDrawer — dấu hiệu 2 tab này được thêm sau, bởi luồng phát triển khác, chưa được thống nhất lại chuẩn chung.

---

## 4. Khu vực Quản trị viên — Admin Console (mục 6.5)

7 tab thật trong `AdminConsole.jsx` (đối chiếu trực tiếp code — mục 6.5 hiện chỉ mô tả 6 nhóm chức năng, không khớp 1-1 với tên tab):

| Tab code | Tên hiển thị | Có trong mục 6.5? |
|---|---|---|
| `courses` | Curriculum | Có |
| `academic` | (không tên trong Admin Console, nội dung "Học kỳ hiện hành"/"Lịch thi") | **Không — undocumented, xem mục 7** |
| `policy` | Chính sách AI | Có |
| `mocklms` | Mock LMS | Có (tài liệu riêng ở mục 6.6) |
| `users` | Người dùng + Lời mời | Có |
| `audit` | Audit log | Có |
| `analytics` | Analytics | Có |

### 4.1. Curriculum

✅ **ĐÃ ĐÚNG CHUẨN:** danh sách môn, trạng thái nạp tách rõ real/mock (badge "ĐÃ NẠP" xanh vs "MÔ PHỎNG · N" vàng, không dùng chung màu — verify Playwright 21/08), real content đã tăng lên 44 môn (Phase 2, tối nay) — vượt xa mốc "vài môn" mà mục 6.5 còn ghi là 🔜.
⚠️ **CÒN THIẾU:** mục 6.5 vẫn còn dòng 🔜 "tải file tài liệu thật lên thay vì chỉ nhập tên môn" — **cần xác nhận lại xem còn đúng không** giờ đã có luồng ingest 44 môn qua `real_curriculum_service.py` (có thể dòng 🔜 này đã lỗi thời một phần, chỉ áp dụng cho upload file thủ công qua UI, không áp dụng cho ingest hàng loạt qua script — 2 việc khác nhau, cần Phase 2 (research/evaluate) làm rõ chứ không tự sửa doc ở đây).
🚨 **GIẢ VỜ CÓ:** Không phát hiện.

### 4.2. Người dùng + Lời mời (Invites & Users)

✅ **ĐÃ ĐÚNG CHUẨN:** lock/unlock thật (`PATCH /admin/users/{id}/status`), org-scoped, chặn tự khoá chính mình, invite send/revoke, modal có focus trap, test đầy đủ, ảnh chụp 2 theme × 2 ngôn ngữ × mobile (`docs/evidence/screenshots/2026-08-22_p0-5a-invites-users-tab/`).
⚠️ **CÒN THIẾU:** bước "chọn lớp gán" riêng cho lời mời giảng viên chưa có (`CreateInviteRequest` chưa có field này) — gán lớp vẫn phải làm thủ công sau khi giảng viên vào hệ thống. Đây là gap đã biết từ trước, không phải phát hiện mới.
🚨 **GIẢ VỜ CÓ:** Không phát hiện.

### 4.3. Analytics

✅ **ĐÃ ĐÚNG CHUẨN:** 4 thẻ KPI, biểu đồ xu hướng cảnh báo theo tuần, tách real/mock chunk count, test 24 pass, ảnh chụp đầy đủ.
⚠️ **CÒN THIẾU (góc nhìn mới — production-quality, không phải góc nhìn chức năng đã audit trước):** biểu đồ là CSS thuần tự vẽ (cột đơn giản), không có tương tác (hover để xem số chính xác, zoom theo khoảng thời gian) — nếu đối chiếu theo đúng tinh thần "chuẩn production" mà yêu cầu mới đề cập (Stripe Dashboard/Mixpanel/Retool làm tham khảo), đây là điểm có thể cải thiện rõ ràng nhất của tab này. Đây là nhận định để đưa vào Giai đoạn 1 (Research) — không phải lỗi, chỉ là mức độ polish thấp hơn tham chiếu.
🚨 **GIẢ VỜ CÓ:** Không phát hiện.

### 4.4. Chính sách AI (Guardrail + Risk Policy)

✅ **ĐÃ ĐÚNG CHUẨN:** toggle rule thật, preview/publish/rollback risk policy đầy đủ versioning đúng mục 14.1 (min/max, preview, rollback, audit log), test 22 case, Playwright verify thật.
⚠️ **CÒN THIẾU:**
- Toggle rule guardrail không có ô "lý do đổi" (giới hạn API hiện tại, `AdminGuardrailRuleUpdateRequest` chỉ nhận `enabled`) — dù mục 14.1 yêu cầu *"Admin không được bật/tắt tuỳ tiện rule ảnh hưởng trực tiếp quyền lợi sinh viên... mà không ghi lý do."* Đây là khoảng cách thật giữa business rule đã chốt và implementation hiện tại — đã biết trước nhưng chưa từng bị đối chiếu trực diện với đúng câu chữ mục 14.1 như audit này.
- "Eval risk rules phải chạy lại sau khi đổi policy" (mục 14.1) — vẫn hoàn toàn thủ công, không có cơ chế nhắc/chặn tự động.
🚨 **GIẢ VỜ CÓ:** Không phát hiện.

### 4.5. Audit log

✅ **ĐÃ ĐÚNG CHUẨN:** UI đọc đúng `GET /api/v1/audit/events`, filter theo event_type, mở rộng xem raw metadata.
🚨 **GIẢ VỜ CÓ (mức độ nghiêm trọng — đã biết, nhắc lại vì đây là đúng loại phát hiện Phase 0 cần bắt):** màn hình **trông như** đã org-scoped giống mọi tab Admin khác (Users/Invites/Analytics đều tách theo tổ chức), nhưng **`AuditLog` không có cột `organization_id`** — bất kỳ Admin tổ chức nào cũng xem được nhật ký của MỌI tổ chức khác. Đã escalate ở `docs/PENDING_DECISIONS.md` #2, chưa có quyết định schema. **Đây chính xác là loại "GIẢ VỜ CÓ" mà audit này tìm kiếm: một màn hình nhìn/dùng giống hệt các tab đã org-scope đúng, khiến người dùng (kể cả Admin) mặc định tin nó cũng vậy.**

### 4.6. Cấu hình (Config) — 🚨 GIẢ VỜ CÓ rõ ràng nhất trong toàn bộ Admin Console

Mục 6.5 liệt kê "Cấu hình — bật/tắt chế độ demo, bật/tắt tự động cảnh báo nguy cơ, học kỳ mặc định" như một bullet ngang hàng các mục đã có UI khác, **không đánh dấu 🔜 hay ⚠️ gì cả** — dễ khiến người đọc tài liệu tin đây cũng đã tồn tại.

**Thực tế xác nhận bằng grep trực tiếp:**
- `grep -n "Cấu hình\|config\|Settings" frontend/src/components/admin/AdminConsole.jsx` → **0 kết quả liên quan.** Không có tab, không có nút, không có form nào cho tính năng này ở frontend.
- Backend **đã có sẵn, hoạt động đầy đủ**: `src/api/admin_settings.py` — `GET/PATCH /api/v1/admin/settings` (đã `include_router` trong `src/main.py:95`), model `AdminSettings`, repository `AdminSettingsRepository`.

**Kết luận:** đây là trường hợp "backend xong, frontend 0%" — đúng pattern đã thấy nhiều lần trong dự án (Analytics/Users/Audit log đều từng ở trạng thái này trước 22/08). Khác các mục ⚠️ khác ở chỗ mục 6.5 hiện tại **không hề gắn nhãn cảnh báo nào** cho mục này, nên nếu không audit kỹ sẽ tưởng nhầm là đã xong.

---

## 5. Mock LMS (mục 6.6)

✅ **ĐÃ ĐÚNG CHUẨN (đã verify rất kỹ 22/08, không audit lại chức năng):** app tách biệt thật (FastAPI riêng, SQLite riêng, OAuth client_credentials thật với khoá ký riêng), 2 màn hình Jinja2 + banner, source precedence 5 bậc nối vào citation thật (demo end-to-end: publish deadline → hỏi QA → citation đổi nhãn đúng), preview/publish/rollback versioned đúng mẫu RiskPolicy, `AdminMockLms.jsx` tab đầy đủ draft/preview/publish/history. 392 test pass.

⚠️ **CÒN THIẾU (góc nhìn UI/UX mới — chưa từng đối chiếu trước đây vì lần trước chỉ audit tính đúng đắn tích hợp, không audit chất lượng giao diện):**
- UI của chính app Mock LMS (`mock-lms/app/templates/`) là Jinja2 tối giản **có chủ đích** (mục 6.6: "không dùng chung UI với Cursus") — đây là quyết định phạm vi hợp lệ, **không phải lỗi**, nhưng chưa được đối chiếu với 7 tiêu chí UI/UX (responsive, dark mode, i18n) vì bản thân nó không cần đạt chuẩn đó — cần Giai đoạn 2 (Evaluation) xác nhận lại phạm vi này có cần nâng cấp thêm không hay giữ nguyên tối giản là đủ cho mục đích "chứng minh tích hợp hệ thống ngoài".
- Checkpoint 4b (nối source precedence vào citation phía Plan/StudyTask, ngoài QA) — quyết định 22/08 là "không làm", vẫn còn nguyên hiệu lực, nhắc lại để không lặp lại điều tra.

🚨 **GIẢ VỜ CÓ:** Không phát hiện — đây là 1 trong số ít khu vực có bằng chứng đầy đủ nhất toàn dự án (bug thật tự phát hiện qua bấm tay UI đã được vá + có test regression).

---

## 6. Business rules cross-cutting (mục 13-14, 16) — đối chiếu riêng, không gắn theo màn hình cụ thể

- **Mục 13.2 "actual_minutes" qua modal hỏi, không dùng timer tự động:** ✅ đã audit, **🚨 vi phạm xác nhận** — xem chi tiết đầy đủ ở mục 2.1 (Trang Tổng quan) trên. Không có modal, `actualMinutes` bị gán cứng = `estimatedMinutes` tại `StudentHome.jsx:468`, khiến so sánh actual-vs-estimate luôn luôn "đúng kế hoạch". Đây là phát hiện có mức ảnh hưởng cao nhất trong toàn bộ audit này về tính trung thực của dữ liệu tự báo cáo (self-reported data).
- **Mục 13.3 Reflect câu hỏi theo mức hoàn thành (bảng 4 dòng):** mục 6.3 đã tự ghi nhận đây vẫn là 🔜 (chưa làm, còn hỏi rập khuôn 3 bước giống nhau) — xác nhận lại trạng thái ở mục 2.2 khi agent báo cáo.
- **Mục 14.1 Risk score — outcome definition + missingness:** xem phát hiện mới ở mục 3.1 trên (Lecturer Dashboard).
- **Mục 14.3 Citation contract — 8 khía cạnh:** đã có eval case entailment cụ thể trong tài liệu nhưng **chưa từng đo lại bằng eval thật sau các thay đổi 20-22/08** (P0#5, ngoài phạm vi tối nay).
- **Mục 16 Data contract — provenance đủ 5 loại:** đã verify kỹ cho `official_document`/`simulated` (mock-vs-real conflation fix 21/08); `user_entered`/`system_derived`/`ai_suggested` chưa có audit UI riêng xem có hiển thị đúng nhãn tương ứng ("Do bạn cung cấp"/"Hiện công thức"/"Ước tính của Cursus Assistant") ở mọi nơi hiển thị hay chỉ ở nơi đã audit — cần bổ sung nếu có thời gian.

---

## 7. Cụm tính năng chưa tài liệu hoá — Semester/Practice/Companion/Academic (điều tra chuyên sâu, trả lời dứt khoát mục 23)

Điều tra bằng 2 agent độc lập (1 kiến trúc/quan hệ dữ liệu, 1 UI/UX chi tiết) — kết quả **hội tụ hoàn toàn**, không mâu thuẫn ở bất kỳ điểm nào. UI/UX chi tiết từng file đã trình bày ở mục 2.4/3.5; mục này tập trung vào 4 câu hỏi kiến trúc mà mục 23 để ngỏ.

### 7.1. Có "mồ côi" không? — Có, nhưng chỉ 2/8 màn hình

`planner`/`practice`/`companion` (Student, có sidebar) và 2 tab Instructor + 1 tab Admin (`academic`, bấm được thật) — **không mồ côi**, chỉ thiếu tài liệu. Riêng `semester-setup`/`lecture-plan` — **mồ côi thật sự**: 0 link Sidebar/Topbar, chỉ tự trỏ vào nhau, code tự nhận trong comment ("reachable only via its own route").

### 7.2. Quan hệ với luồng Plan-Do-Reflect chính (Gate2Demo) — song song thật, có đụng độ, xử lý ÂM THẦM

`StudentPlanner.jsx` **không** thuộc cụm lạ — dùng thẳng `useGate2()`, chính là bước Plan của Gate2Demo tách route riêng.

`SemesterSetupWizard` + `LecturePlanPanel` **là hệ thống song song thật sự**, dùng chung bảng DB với Gate2Demo (`WeeklyPlan`/`DailyPlan`/`ScheduleBlock`/`StudyTask`, `src/db/models.py:464-509`), phân biệt chỉ bằng 1 tag `WeeklyPlan.goals["source"]="lecture_plan"`. Có cơ chế chống đụng độ **thật, đã verify bằng code, không chỉ comment** — ở 3 nơi độc lập (`src/api/plans.py:171-201`, `src/api/student.py:398-432`, `src/services/academic/timetable_service.py:473-480,549-558`): Gate2 plan (có `assignment_id`) luôn được cộng +5 điểm ưu tiên, luôn thắng. **Vấn đề:** cơ chế này dựa trên **magic string `"lecture_plan"` lặp lại ở 5 chỗ code khác nhau, không có hằng số dùng chung**, và khi đụng độ xảy ra, **sinh viên không được báo** rằng lecture-plan của họ vừa bị đè bởi Gate2 plan cùng tuần.

`AdminAcademicPanel` (Admin) **có ảnh hưởng thật, đã verify 2 chiều cụ thể** tới `SemesterSetupWizard`/`LecturePlanPanel`: `semester_service.py:317-323` — ngày học kỳ Admin nhập sẽ **ghi đè** ngày sinh viên tự chọn; `semester_service.py:331-339` — **chặn** tạo học kỳ nếu môn trùng lịch thi Admin đã nhập; `lecture_plan_service.py:240` — kéo thẳng lịch thi Admin vào task "Ôn thi" tự sinh cho sinh viên. Ngược lại, `AcademicTerm`/`CourseExam` **không hề chạm tới Gate2Demo** (0 kết quả grep trong `gate2_demo.py`/`plan_builder.py`/`student_mock_data_service.py`).

### 7.3. `weekly_plan_service.py`/`study_scheduler.py` — không đổi tên, bị thay thế có chủ đích, có tự thừa nhận regression

Xác nhận qua `git show 5df784c:...` — 2 file gốc thật sự tồn tại trên `origin/develop`. HEAD thay bằng `lecture_plan_service.py`, và **docstring đầu file tự khai rõ 3 khác biệt cụ thể** với bản gốc, trong đó quan trọng nhất: **bỏ RAG-grounding** — bản gốc lấy nội dung task từ retrieval syllabus chunks thật, bản hiện tại chỉ sinh template cố định ("ôn trước/luyện sau"), tự nhận đây là đánh đổi để "self-contained and cheap". Đây là tái kiến trúc có ý thức, không phải mất mát âm thầm — nhưng nghĩa là task do `lecture_plan_service` sinh ra **không có citation/nguồn thật** như phần Gate2Demo có, dù cả hai đều hiện ra như "task học tập" giống nhau trên UI.

### 7.4. Dữ liệu thật hay giả — 100% THẬT ở mọi route, không có fixture/hardcode nào trong cụm này

`SemesterService`/`LecturePlanService`/`AcademicTermService` đều query bảng SQL thật. `practice_generator.py:82-88` gọi **LLM thật** khi có key cấu hình, fallback tất định vẫn lấy từ chunk RAG thật (không bịa). `CompanionService` tái dùng nguyên pipeline QA production (`QaAnswerService`/`RetrievalService`/`GuardrailService`). **Đây là điểm khác biệt quan trọng với các phát hiện "GIẢ VỜ CÓ" khác trong audit này** — cụm tính năng này không giả, chỉ vô hình/thiếu tài liệu.

### 7.5. Chất lượng UI — tóm tắt chéo (chi tiết đầy đủ từng file ở mục 2.4/3.5)

Quan sát hệ thống nhất quán: **mọi màn hình là route riêng** (`StudentPlanner`, `SemesterSetupWizard`, `StudentPractice`, `CourseCompanionChat`, `LecturePlanPanel`) đều dùng đúng `Skeleton`+`ErrorState`/`EmptyState` chuẩn của app; **mọi phần nhúng làm tab** (2 tab Instructor + `AdminAcademicPanel`) đều tự viết loading/error thô sơ hơn, bỏ qua component dùng chung. i18n cũng lệch: 8 file trong cụm này 100% dùng ternary `lang===` trực tiếp, 0 khoá nào khớp `locales/*.js`, cộng 3 mini-dictionary cục bộ khác nhau cho cùng khái niệm "nhãn trạng thái" (`STATUS_LABEL`, `KIND_LABEL`, `WEEKDAY_LABEL`) — hoạt động đúng cho cả 2 ngôn ngữ nhưng đi lệch kiến trúc `t()` chung của phần còn lại của app.

### 7.6b. Phát hiện bổ sung khi thực thi Checkpoint 8 (22/08, tối) — cơ chế "Gate2 luôn thắng" KHÔNG áp dụng cho đường live thật

Khi cài đặt thông báo "kế hoạch bị đè" (mục 7.6 ý 1 dưới), phát hiện: `_resolve_plan`/`_resolve_plan_for_reflection` (nơi có đúng logic ưu tiên `assignment_id`+5 điểm) **không phải nơi `StudentPlanner.jsx`/`StudentHome.jsx` thực sự dùng** — 2 màn hình này lấy dữ liệu qua `useGate2()` → `GET /student/demo/state`, và hàm dựng plan trong `get_demo_state` (`src/api/student.py` dòng ~572-590) dùng logic chọn **hoàn toàn khác, đơn giản hơn**: `next(plan for plan in plans if plan.week_number == week_number)` — không hề so điểm ưu tiên `assignment_id` như 2 hàm kia. Nếu 1 sinh viên có cả plan Gate2 lẫn `lecture_plan` cùng tuần, kết quả phụ thuộc thứ tự trả về của query DB (không cam kết edge nào thắng), không đảm bảo Gate2 luôn thắng như tài liệu (docstring `lecture_plan_service.py`) mô tả.

**Quyết định tối nay:** KHÔNG sửa logic chọn plan trong `get_demo_state` — đây là đường dữ liệu chính của toàn bộ demo, sửa hành vi lõi ngay trước giờ nộp bài rủi ro cao hơn giá trị. Đã thêm thông báo "superseded" đúng vào `GET /plans/weekly` (chỗ CÓ logic ưu tiên đúng, dùng `_resolve_plan(with_superseded=True)`, có test), nhưng route này **hiện không được frontend gọi** (`getWeeklyPlan()` ở `lib/api.js:515` không có nơi nào import/dùng trong `frontend/src/components` — cùng họ "dead code" với `getStudentDashboard()` đã biết từ 20/08). Coi đây là **fix đúng, đã test, sẵn sàng khi route được nối dây thật** — không phải fix cho đường demo đang chạy. Ghi nhận riêng để không mất dấu, cần quyết định ở Giai đoạn sau: nối `get_demo_state` dùng chung `_resolve_plan`, hay chấp nhận 2 luồng plan-resolution khác nhau vĩnh viễn (1 cho demo Gate2, 1 cho luồng thật).

### 7.6. Khuyến nghị cho Giai đoạn 3 (Plan) — 3 nhánh hành động khác nhau, không gộp chung 1 giải pháp

1. **Cần escalate quyết định kiến trúc (không tự sửa ở Giai đoạn thực thi):** cơ chế chống đụng độ Gate2-vs-lecture_plan — gộp 2 luồng plan làm một, hay giữ tách biệt vĩnh viễn kèm UI thông báo rõ ràng khi 1 bên bị đè? Đề xuất tối thiểu không cần quyết định lớn ngay: đổi 5 magic-string `"lecture_plan"` thành 1 hằng số dùng chung (rủi ro thấp, dọn nợ kỹ thuật) + thêm 1 dòng thông báo UI khi phát hiện đụng độ (rủi ro thấp, cải thiện trung thực dữ liệu) — 2 việc này có thể làm ngay không cần chờ quyết định "gộp hay tách".
2. **Đưa vào tài liệu chính thức + dọn UI nhỏ (không cần quyết định kiến trúc):** `StudentPractice`, `CourseCompanionChat`, 2 tab Instructor, tab Admin `academic` — cập nhật mục 6 để phản ánh đúng, chuẩn hoá loading/error component, chuyển dần sang `t()`.
3. **Thêm 1 dòng nav, KHÔNG viết lại:** `SemesterSetupWizard`/`LecturePlanPanel` — chất lượng code/UI tốt, dữ liệu thật, chỉ thiếu đúng 1 điểm vào từ Sidebar hoặc thẻ liên kết từ trang Tổng quan. Chi phí sửa thấp nhất trong toàn bộ cụm so với giá trị tính năng đang bị chôn.

---

## 8. Bảng tổng hợp toàn bộ Giai đoạn 0

**Thống kê nhanh:** 8 màn hình/tính năng thật sự tồn tại nhưng vắng mặt khỏi mục 6 (`planner`, `practice`, `companion` trang riêng, `semester-setup`, `lecture-plan`, `academic` tab Admin, 2 tab Instructor); 2 route mồ côi hoàn toàn; 1 tab Admin có backend nhưng 0% frontend; ít nhất **8 phát hiện 🚨 GIẢ VỜ CÓ** ở các mức độ nghiêm trọng khác nhau; toàn bộ dữ liệu trong cụm chưa tài liệu hoá được xác nhận là **thật**, không phải fixture.

### 8.1. Xếp hạng theo mức độ nghiêm trọng (🚨 = ảnh hưởng người dùng/demo trực tiếp, active-wrong; ⚠️ = thiếu/chưa đạt chuẩn nhưng không gây hiểu lầm chủ động)

| # | Mức độ | Phát hiện | Vị trí | Vì sao nghiêm trọng |
|---|---|---|---|---|
| 1 | 🚨🚨🚨 | Biểu đồ tiến độ lớp Giảng viên là mảng hardcode 4 số, cảnh báo "xu hướng giảm" hiện **vĩnh viễn cho mọi giảng viên** | `InstructorHome.jsx:12,58,185` | Trung tâm demo Lecturer HITL (mục 19.1); hiển thị SAI chủ động, không chỉ thiếu |
| 2 | 🚨🚨🚨 | "Cursus Assistant" = 3 hệ thống khác nhau; bản "nổi mọi trang" là kịch bản FAQ cứng, biến mất hoàn toàn sau đăng nhập | `CuriChatLauncher.jsx` + `CuriContextPanel.jsx` + `CourseCompanionChat.jsx` | Lời hứa cốt lõi "luôn trả lời kèm trích nguồn, nổi mọi lúc" (mục 6.2, câu mở đầu mục 1) không đúng ở chính bản nổi thật |
| 3 | 🚨🚨 | "Hoàn tất hồ sơ" — form thật không thể hiển thị cho bất kỳ ai (`user` state không bao giờ được gán) | `OnboardingScreen.jsx:20,161-168`, `App.jsx:588` | Yêu cầu spec 6.1 không xảy ra ở bất kỳ đường nào trong hệ thống |
| 4 | 🚨🚨 | Danh sách sinh viên + tìm kiếm (Lecturer) — "xác chết tính năng": backend + locale keys có sẵn, UI không tồn tại | `InstructorHome.jsx` (thiếu đọc `classInfo.roster`), `locales/*.js:285-290` | Tính năng cốt lõi mục 6.4, chi phí hoàn thiện thấp vì phần khó đã xong |
| 5 | 🚨 | Audit log không org-scoped — Admin tổ chức này xem được log MỌI tổ chức khác | `AuditLog` model, đã escalate `PENDING_DECISIONS.md` #2 | Rò rỉ dữ liệu chéo tổ chức, đã biết trước nhưng đáng nhắc lại vì đúng loại lỗi "trông như đúng" |
| 6 | 🚨 | Google login luôn báo lỗi 100% số lần, không phải thỉnh thoảng | `LoginScreen.jsx:118-125` | Trực tiếp mâu thuẫn spec "đăng nhập bằng Google hoặc email" |
| 7 | 🚨 | `actual_minutes` luôn luôn = `estimated_minutes` (không có modal hỏi), mọi so sánh thực tế-vs-ước tính vô nghĩa | `StudentHome.jsx:467-468` | Vi phạm trực diện mục 13.2; làm hỏng dữ liệu nền cho Reflect |
| 8 | 🚨 | Cấu hình (Admin) — backend xong hoàn toàn, frontend 0%, mục 6.5 không hề cảnh báo | `AdminConsole.jsx` (0 kết quả), `src/api/admin_settings.py` (đã mount) | Dễ bị tưởng nhầm là đã xong nếu không audit kỹ |
| 9 | ⚠️⚠️ | Cụm Semester/Practice/Academic (~5100 dòng, dữ liệu thật) vắng mặt khỏi mọi tài liệu/thuyết trình | Mục 7 | Có thể là phần lớn phạm vi "Nâng cao" (mục 2.4) chưa từng được tính điểm |
| 10 | ⚠️⚠️ | 2 route mồ côi hoàn toàn (`semester-setup`, `lecture-plan`) — tính năng tốt nhưng vô hình | Mục 7.1 | Chi phí sửa thấp nhất (1 dòng nav) so với giá trị bị chôn |
| 11 | ⚠️ | Sidebar + banner demo-mode + nhiều `aria-label` hardcode tiếng Việt, không đổi khi chuyển English | `App.jsx` (nhiều dòng, gốc rễ `constants/roles.js`) | Hạng mục "chuyển ngôn ngữ" bắt buộc theo thang điểm BTC (mục 9/10), lỗi ở nơi luôn hiển thị |
| 12 | ⚠️ | `AuthLayout` ẩn h1 dưới 1024px — 5+ màn hình auth không có heading nào ở mobile; 2 màn có h1 trùng ở desktop | `AuthLayout.jsx:58-59`, `ForgotPasswordScreen.jsx`, `ResetPasswordScreen.jsx` | 1 lỗi layout dùng chung ảnh hưởng đồng loạt nhiều màn |
| 13 | ⚠️ | Badge mức rủi ro (Lecturer) fail/cận-fail WCAG AA ở theme sáng (3.07-4.41:1) | `RiskCaseDrawer.jsx`, `InstructorHome.jsx` | Tiêu chí bắt buộc theo thang điểm BTC ("thiết kế giao diện", mục 10) |
| 14 | ⚠️ | Thiếu tooltip định nghĩa "nguy cơ" + trạng thái "chưa đủ dữ liệu" riêng (mục 14.1) | Toàn bộ `frontend/src/components/instructor/` | Yêu cầu compliance rõ ràng trong chính tài liệu nghiệp vụ |
| 15 | ⚠️ | Class picker Lecturer không tồn tại dù multi-class là thật | `InstructorHome.jsx` | Sai lệch trực tiếp với mô tả mục 6.4 |
| 16 | 📝 | Loạt gap nhỏ nhất quán: typography scale phân mảnh (9-15px tự do khắp nơi), error-state thiếu Retry ở các tab mới, i18n kiến trúc lệch (ternary thay vì `t()`) ở mọi màn hình mới thêm | Nhiều file, xem mục 2-7 | Không nghiêm trọng riêng lẻ nhưng cộng dồn ảnh hưởng điểm "Chất lượng mã nguồn"/"Thiết kế giao diện" |

### 8.2. Điểm đáng mừng — không phải mọi thứ đều là gap

- Dữ liệu ở **mọi nơi audit tối nay** (kể cả cụm "lạ" mục 7) đều là **dữ liệu thật**, không phát hiện thêm fixture/hardcode giả nào ngoài các mục đã liệt kê ở 8.1 — kiến trúc data pipeline nhìn chung đáng tin cậy.
- `RiskCaseDrawer.jsx`, `AcceptInviteScreen.jsx`, `NotFoundPage.jsx`, `SettingsScreen.jsx`, `StudentReflection.jsx`, `StudentPlanner.jsx` là các màn hình chất lượng cao, đáng dùng làm mẫu tham chiếu khi sửa các màn khác (loading/error/empty đầy đủ, a11y tốt, đúng kiến trúc `t()`).
- Toàn bộ 6.5 (Admin) và 6.6 (Mock LMS) đã có mức độ verify/evidence sâu nhất dự án — chỉ còn vài điểm polish (mục 4, 5), không có phát hiện nghiêm trọng mới.
- "Chọn vai trò demo" khớp 100% với spec ở cả frontend lẫn backend — không có lỗ hổng tạo `User` giả.

---

**Giai đoạn 0 hoàn tất.** Theo đúng mandate, không có cổng chặn sau Giai đoạn 0/1 — tiếp tục sang Giai đoạn 1 (Research) ngay, sẽ dừng lại chờ duyệt sau Giai đoạn 2 (Evaluation) như đã yêu cầu.
