# EVALUATION 2 — Kết luận & đề xuất ưu tiên (Giai đoạn 2)

**Bối cảnh bắt buộc phải nói thẳng trước khi đọc tiếp:** deadline là 23/08/2026 — tức **ngày mai**. Audit (Giai đoạn 0) tìm ra nhiều hơn dự kiến rất nhiều: 16 phát hiện, trong đó có những phát hiện lớn (biểu đồ Lecturer bịa số, "Cursus Assistant" là 3 hệ thống rời rạc, 1 form onboarding chết hoàn toàn, cả 1 cụm ~5100 dòng chưa từng được tài liệu hoá). Nếu cố làm hết mọi thứ mục 8.1 liệt kê, chắc chắn không kịp và rủi ro làm hỏng thứ đang chạy tốt ngay trước giờ nộp. Giai đoạn này **tồn tại chính xác để tránh việc đó** — chia 16 phát hiện thành 3 nhóm hành động rõ ràng, không né tránh việc nói "cái này không kịp làm, chỉ ghi nhận."

---

## Nhóm A — Làm ngay trong Giai đoạn 3-4 (rẻ, an toàn, giá trị cao)

Tiêu chí chọn vào nhóm này: (1) phạm vi sửa đổi nhỏ, khoanh vùng rõ, (2) không đụng schema/migration/kiến trúc, (3) có pattern đã đúng sẵn trong app để tái dùng (không thiết kế từ đầu), (4) rủi ro làm vỡ tính năng đang chạy tốt là thấp.

| # | Việc | Vì sao rẻ | Giá trị | File chính |
|---|---|---|---|---|
| A1 | `constants/roles.js` thêm bản tiếng Anh cho `ROLE_LABEL`/`ROLE_DESC` | 1 file, thêm object, sửa 3-4 nơi gọi để chọn theo `lang` | **Cao — sửa cùng lúc ≥4 gap** (sidebar, UnauthorizedPage, AcceptInviteScreen, theme-toggle label) | `frontend/src/constants/roles.js` |
| A2 | `AuthLayout.jsx` — sửa cách ẩn h1 dưới 1024px (không dùng `hidden` cho riêng thẻ heading) + bỏ h1 trùng ở `ForgotPasswordScreen`/`ResetPasswordScreen` | 1 layout dùng chung, sửa 1 lần | Sửa heading-hierarchy cho ≥5 màn hình auth cùng lúc | `AuthLayout.jsx` + 2 file |
| A3 | Nút "Hoàn thành" task — thêm modal hỏi thời gian thực tế, clone đúng pattern `DeferTaskDialog.jsx` đã có sẵn và đúng | Pattern đã tồn tại, chỉ áp dụng lại cho 1 nút khác | Sửa đúng vi phạm mục 13.2, khôi phục tính trung thực dữ liệu tự báo cáo | `StudentHome.jsx` |
| A4 | Bảng danh sách sinh viên + tìm kiếm (Lecturer) — ráp `classInfo.roster` (đã có ở backend) vào 1 bảng UI, tái dùng cấu trúc bảng của `AdminUsers.jsx` | Data + bản dịch đã có sẵn 100%, chỉ thiếu UI | Đóng gap "xác chết tính năng" nghiêm trọng nhất còn lại | `InstructorHome.jsx` |
| A5 | Thêm 2 link điều hướng cho `semester-setup`/`lecture-plan` (Sidebar hoặc thẻ trong Tổng quan) | Chỉ thêm 1-2 dòng JSX, không đụng logic | Mở khoá 1 tính năng thật, hoàn chỉnh, đang bị chôn | `App.jsx` hoặc `StudentHome.jsx` |
| A6 | Google login — ẩn/vô hiệu hoá nút rõ ràng thay vì để nút "trông hoạt động" nhưng luôn fail | Đổi điều kiện hiển thị, không cần build OAuth thật | Tránh trải nghiệm "trông như lỗi" khi giám khảo tự bấm thử | `LoginScreen.jsx` |
| A7 | Backend Lecturer dashboard — trả mảng completion **theo tuần thật** thay vì 1 số trung bình; frontend đọc từ đó, xoá `DASH_DATA` hardcode | Cần thêm field ở query (nhóm theo tuần) + sửa 1 chỗ đọc ở frontend — không đổi schema, chỉ đổi cách tổng hợp | **Phát hiện nghiêm trọng nhất toàn bộ audit** — ưu tiên cao nhất nếu phải chọn 1 việc duy nhất | `src/api/instructor.py` + `InstructorHome.jsx` |
| A8 | Risk badge (HIGH/MEDIUM/LOW) — chỉnh token màu cho theme sáng để đạt AA (đo lại bằng đúng công thức đã dùng trong audit) | Chỉ đổi giá trị hex trong `index.css`, không đổi component | Tiêu chí bắt buộc theo thang điểm BTC | `index.css` |
| A9 | Thêm tooltip/dòng chú thích cạnh badge risk giải thích "nguy cơ = có thể trễ kế hoạch tuần này, không phải dự đoán học lực" | 1 dòng JSX + 1 icon info | Đóng đúng yêu cầu compliance mục 14.1 | `InstructorHome.jsx`/`RiskCaseDrawer.jsx` |
| A10 | Dedupe 5 chỗ magic-string `"lecture_plan"` thành 1 hằng số + thêm 1 dòng thông báo UI khi phát hiện lecture-plan bị Gate2 đè | Không cần quyết định "gộp hay tách" — chỉ làm hành vi ẩn hiện trở nên minh bạch | Giảm rủi ro "silent fallback" tái diễn, không cần chờ quyết định kiến trúc | `lecture_plan_service.py` + 4 file khác |

**Ước tính:** A1-A6, A8-A10 mỗi việc nhỏ, có thể làm + test + commit riêng trong một buổi. A7 nặng nhất trong nhóm (cần sửa aggregation ở backend) — làm sau cùng trong nhóm A, hoặc làm đầu tiên nếu ưu tiên "sửa cái nghiêm trọng nhất trước" bất kể effort.

## Nhóm B — Chỉ cập nhật tài liệu, KHÔNG code (rủi ro gần như bằng 0, nên làm hết)

| # | Việc | Lý do không code |
|---|---|---|
| B1 | Cập nhật mục 6.3/6.4/6.5 của `PROJECT_CONTEXT.md` để liệt kê đủ 8 màn hình/tab chưa tài liệu hoá (planner/practice/companion riêng/semester-setup/lecture-plan/academic tab/2 tab instructor) | Đây là việc viết tài liệu cho tính năng ĐÃ THẬT, không phải build gì mới |
| B2 | Ghi rõ trong mục 6.1 rằng "Hoàn tất hồ sơ" hiện không hoạt động trong luồng thật (form tồn tại nhưng không thể truy cập) — cùng với lý do thật: profile/enrollment hiện được seed sẵn ở server, không phụ thuộc bước này | Sửa cho hoạt động thật cần thời gian test kỹ (đụng tới auth flow) — rủi ro cao đêm trước deadline nếu không có thời gian verify kỹ; ghi nhận trung thực an toàn hơn |
| B3 | Ghi nhận "Class picker Lecturer" và "trạng thái chưa đủ dữ liệu" (mục 14.1) là gap đã biết, chưa làm | Cần thêm khái niệm UI mới (không chỉ ráp dữ liệu có sẵn như A4) — effort cao hơn A4 dù cùng loại |
| B4 | Ghi nhận Admin "Cấu hình" tab thiếu UI (mục 6.5) kèm nhãn rõ ràng thay vì để trống như hiện tại | Có thể nâng lên nhóm A nếu A1-A9 xong sớm và còn thời gian — xem "Nếu còn dư thời gian" bên dưới |
| B5 | Cập nhật mục 6.2 làm rõ: banner demo-mode hiện chưa tồn tại; khung chat nổi hiện không xuất hiện sau đăng nhập (cho tới khi Nhóm C mục C1 được quyết định) | Tránh tài liệu hứa hẹn thứ chưa có |

## Nhóm C — Cần quyết định của người, KHÔNG tự chọn thay

**C1. "Cursus Assistant" — hợp nhất 3 hiện thân hay chấp nhận kiến trúc hiện tại + sửa tài liệu?**
- Lựa chọn 1 (đúng spec nhất, rủi ro cao nhất đêm trước deadline): làm widget nổi gọi thẳng pipeline QA thật, hiện trên mọi trang `/student/*`. Effort: trung bình-cao, cần test kỹ vì đụng tới component hiển thị nhiều nhất trong app.
- Lựa chọn 2 (an toàn, tốn 5 phút): sửa mục 6.2 cho khớp thực tế (nói rõ có 3 điểm chạm AI: widget FAQ nhanh ở trang công khai, panel ngữ cảnh ở Tổng quan, trang riêng theo môn) — không code gì.
- **Khuyến nghị của tôi (không phải quyết định thay bạn):** chọn Lựa chọn 2 cho 23/08, ghi Lựa chọn 1 vào backlog production-target (mục "Production target" đã có sẵn khuôn trong PROJECT_CONTEXT.md) — quá rủi ro để đại tu component hiển thị nhiều nhất app trong những giờ cuối.
- **✅ QUYẾT ĐỊNH 22/08, đêm — đảo ngược khuyến nghị trên:** bạn chọn **Lựa chọn 1**, cùng lúc với 4 việc còn lại của Nhóm C/backlog ("Đảo lại, làm luôn cả 5 việc tối nay vừa hoãn"). Đã triển khai: `CuriChatLauncher.jsx` gọi thật `POST /qa` (không còn kịch bản FAQ) khi `location.pathname` bắt đầu bằng `/student` — không đại tu component (giữ nguyên toàn bộ UI shell/animation/focus-trap đã có), chỉ thay nội dung trả lời + mở rộng route-guard, nên rủi ro thấp hơn dự đoán ban đầu. Không hợp nhất 3 hiện thân thành 1 component — `CuriContextPanel.jsx`/`CourseCompanionChat.jsx` giữ nguyên, vẫn là 3 điểm chạm khác nhau về code, nhưng khoảng cách trải nghiệm (FAQ giả vs pipeline thật) đã đóng. Chi tiết + bằng chứng: `docs/PROJECT_CONTEXT.md` mục 6.2, `docs/evidence/screenshots/2026-08-22_curi-assistant-consolidation/`.

**C2. Gate2 Plan vs `lecture_plan` — gộp làm 1 luồng hay giữ tách biệt vĩnh viễn?**
- Đã có bản vá an toàn tối thiểu ở A10 (minh bạch hoá, không cần quyết định ngay). Câu hỏi gộp-hay-tách có thể để sau 23/08 — không chặn demo vì cơ chế ưu tiên hiện tại (Gate2 luôn thắng) đã hoạt động đúng, chỉ thiếu minh bạch.

**C3. Audit log org-scoping — đã escalate từ trước (`PENDING_DECISIONS.md` #2), nhắc lại vì mức độ nghiêm trọng**
- Vẫn cần bạn chọn 1 trong 3 hướng đã ghi ở đó (thêm cột `organization_id` + migration + backfill là hướng đúng nhất nhưng có rủi ro schema đêm trước deadline). Không tự chọn thay ở đây.

**C4. Admin "Cấu hình" tab — có đáng làm trước 23/08 không?**
- Backend đã xong 100%, effort frontend thấp (tương tự AdminAiPolicy.jsx) — có thể xếp vào Nhóm A nếu bạn xác nhận còn thời gian sau khi xong A1-A10. Để bạn quyết định vì đây là "có thời gian dư hay không", không phải câu hỏi kỹ thuật.

---

## Thứ tự đề xuất nếu được duyệt (chờ quyết định C1-C4 trước khi vào Giai đoạn 3 chi tiết)

1. A1, A2 (đòn bẩy cao nhất, rẻ nhất — làm trước tiên)
2. A3, A5, A6 (độc lập nhau, rẻ, có thể làm song song)
3. A4 (cần A1 xong trước nếu bảng roster hiện role/label)
4. A7 (nặng nhất nhóm A, cần thời gian test riêng — bắt đầu sớm để có buffer)
5. A8, A9, A10 (polish cuối, làm nếu còn thời gian sau 1-4)
6. Toàn bộ Nhóm B (viết tài liệu, làm song song bất kỳ lúc nào, không phụ thuộc A)
7. C1-C4: chờ quyết định của bạn trước khi Giai đoạn 3 (Plan) chốt phạm vi chính xác, viết checkpoint cụ thể theo đúng kỷ luật đã dùng xuyên suốt dự án (commit riêng, pytest + ảnh chụp mỗi bước, không tự chạy sang phạm vi ngoài đã duyệt).

**Việc CHỦ ĐỘNG KHÔNG làm trước 23/08 (khuyến nghị, không phải đã quyết):** hợp nhất kiến trúc Cursus Assistant (C1 lựa chọn 1), gộp/tách Gate2 vs lecture_plan (C2), thêm class picker Lecturer đầy đủ, thêm trạng thái "chưa đủ dữ liệu" (mục 14.1), sửa mọi lỗi typography/spacing nhỏ lẻ mục 8.1 #16 — tất cả ghi vào Nhóm B hoặc production-target backlog, không lãng phí giờ còn lại cho việc thấp giá trị/rủi ro cao.

---

**Dừng lại ở đây theo đúng yêu cầu — chờ bạn duyệt Nhóm A (làm hay bớt việc gì), trả lời C1-C4, rồi mới sang Giai đoạn 3 (Plan chi tiết từng checkpoint).**
