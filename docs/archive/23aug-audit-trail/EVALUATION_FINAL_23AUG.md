# Evaluation & Kết luận — Giai đoạn 2 (23/08/2026)

> So sánh `AUDIT_FINAL_23AUG.md` (hiện trạng) với `RESEARCH_FINAL_23AUG.md` (nguyên tắc từ sản phẩm thật), đánh giá theo 4 tiêu chí: (1) UX/luồng nghiệp vụ, (2) thiết kế/UI chuyên nghiệp, (3) SEO/Accessibility, (4) production-readiness (data thật). Kết luận: **GIỮ NGUYÊN** / **CẦN SỬA** (mô tả cụ thể) / **CẦN XÂY MỚI**.
>
> **Nguyên tắc chọn phạm vi sửa cho phiên này (quan trọng, quyết định trước khi lập Giai đoạn 3):** thời gian còn lại tới 23/08 rất ít. Ưu tiên sửa những gì (a) rủi ro thật cho demo/chấm điểm, (b) sửa nhanh/cơ học/ít rủi ro phá vỡ luồng đang chạy đúng, và (c) đúng north-star flow trước. KHÔNG đụng vào bất kỳ chỗ nào đang "GIỮ NGUYÊN" chỉ để "làm đẹp thêm".

---

## A. Khu vực Sinh viên

| Màn hình | (1) UX | (2) UI | (3) A11y/SEO | (4) Production-ready | Kết luận |
|---|---|---|---|---|---|
| Tổng quan | Đạt | Đạt | Đạt | Đạt (data thật) | **GIỮ NGUYÊN** |
| Phản tư | Đạt | Đạt | Đạt | Đạt | **GIỮ NGUYÊN** — nhưng cập nhật riêng `PROJECT_CONTEXT.md` mục 6.3 (tài liệu lỗi thời, không phải sửa code) |
| Cài đặt | Đạt | Đạt | Đạt | Đạt | **GIỮ NGUYÊN** |
| Lập kế hoạch tuần | Đạt | Đạt | Đạt | Đạt | **GIỮ NGUYÊN** |
| Luyện tập | Đạt phần lớn | Đạt | Thiếu `aria-live` cho kết quả đúng/sai | Đạt | **CẦN SỬA (nhỏ)** — thêm `aria-live="polite"` cho vùng kết quả MCQ; cân nhắc thêm confirm nhẹ khi "Tạo lại bộ luyện tập" (nếu còn giờ, không bắt buộc) |
| Trợ lý theo môn | Đạt | Đạt | **Không đạt** — không dùng được bàn phím | Đạt | **CẦN SỬA (ưu tiên cao)** — đổi `div onClick` sang phần tử focusable đúng chuẩn (Gap 4); thêm confirm nhẹ cho xoá hội thoại |
| Thiết lập học kỳ | Đạt | Đạt | **Không đạt** — label/aria thiếu nhiều chỗ | Đạt | **CẦN SỬA (ưu tiên cao)** — gắn `htmlFor`/`id`, thêm `aria-label` ô lịch tuần (Gap 5) |
| Kế hoạch theo lịch học | Đạt | Đạt | Không đạt (cùng lỗi label) | Đạt | **CẦN SỬA (ưu tiên trung bình)** — cùng fix Gap 5 |

---

## B. Khu vực Giảng viên

| Màn hình/Tab | (1) UX | (2) UI | (3) A11y/SEO | (4) Production-ready | Kết luận |
|---|---|---|---|---|---|
| Tab Tổng quan (số liệu + alert + roster) | **Không đạt** — hành động can thiệp không confirm | Đạt | Thiếu label input search (nhỏ) | Đạt | **CẦN SỬA (ưu tiên cao)** — thêm confirm nhẹ cho "Đánh dấu đã can thiệp" (Gap 1 nhóm B); thêm `aria-label` cho input search |
| `RiskCaseDrawer.jsx` | **Không đạt** — nút can thiệp footer cũng không confirm | Đạt | **Đạt xuất sắc** (mẫu mực) | Đạt | **CẦN SỬA (nhỏ)** — chỉ thêm confirm, giữ nguyên toàn bộ phần accessibility đã làm đúng, không đụng vào |
| Tab Nhật ký buổi học | Đạt | Đạt | Đạt (label OK) nhưng thiếu Retry/dịch đồng bộ | Đạt | **CẦN SỬA (thấp, không bắt buộc)** — đồng bộ `t()`/Retry nếu còn thời gian, không chặn demo |
| Tab Duyệt luyện tập | **Không đạt** — publish không confirm | Đạt | **Không đạt** — form nhiều trường thiếu label | Đạt | **CẦN SỬA (ưu tiên cao)** — confirm cho Publish (Gap 1 nhóm A vì ảnh hưởng trực tiếp SV), gắn label cho form (Gap 5) |
| Hàng đợi guardrail-review | **Không đạt** — quyết định không confirm | Đạt | Thiếu `aria-label`/blockquote (nhỏ) | Đạt | **CẦN SỬA (ưu tiên cao)** — confirm/lý do bắt buộc khi "Mở chặn" (Gap 1, academic-integrity) |

---

## C. Khu vực Admin

| Tab | (1) UX | (2) UI | (3) A11y/SEO | (4) Production-ready | Kết luận |
|---|---|---|---|---|---|
| Curriculum | Đạt (trừ xoá môn 2-nút-cạnh-nhau) | Đạt | **Không đạt** — h1 tĩnh + tab ARIA thiếu (ảnh hưởng toàn khung `AdminConsole.jsx`) | Đạt | **CẦN SỬA (ưu tiên cao nhất — ảnh hưởng cả 7 tab)** — Gap 2 |
| Người dùng/Lời mời | Đạt | Đạt | Thiếu `scope="col"` (chung với mọi tab) | Đạt | **CẦN SỬA (ưu tiên trung bình)** — Gap 3, làm 1 lượt toàn bộ Admin |
| Analytics | Đạt | Đạt | Đạt (đã có `sr-only h2`) | Đạt | **GIỮ NGUYÊN** (trừ `scope="col"` chung) |
| Chính sách AI | **Không đạt** — Restore defaults không confirm | Đạt | Thiếu `aria-describedby` cho validate message (nhỏ) | Đạt | **CẦN SỬA (ưu tiên trung bình)** — confirm cho Restore defaults (Gap 1 nhóm A) |
| Audit log | Đạt | Đạt | Đạt (đã có `sr-only label`) | Đạt | **GIỮ NGUYÊN** (trừ `scope="col"` chung) |
| Cấu hình | Đạt | Đạt | Đạt | Đạt | **GIỮ NGUYÊN**, cân nhắc thêm confirm cho toggle demo mode nếu còn giờ (không bắt buộc — mức rủi ro thấp) |
| Học kỳ & Lịch thi | **Không đạt** — xoá lịch thi không confirm, lưu học kỳ không cảnh báo ghi đè | Đạt | Thiếu `scope="col"` | Đạt | **CẦN SỬA (ưu tiên cao)** — confirm cho xoá (Gap 1 nhóm A), thêm cảnh báo ghi đè trước khi lưu |

**Quyết định riêng cho Curriculum (h1/tab ARIA):** đây là 1 sửa ở tầng khung `AdminConsole.jsx` áp dụng cho toàn bộ 7 tab cùng lúc — xếp priority cao nhất trong Admin vì 1 lần sửa giải quyết được gap lặp lại ở mọi tab, hiệu quả effort/impact tốt nhất.

---

## D. Mock LMS + Public/Shared

| Màn hình | (1) UX | (2) UI | (3) A11y/SEO | (4) Production-ready | Kết luận |
|---|---|---|---|---|---|
| Mock LMS `/courses` | Đạt | Đạt | Đạt (nhỏ, chấp nhận được — app phụ trợ) | Đạt | **GIỮ NGUYÊN** |
| Mock LMS `/courses/<code>` sửa deadline | **Không đạt** — không confirm/preview | Đạt | Thiếu label input date (nhỏ, app phụ trợ) | Đạt | **CẦN SỬA (ưu tiên cao — ảnh hưởng source precedence #1)** — Gap 7 |
| Trang chủ/Auth/404/403 | Đạt | Đạt | Đạt | Đạt | **GIỮ NGUYÊN** |
| `OnboardingScreen.jsx` | N/A (không ai thấy) | N/A | N/A | Bug đã biết | **GIỮ NGUYÊN — quyết định cũ không sửa vẫn hợp lý**, không mở lại trước deadline |
| Khung chung (Sidebar/Topbar) | Đạt (trừ search disabled, đã biết) | Đạt | Đạt | Đạt | **GIỮ NGUYÊN** |
| `CuriChatLauncher.jsx` | Thiếu đóng click-ra-ngoài | Đạt | Đạt (ARIA nút mở/đóng tốt) | Đạt | **CẦN SỬA (thấp, không bắt buộc)** — thêm click-outside handler nếu còn giờ |
| Design token (`index.css`) | — | Đạt | Đạt | — | **GIỮ NGUYÊN** |

---

## Tổng hợp ưu tiên sửa (đưa sang Giai đoạn 3 lập plan)

**Ưu tiên CAO (rủi ro thật/ảnh hưởng nhiều màn hình/lõi north-star flow):**
1. Admin: h1 động theo tab + ARIA tab semantics (`AdminConsole.jsx`) — ảnh hưởng 7 tab.
2. Lecturer: confirm cho "Đánh dấu đã can thiệp" (AlertCard + RiskCaseDrawer footer).
3. Lecturer: confirm cho "Xuất bản" bộ luyện tập.
4. Lecturer: confirm/lý do bắt buộc cho "Mở chặn" guardrail review.
5. Admin: confirm cho xoá lịch thi + cảnh báo ghi đè khi lưu học kỳ.
6. Student: sửa keyboard accessibility cho `CourseCompanionChat.jsx` (chọn hội thoại).
7. Student: gắn label/aria cho `SemesterSetupWizard.jsx` (label-input + ô lịch tuần).
8. Mock LMS: confirm/preview cho form sửa deadline.

**Ưu tiên TRUNG BÌNH:**
9. Admin: `scope="col"` toàn bộ bảng (làm 1 lượt).
10. Admin: confirm cho "Restore defaults" Guardrail.
11. Student: label/aria cho `LecturePlanPanel.jsx`.

**Ưu tiên THẤP (chỉ làm nếu còn dư thời gian sau các mục trên):**
12. Student Luyện tập: `aria-live` cho kết quả MCQ.
13. `CuriChatLauncher.jsx`: đóng bằng click-ra-ngoài.
14. Lecturer: đồng bộ `t()`/Retry cho 2 tab mới.
15. Mock LMS: label cho input date.

**Tài liệu (không phải code):**
16. Cập nhật `PROJECT_CONTEXT.md` mục 6.3 — tính năng Reflect band-question đã xong, không còn "🔜 chưa làm".

**KHÔNG đụng (đã GIỮ NGUYÊN, đạt chuẩn):** toàn bộ phần còn lại — đặc biệt không refactor `RiskCaseDrawer.jsx` (đã mẫu mực), không mở lại `OnboardingScreen.jsx` (quyết định cũ), không đổi kiến trúc Admin Console thành nhiều trang riêng (mục 6.5 đã cho phép giữ 1 trang nhiều tab).

**Không có quyết định kiến trúc lớn nào phát sinh ở Giai đoạn 0-2 này** — mọi CẦN SỬA đều là fix cơ học (ARIA attribute, confirm dialog dùng token có sẵn, label-id liên kết), không cần schema/kiến trúc mới, không cần ghi vào `PENDING_DECISIONS.md`.

---

**DỪNG TẠI ĐÂY — cổng chặn 1. Chờ duyệt trước khi lập Giai đoạn 3 (plan thi công chi tiết).**
