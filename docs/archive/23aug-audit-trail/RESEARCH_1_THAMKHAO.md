# RESEARCH 1 — Tham khảo sản phẩm thật cho từng nhóm phát hiện (Giai đoạn 1)

**Phương pháp:** dựa trên kiến thức đã có về UX pattern ổn định, lâu năm của các sản phẩm được liệt kê (không phải tra cứu ảnh chụp mới) — mọi pattern nêu dưới đây là hành vi công khai, đã ổn định nhiều năm của các sản phẩm này, không phải chi tiết dễ đổi (giá, số liệu, UI mới ra mắt). Với mỗi nhóm phát hiện ở `docs/AUDIT_0_HIENTRANG.md` mục 8.1, chọn 2-3 sản phẩm tham khảo cụ thể + pattern áp dụng được, để Giai đoạn 2 (Evaluation) có cơ sở ra quyết định thay vì tự nghĩ ra giải pháp không có căn cứ.

---

## 1. "Cursus Assistant" — hợp nhất 3 hiện thân thành 1 trải nghiệm nhất quán (audit #2)

**Vấn đề cốt lõi cần giải:** widget nổi (visible mọi lúc) và pipeline có backend thật (trích dẫn/guardrail thật) hiện là 2 thứ tách rời — cần 1 trong 2 hướng: (a) làm widget nổi gọi thẳng pipeline thật, hoặc (b) chấp nhận kiến trúc nhúng-theo-ngữ-cảnh nhưng làm nó xuất hiện nhất quán hơn.

- **Intercom / Crisp (chat widget cho SaaS B2B)** — pattern chuẩn ngành: 1 widget nổi DUY NHẤT, luôn cùng 1 component, nhưng **nội dung/khả năng đổi theo ngữ cảnh trang** (ví dụ trên trang billing thì gợi ý câu hỏi về billing) chứ không phải đổi HẲN sang 1 component khác. Áp dụng: giữ `CuriChatLauncher` làm vỏ nổi duy nhất, nhưng thay nội dung kịch bản cứng bằng lời gọi thật tới cùng pipeline `CuriContextPanel`/`CourseCompanionChat` đang dùng (`QaAnswerService`), truyền `subjectCode` theo route hiện tại thay vì cố định.
- **Notion AI (Q&A trong sidebar)** — pattern: 1 điểm vào chat duy nhất, nhớ ngữ cảnh trang đang mở, không có "bản đầy đủ" và "bản rút gọn" tách biệt như Cursus hiện tại (context panel vs trang riêng vs widget).
- **Linear (Command palette + AI)** — pattern liên quan: widget/panel AI chỉ có 1 hiện thân, xuất hiện nhất quán ở mọi màn hình ứng dụng qua phím tắt/nút cố định, không biến mất tuỳ route.

**Khuyến nghị nghiên cứu → Giai đoạn 2:** quyết định giữa (a) hợp nhất kỹ thuật (nhiều việc, rủi ro cao hơn, đúng lời hứa spec nhất) và (b) sửa lại mô tả spec 6.2 cho khớp kiến trúc nhúng-theo-trang hiện tại (ít việc, an toàn hơn về thời gian, nhưng phải chấp nhận "không nổi mọi lúc" không còn là true statement khi demo).

## 2. Bảng số liệu Analytics/biểu đồ (Admin Analytics, Lecturer weekly chart) — audit #1, #4.3

**Vấn đề cốt lõi:** biểu đồ Lecturer đang bịa số; biểu đồ Analytics Admin là CSS thuần không tương tác.

- **Stripe Dashboard** — pattern: mọi biểu đồ trend đều có (1) trạng thái rỗng rõ ràng khi chưa đủ dữ liệu ("Not enough data yet" thay vì vẽ đường phẳng/giả), (2) tooltip hover hiện giá trị chính xác từng điểm, (3) không bao giờ nội suy/bịa điểm thiếu — nếu thiếu dữ liệu, biểu đồ có khoảng trống rõ ràng chứ không nối liền giả tạo.
- **Mixpanel (trend/insight charts)** — pattern: mỗi cảnh báo xu hướng (tăng/giảm) luôn kèm % thay đổi cụ thể + khoảng thời gian so sánh ("giảm 12% so với tuần trước"), không bao giờ hiện cảnh báo nhị phân (có/không) mà không có con số đứng sau.
- **Retool (admin app builder, biểu đồ nhúng)** — pattern liên quan tới việc component hoá: Retool khuyến khích bind chart trực tiếp vào query thật, có chế độ "preview với dữ liệu mẫu" TÁCH BIỆT rõ ràng khỏi chế độ live — không bao giờ để lẫn giữa 2 chế độ như `DASH_DATA` hiện tại (không rõ là "dữ liệu mẫu lúc dev" hay "dữ liệu thật").

**Khuyến nghị cụ thể, không cần nghiên cứu thêm (đây là bug, không phải thiếu design):** việc đầu tiên và bắt buộc trước bất kỳ polish nào — **backend phải trả về mảng theo tuần thật** (hiện chỉ có 1 số trung bình), sau đó frontend đọc từ đó thay vì `DASH_DATA`. Đây là sửa lỗi (P0-class), phần "tham khảo Stripe/Mixpanel" chỉ áp dụng cho bước polish SAU KHI có dữ liệu thật (tooltip, xử lý thiếu dữ liệu).

## 3. Danh sách người dùng/sinh viên + tìm kiếm (Admin Users đã tốt; Lecturer roster đang thiếu) — audit #4

- **Linear (Members/Teams settings)** — bảng người dùng: cột cố định (tên, vai trò, trạng thái, hoạt động gần nhất), tìm kiếm tức thời (debounce ngắn, không cần bấm nút), có thể sort theo cột, hành động (khoá/đổi vai trò) nằm ở cột cuối dạng menu 3 chấm — Admin Users hiện tại đã khá gần pattern này (đã ✅ ở audit).
- **Notion (Workspace members)** — pattern trạng thái rủi ro/hoạt động: dùng badge màu nhỏ cạnh tên thay vì cột riêng, giúp bảng gọn hơn khi có nhiều cột dữ liệu (hợp với Lecturer roster cần hiện cả completion% + risk level + action).
- **GitHub (Org People tab)** — pattern filter kết hợp search: ô tìm kiếm + dropdown lọc phụ (ví dụ lọc theo team/role) đặt cùng hàng, ngay trên bảng — áp dụng tốt cho Lecturer roster nếu sau này cần lọc theo mức rủi ro ngoài tìm theo tên.

**Khuyến nghị:** Lecturer roster đã có sẵn dữ liệu (`classInfo.roster`) và bản dịch — đây là việc RÁP UI, không phải thiết kế từ đầu. Tái dùng cấu trúc bảng đã có ở `AdminUsers.jsx` (đã ✅ audit) làm khung, không cần thiết kế bảng mới.

## 4. Audit log — audit #5 (org-scoping là quyết định schema, không phải UX; phần UX tham khảo cho hiển thị)

- **GitHub organization audit log** — pattern hiển thị: mỗi dòng có actor + action + target + timestamp trên 1 hàng, click để mở rộng xem raw JSON — đúng pattern `AdminAudit.jsx` hiện tại đã làm.
- **Stripe Events (Dashboard → Developers → Events)** — pattern lọc: filter theo loại sự kiện bằng dropdown có autocomplete (không phải ô nhập tự do thô) — Cursus hiện dùng ô nhập tự do vì có >20 loại sự kiện, đây là lựa chọn hợp lý đã ghi trong audit (tránh danh sách cứng lỗi thời), giữ nguyên.
- **Auth0 Logs** — pattern liên quan trực tiếp tới gap tổ chức: Auth0 tenant logs **mặc định scope theo tenant đang đăng nhập**, không có cách nào xem tenant khác qua UI — đây chính là hành vi ĐÚNG mà Cursus's Audit log cần đạt, xác nhận lại rằng gap hiện tại (không org-scope) là sai lệch so với chuẩn ngành, không phải "chưa polish".

**Lưu ý quan trọng:** phần org-scoping là quyết định SCHEMA (thêm cột `organization_id`, migration, backfill) — đã escalate đúng chỗ ở `PENDING_DECISIONS.md` #2, Giai đoạn Research này không đề xuất tự quyết định thay.

## 5. Policy editors (Risk Policy, Guardrail rules) — đã tốt, tham khảo cho phần "lý do đổi" còn thiếu

- **Vercel (Environment Variables / Project Settings)** — pattern thay đổi cấu hình có ảnh hưởng rộng: mọi thay đổi quan trọng đều có changeset preview trước khi "Deploy" (áp dụng), lịch sử đổi có thể rollback — đúng pattern `AdminRiskPolicy.jsx` đã làm.
- **GitHub (branch protection rules)** — bật/tắt rule không bắt buộc lý do, nhưng MỌI thay đổi đều xuất hiện trong audit log tự động kèm actor — đây là pattern tối thiểu Cursus đã đạt cho Guardrail rule toggle (dù thiếu ô "lý do" tường minh, audit log vẫn ghi lại ai bật/tắt).
- **Khuyến nghị cho gap "thiếu ô lý do đổi guardrail rule":** đây là việc backend nhỏ (thêm field `reason` optional vào `AdminGuardrailRuleUpdateRequest`), không cần nghiên cứu thêm — độ ưu tiên thấp so với các gap khác vì audit log đã ghi nhận hành động, chỉ thiếu lý do tường minh.

## 6. i18n kiến trúc (sidebar hardcode, ternary thay vì `t()`) — audit #11, xuyên suốt mục 2-7

**Đây không phải vấn đề thiết kế, mà là vấn đề kỷ luật kỹ thuật** — tham khảo ngắn gọn:
- **next-intl / react-i18next (chuẩn ngành cho React)** — nguyên tắc cốt lõi: KHÔNG BAO GIỜ literal string trong JSX, luôn qua hàm `t(key)`; lint rule (`eslint-plugin-i18next`) có thể tự động phát hiện string tiếng Việt có dấu hardcode trong JSX — đây chính là công cụ có thể áp dụng ngay để tránh tái diễn gap này (34+ chuỗi hardcode tìm được xuyên suốt audit).
- **Khuyến nghị cụ thể:** việc sửa `constants/roles.js` để có bản tiếng Anh là **gốc rễ của ít nhất 4 phát hiện riêng lẻ** (sidebar, UnauthorizedPage, AcceptInviteScreen, theme toggle label) — đây là điểm đòn bẩy cao nhất trong toàn bộ audit: 1 file sửa, nhiều gap tự động hết.

## 7. Mock LMS UI — đã là quyết định phạm vi đúng, tham khảo chỉ để xác nhận, không phải để mở rộng ngay

- **Canvas LMS / Google Classroom** — cả 2 đều có UI đầy đủ, phong phú hơn nhiều so với Mock LMS hiện tại (Jinja2 tối giản) — nhưng đây **không phải benchmark phù hợp** vì mục 6.6 đã chốt rõ Mock LMS chỉ cần "chứng minh 2 hệ thống thật nói chuyện qua API", không phải cạnh tranh trải nghiệm với LMS thật. Giữ nguyên tối giản là quyết định đúng, không cần đầu tư thêm trừ khi Giai đoạn 2 kết luận khác.

## 8. Onboarding, Google login, AuthLayout heading — đây là BUG, không phải thiếu nghiên cứu UX

Cả 3 phát hiện này (form chết, login luôn fail, heading ẩn dưới 1024px) đều là lỗi logic/code cụ thể có thể sửa trực tiếp mà không cần tham khảo sản phẩm ngoài — không tốn thời gian Giai đoạn 1 cho nhóm này, chuyển thẳng sang Giai đoạn 2 để xếp độ ưu tiên sửa.

---

## Tổng hợp đòn bẩy cao nhất (ít việc, nhiều gap được giải quyết cùng lúc)

1. **`constants/roles.js` thêm bản tiếng Anh** → tự động sửa ít nhất 4 gap i18n riêng lẻ.
2. **`AuthLayout.jsx` sửa cách ẩn h1** → tự động sửa heading-hierarchy cho ít nhất 5 màn hình auth.
3. **Backend Lecturer dashboard trả mảng completion theo tuần thật** (thay vì 1 số trung bình) → mở khoá việc xoá `DASH_DATA` hardcode, đây là gap nghiêm trọng nhất nên đứng đầu danh sách Giai đoạn 3.
4. **Ráp `classInfo.roster` đã có sẵn vào 1 bảng UI** (tái dùng cấu trúc `AdminUsers.jsx`) → giải quyết gap "danh sách sinh viên" gần như miễn phí vì dữ liệu + bản dịch đã có sẵn.
