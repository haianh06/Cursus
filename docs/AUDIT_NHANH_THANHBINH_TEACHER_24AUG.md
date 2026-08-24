# Đánh giá nhánh `thanhbinh` (Instructor Role) & Kế hoạch Tích hợp

> Viết bởi Antigravity Agent - 24/08/2026

## 1. Tổng quan các tính năng (Features)
Nhánh `thanhbinh` đã xây dựng một bộ tính năng khổng lồ cho vai trò Giảng viên (Instructor), bao gồm:
1. **Dashboard & Báo cáo:** F4 (Dashboard), F9 (Bộ lọc lớp), F12 (Xuất CSV), B3 (So sánh các lớp).
2. **Quản lý rủi ro (Risk Management):** F5 (Chi tiết 1 risk), F10 (Lịch sử can thiệp), B1 (Can thiệp hàng loạt - Bulk Intervention).
3. **Student 360 (Instructor View):** A1 (Hồ sơ sinh viên), A3 (Ghi chú riêng của GV).
4. **Quiz Manager (Mới):** Thay thế hoàn toàn tính năng Practice cũ bằng hệ thống tạo và quản lý Quiz mới (với tính năng Publish/Unpublish, Reorder, Auto-generate câu hỏi).
5. **Class Activity:** Ghi nhận và điều chỉnh hoạt động trên lớp (Live Class Activity Window - F17).
6. **Guardrail Reviews:** Duyệt các yêu cầu vượt rào (bypass) từ sinh viên.
7. **Instructor Digest:** Báo cáo tổng hợp gửi qua email/UI.

## 2. Đánh giá UI/UX
- **Điểm mạnh:**
  - Thiết kế UI cực kỳ chi tiết, có phân chia component rõ ràng (`InstructorHome`, `ClassComparisonPanel`, `InstructorRiskPage`, `InstructorStudentProfile`, `InstructorQuizManager`).
  - Xử lý Loading/Error states rất tốt (skeleton loading, thông báo lỗi có nút Retry).
  - Phân trang, bộ lọc và các thao tác Bulk Action (chọn nhiều row) được thiết kế trực quan.
- **Điểm yếu / Cần cải thiện:**
  - Vẫn còn một số text hardcode (như `classCompletionRate` luôn trả về "76%" trên backend).
  - Cấu trúc thư mục component có thể gộp chung lại cho gọn nếu dùng React Router thay vì render trực tiếp.

## 3. Đánh giá Backend & Bảo mật (Các lỗi nghiêm trọng cần sửa khi rebuild)
Dù logic nghiệp vụ rất đầy đủ, nhánh `thanhbinh` mắc phải một số lỗi vi phạm quy tắc hệ thống tương tự nhánh `chung`:
1. **Thiếu Audit-trước-trả-sau:** API `GET /students/{student_id}/profile` trả về thông tin nhạy cảm của sinh viên nhưng KHÔNG sử dụng `AuditService.log_event` để ghi log truy cập. Bắt buộc phải bọc bằng transaction: log thành công -> trả data.
2. **Hardcode số liệu:** API `/instructor/dashboard` trả về `classCompletionRate: "76%"` và `onTimeSubmissions: "68%"`. Không được phép hardcode, nếu chưa tính được thì trả `null` hoặc tính toán thực tế.
3. **Org-scoping:** API Bulk Intervention (`/risks/bulk-intervention`) có kiểm tra quyền sở hữu nhưng chưa chặt chẽ về mặt transaction (lưu nhiều case nhưng không bọc chung 1 DB transaction, có thể sinh lỗi partial commit).
4. **Thay thế Practice bằng Quiz:** Nhánh này đã xóa `practice_generator.py` và `test_practice_sets.py` để thay bằng `quiz_service.py`. Khi merge, ta cần phải cẩn thận giữ lại các file test cũ nếu chúng thuộc module khác, hoặc cập nhật toàn bộ test suite để tương thích với Quiz Manager.

## 4. Kế hoạch Rebuild (Port sang `haidang2425`)
Không git merge trực tiếp để tránh hỏng kiến trúc (giống hệt cách xử lý nhánh `chung`). Ta sẽ port code bằng cách:
1. **Dữ liệu & Migration:** Sao chép các file migration mới (từ `20260827_...` đến `20260901_...`) vào nhánh `haidang2425` và chạy migrate.
2. **Backend Services & API:** Tạo lại các router trong `src/api/instructor.py`, BẮT BUỘC áp dụng `AuditService.log_event` cho các API đọc dữ liệu nhạy cảm (như hồ sơ sinh viên).
3. **Frontend Components:** Chuyển các component từ `thanhbinh_worktree/frontend/src/components/instructor/` sang, sử dụng chuẩn UI mới nhất (`ConfirmDialog` thay vì `window.confirm`). Tích hợp chúng vào `react-router-dom` (ví dụ: `/instructor/dashboard`, `/instructor/quizzes`, `/instructor/risks`).
4. **Kiểm thử:** Chạy lại toàn bộ bộ test `pytest` để đảm bảo hệ thống Auth và Admin không bị vỡ bởi các thay đổi của Instructor.
