# PLAN 3 — Kế hoạch thực thi chi tiết (Giai đoạn 3)

**Đã duyệt (Giai đoạn 2):** toàn bộ 10 việc Nhóm A · C1 = sửa tài liệu (không hợp nhất Cursus Assistant) · C3 = giữ nguyên audit log, chỉ ghi nhận · C4 = không làm tab Cấu hình đợt này.

**Kỷ luật áp dụng xuyên suốt (đã dùng nhất quán cả phiên, không lặp lại giải thích ở từng checkpoint):** 1 commit/checkpoint · `pytest --junitxml=docs/evidence/test-runs/...` cho mọi checkpoint đụng backend · không đụng Supabase/schema · không push (đợi lệnh) · nếu hết giờ giữa chừng, báo đúng "đã code, CHƯA verify" — không tự nhận đã xong. **Bậc bằng chứng theo mức độ hiển thị:** checkpoint đụng UI hay bị giám khảo nhìn thấy trực tiếp (A1 sidebar, A3 modal, A4 bảng, A8/A9 badge) → ảnh chụp 2 theme + 2 ngôn ngữ tối thiểu (bỏ bớt mobile nếu thiếu giờ, ghi rõ lý do); checkpoint ít hiển thị/thuần logic (A6, A10 backend, A2 layout) → 1 bộ ảnh sáng/tối là đủ, ưu tiên pytest hơn ảnh.

**Thứ tự cố định** (theo mục "Thứ tự đề xuất" của Giai đoạn 2, không đổi trừ khi phát sinh phụ thuộc mới):

---

## Checkpoint 1 — A1: `constants/roles.js` có bản tiếng Anh

1. Đọc `frontend/src/constants/roles.js` + tất cả nơi gọi `ROLE_LABEL`/`ROLE_DESC` (grep toàn `frontend/src` trước khi sửa — đã biết tối thiểu `App.jsx:146,149`, `UnauthorizedPage.jsx:27-28`, `AcceptInviteScreen.jsx` có bản trùng lặp riêng `ROLE_LABEL_VI/EN`).
2. Đổi shape thành `{ vi: {...}, en: {...} }` (giữ nguyên key role: `student/instructor/admin`), cập nhật mọi nơi gọi để chọn theo `lang` hiện tại.
3. Xoá `ROLE_LABEL_VI`/`ROLE_LABEL_EN` viết tay trong `AcceptInviteScreen.jsx`, thay bằng import từ `constants/roles.js` — dọn trùng lặp nhân tiện (không phải yêu cầu thêm, chỉ vì cùng 1 lần sửa).
4. **Verify:** dev server, đổi ngôn ngữ, xác nhận: hộp vai trò Sidebar, `UnauthorizedPage`, `AcceptInviteScreen` đều đổi đúng cả 2 ngôn ngữ. Ảnh 2 theme × 2 ngôn ngữ cho Sidebar (nơi hiển thị rõ nhất).
5. Commit riêng.

## Checkpoint 2 — A2: `AuthLayout.jsx` sửa heading

1. Đọc `AuthLayout.jsx` dòng 40-95 (khu vực h1 hiện tại), `ForgotPasswordScreen.jsx` dòng 60-90, `ResetPasswordScreen.jsx` dòng 110-140.
2. Sửa `AuthLayout` để h1 luôn có mặt trong DOM (bỏ `hidden` khỏi chính thẻ heading — nếu cần ẩn phần trang trí bên cạnh nó ở mobile thì tách riêng phần trang trí ra khỏi phần tử heading, không ẩn cả cụm).
3. Bỏ h1 tự thêm ở `ForgotPasswordScreen`/`ResetPasswordScreen`, đổi thành h2 (khớp pattern `EmailVerificationScreen.jsx` đã làm đúng).
4. **Verify:** thu nhỏ viewport <1024px, xác nhận có đúng 1 h1 (dùng DevTools/Accessibility tree, không chỉ nhìn mắt) trên cả 5 màn hình auth qua `AuthLayout`. Ảnh sáng/tối, 1 màn đại diện (Login) + xác nhận nhanh 4 màn còn lại không cần ảnh riêng.
5. Commit riêng.

## Checkpoint 3 — A6: Google login — ẩn/vô hiệu hoá rõ ràng

1. Đọc `LoginScreen.jsx` dòng 118-165 (`handleGoogleLogin` + nút render).
2. Đổi nút sang trạng thái `disabled` thật với nhãn phụ rõ ràng (2 ngôn ngữ) kiểu "Sắp ra mắt"/"Coming soon" thay vì bấm được rồi báo lỗi tĩnh; xoá handler giả hiện lỗi, xoá import `supabase` không dùng.
3. **Verify:** bấm thử xác nhận không còn thông báo lỗi giả nào xuất hiện, nút rõ ràng là chưa khả dụng chứ không phải "trông như lỗi". Ảnh sáng/tối.
4. Commit riêng.

## Checkpoint 4 — A9: Tooltip định nghĩa "nguy cơ" (mục 14.1)

1. Xác định đúng vị trí cần thêm: badge risk ở `InstructorHome.jsx` (thẻ cảnh báo) + `RiskCaseDrawer.jsx` (badge mức độ).
2. Thêm icon info nhỏ cạnh badge, `title`/tooltip nội dung đúng câu mục 14.1 đã chốt: "Nguy cơ = có thể trễ kế hoạch tuần này/assignment sắp tới — KHÔNG phải dự đoán kết quả học tập dài hạn", dịch đủ 2 ngôn ngữ.
3. **Verify:** hover/focus vào icon hiện đúng nội dung cả 2 ngôn ngữ. Ảnh sáng/tối.
4. Commit riêng.

## Checkpoint 5 — A8: Risk badge contrast (light theme)

1. Đọc token hiện tại trong `index.css` cho `.badge-danger`/`.badge-warning`/`.badge-success` (giá trị đã biết từ audit: danger 4.41:1, success 3.60:1, warning 3.07:1 — cả 3 dưới hoặc cận ngưỡng 4.5:1 ở theme sáng).
2. Tính lại giá trị text color (giữ nguyên nền `-soft` nếu có thể, ưu tiên đổi màu chữ đậm hơn trước khi đổi nền, để ít ảnh hưởng thị giác nhất) đạt ≥4.5:1 bằng đúng công thức WCAG đã dùng trong audit — không áng chừng.
3. Áp dụng, kiểm tra không phá vỡ theme tối (đang đạt chuẩn, giữ nguyên nhánh dark).
4. **Verify:** đo lại contrast bằng công thức, xác nhận ≥4.5:1 cả 3 badge. Ảnh sáng/tối cho `RiskCaseDrawer` (nơi cả 3 màu cùng xuất hiện).
5. Commit riêng.

## Checkpoint 6 — A3: Modal xác nhận thời gian thực tế khi "Hoàn thành" task

1. Đọc `DeferTaskDialog.jsx` toàn bộ làm khuôn mẫu (đã đúng chuẩn theo audit).
2. Tạo `CompleteTaskDialog.jsx` mới (hoặc tên tương tự) cùng thư mục `frontend/src/components/student/`: input số phút, giá trị mặc định = `task.estimatedMinutes`, cho sửa tay, nút xác nhận gọi `completeTask(task.id, actualMinutesNhập)`.
3. Sửa `StudentHome.jsx:467-468` — `handleComplete` mở dialog thay vì gọi thẳng `completeTask` với `estimatedMinutes`.
4. **Verify:** hoàn thành 1 task với số phút KHÁC estimate qua UI thật (dev server), xác nhận `actualMinutes` lưu đúng giá trị nhập (không phải estimate) — kiểm tra qua network tab hoặc lại vào Trang Phản tư xem con số đổi đúng. Ảnh 2 theme + 2 ngôn ngữ (đây là 1 trong các màn quan trọng nhất, hiển thị nhiều).
5. Commit riêng.

## Checkpoint 7 — A5: Thêm nav link cho `semester-setup`/`lecture-plan`

1. Thêm 2 mục vào Sidebar (`App.jsx`, cạnh các mục Student hiện có) hoặc 1 thẻ liên kết trong `StudentHome.jsx` — quyết định cụ thể khi vào code dựa trên chỗ nào ít xáo trộn layout Sidebar hiện tại nhất (Sidebar đã có 7 mục, thêm 2 nữa có thể cần xem lại `flex-wrap`/scroll của chính Sidebar).
3. Dịch đủ 2 ngôn ngữ, dùng đúng hệ `t()` (không lặp lại lỗi ternary cục bộ của chính 2 trang đích).
4. **Verify:** bấm từ Sidebar vào được cả 2 trang, không cần gõ URL tay. Ảnh sáng/tối.
5. Commit riêng.

## Checkpoint 8 — A10: Dedupe magic string `"lecture_plan"` + thông báo khi bị đè

1. Grep chính xác 5 vị trí đã xác định (`lecture_plan_service.py:7,15,112`; `api/lecture_plan.py:59,72,78`; `timetable_service.py:474,480,549,558`) — tạo 1 hằng số dùng chung (đặt ở `src/services/academic/` cạnh các service liên quan, vd trong `lecture_plan_service.py` rồi import từ nơi khác, hoặc 1 module constants nhỏ nếu tránh được import vòng).
2. Đọc kỹ `_resolve_plan`/`_resolve_plan_for_reflection` (`src/api/plans.py:171-201`, `src/api/student.py:398-432`) để tìm điểm quyết định "Gate2 thắng" — thêm 1 field vào response (vd `supersededLecturePlan: bool` hoặc tương tự) khi có 1 lecture-plan cùng tuần bị bỏ qua.
3. Frontend (`StudentPlanner.jsx` hoặc `StudentHome.jsx`, tuỳ nơi hiện plan) — hiện 1 dòng thông báo nhỏ khi field đó = true, dịch đủ 2 ngôn ngữ.
4. **Verify:** `pytest` cho service liên quan (thêm case: có cả 2 loại plan cùng tuần → field thông báo = true; chỉ có 1 loại → false) — đây là checkpoint có test tự động thật, ưu tiên pytest hơn ảnh chụp. 1 ảnh minh hoạ thông báo hiện đúng nếu kịp tạo được tình huống đụng độ qua UI thật.
5. Commit riêng.

## Checkpoint 9 — A4: Bảng danh sách sinh viên + tìm kiếm (Lecturer)

1. Đọc `AdminUsers.jsx` toàn bộ làm khuôn cấu trúc bảng (đã ✅ audit, có sẵn search debounce/style).
2. Đọc `src/api/instructor.py:315-346,375` xác nhận chính xác field trong `roster` hiện trả về (`studentId`, `displayName`, `completionRate`, `score`, `severity`, `riskLevel`) — không đoán field, đọc code thật trước khi viết JSX.
3. Thêm section mới trong `InstructorHome.jsx` (dưới danh sách cảnh báo, đúng thứ tự spec 6.4), dùng lại các khoá dịch đã có sẵn (`studentListTitle`, `colName`, `colCourse`, `colProgress`, `colRisk`, `colAction`, `markIntervenedBtn` — xác nhận lại các khoá này còn khớp cấu trúc dữ liệu thật trước khi dùng, sửa nếu lệch). Tìm kiếm theo tên: filter phía client trên `roster` đã có (không cần API mới, dữ liệu đã trả đủ về 1 lần).
4. Nút hành động mỗi dòng tái dùng đúng mutation `interveneAlert` đã dùng ở nơi khác trong cùng file (không tạo API call mới).
5. **Verify:** dev server, gõ tìm 1 tên sinh viên có thật trong dữ liệu demo, xác nhận lọc đúng; bấm nút hành động, xác nhận gọi đúng API đã có. Ảnh 2 theme × 2 ngôn ngữ (tính năng cốt lõi mục 6.4, ưu tiên bằng chứng đầy đủ).
6. Commit riêng.

## Checkpoint 10 — A7: Biểu đồ Lecturer dùng dữ liệu tuần thật (nặng nhất, làm cuối để các checkpoint trước đã an toàn nếu hết giờ)

**Bước đầu tiên bắt buộc trước khi viết code — điều tra, chưa giả định sẵn cách làm:**
1. Đọc kỹ `src/api/instructor.py:361-381` + truy ngược hàm tính `weeklyCompletionRate` hiện tại để biết nó lấy dữ liệu từ bảng nào (`StudyTask`? `WeeklyPlan`?) theo scope gì (`class_id`? `instructor_id`?).
2. Xác định cách nhóm theo tuần hợp lý (4 tuần gần nhất, giống `RiskCaseDrawer`'s timeline đã làm — tái dùng cùng cách nếu hợp lý, tránh phát minh 1 cách tính tuần khác).
3. Nếu việc này phức tạp hơn dự kiến (đụng nhiều bảng, cần join phức tạp) và không đủ thời gian làm chắc chắn đúng: **phương án an toàn thay thế** — xoá hẳn banner "cảnh báo xu hướng giảm" (thay vì để nó luôn hiện sai) và hiện biểu đồ với đúng 1 cột duy nhất (giá trị trung bình thật đang có) kèm ghi chú "chưa đủ dữ liệu lịch sử theo tuần" — **thà thiếu tính năng còn hơn tính năng nói sai**, đúng nguyên tắc đã áp dụng xuyên suốt dự án.
4. Nếu điều tra bước 1-2 cho thấy khả thi trong thời gian còn lại: viết query mới trả mảng theo tuần thật, sửa `InstructorHome.jsx` đọc từ `classInfo.weeklyTrend` (tên field ví dụ) thay vì `DASH_DATA.class_avg`, xoá `DASH_DATA` hardcode khỏi file.
5. **Verify:** pytest cho endpoint (case: lớp có dữ liệu nhiều tuần → mảng đúng thứ tự/giá trị; lớp mới/ít dữ liệu → không crash, trả mảng ngắn hơn hoặc rỗng có ý nghĩa). Ảnh 2 theme cho biểu đồ với dữ liệu thật.
6. Commit riêng — **ghi rõ trong commit message phương án nào được chọn** (mảng thật hay fallback an toàn) để không ai nhầm lẫn sau này.

---

## Nhóm B — Cập nhật tài liệu (làm xen kẽ bất kỳ lúc nào, không phụ thuộc thứ tự trên)

Cập nhật `docs/PROJECT_CONTEXT.md`:
- Mục 6.3: thêm `planner`/`practice`/`companion` (trang riêng) vào danh sách trang Student, ghi rõ đã có sidebar link.
- Mục 6.3 (Hoàn tất hồ sơ, mục 6.1 thật ra): ghi chú "hiện không hoạt động trong luồng thật — form tồn tại nhưng không thể truy cập; profile/enrollment hiện được seed sẵn phía server" (theo đúng quyết định B2 đã duyệt).
- Mục 6.2: sửa mô tả Cursus Assistant cho khớp thực tế (3 điểm chạm khác nhau, không phải 1 widget nổi mọi trang) — đây chính là hành động cụ thể cho quyết định C1; ghi thêm banner demo-mode chưa tồn tại.
- Mục 6.4: thêm 2 tab "Nhật ký buổi học"/"Duyệt luyện tập"; ghi nhận gap "class picker chưa có" + "thiếu trạng thái chưa đủ dữ liệu" (mục 14.1) là biết trước, chưa làm đợt này.
- Mục 6.5: thêm tab `academic` (Học kỳ + Lịch thi); giữ cảnh báo rõ cho "Cấu hình" là chưa có UI (quyết định C4).
- Mục 9 hoặc mục mới: dẫn link tới `AUDIT_0_HIENTRANG.md`/`EVALUATION_2_KETLUAN.md` làm hồ sơ audit đầy đủ, tránh lặp lại toàn bộ chi tiết vào chính PROJECT_CONTEXT.md (giữ nguyên tắc file gọn, đã có ở mục 9 P2 ý 13).

Không cần checkpoint/commit riêng cho từng dòng — gộp thành 1 commit "docs" sau khi Nhóm A xong (hoặc sớm hơn nếu thuận tiện), vì đây là thay đổi tài liệu thuần, không có rủi ro kỹ thuật cần cô lập.

---

## Sau khi xong toàn bộ (Giai đoạn 4 verify tổng thể)

`pytest tests/` toàn bộ 1 lần cuối, xác nhận không có test nào vỡ so với mốc trước khi bắt đầu; cập nhật `docs/SESSION_REPORT_20260822.md` với bảng tổng kết 10 checkpoint (đã làm/chưa làm/phương án nào được chọn cho A7); báo cáo cuối cùng cho bạn kèm danh sách file đã đổi + gợi ý commit message tổng, để bạn tự quyết push.

---

**Dừng lại ở đây theo đúng yêu cầu — chờ duyệt Plan này (giữ nguyên/bớt/đổi thứ tự) trước khi bắt đầu Checkpoint 1.**
