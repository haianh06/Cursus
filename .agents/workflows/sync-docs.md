# Workflow: /sync-docs

> Đặt tại `.agents/workflows/sync-docs.md`. Chạy lệnh này mỗi khi docs/planning hoặc docs/guide có thay đổi (thêm file, đổi số thứ tự, lên version mới như v1→v2 từng xảy ra).

## Mục đích

Tránh lặp lại tình huống đã xảy ra: `ui-ux-brief.md` bị thay bởi `08-Cursus-UI-UX-Master-Spec.md` nhưng skill/rule vẫn trỏ vào bản cũ. Workflow này để `.agents/` luôn khớp thực tế thư mục `docs/`.

## Các bước

1. Quét cấu trúc thật của `docs/planning/` và `docs/guide/` (dùng lệnh `list dir` hoặc tương đương).
2. So sánh với bảng điều hướng hiện có trong `.agents/skills/cursus-product-docs/SKILL.md` và `.agents/skills/cursus-engineering-guide/SKILL.md`.
3. Nếu phát hiện:
   - File mới xuất hiện chưa có trong bảng → thêm dòng tương ứng, suy luận task nào nên trỏ tới file này dựa trên tên file/nội dung mở đầu.
   - File trong bảng nhưng đã không còn tồn tại (bị xoá/đổi tên) → đánh dấu, hỏi user có phải đã thay thế bằng file nào không trước khi tự xoá dòng.
   - Có version mới xuất hiện (ví dụ `v3` bên cạnh `v2`) → hỏi user: `v3` đã là bản chính thức thay thế `v2` chưa, trước khi đổi "nguồn hiện hành".
4. Cập nhật lại 2 file skill trên cho khớp thực tế.
5. **Đồng bộ riêng phần thiết kế:** mở `docs/archive/planning-v2/08-Cursus-UI-UX-Master-Spec.md` (hoặc file UI/UX master spec hiện hành theo bước 3), đối chiếu với `.agents/skills/cursus-design-system/SKILL.md`. Nếu có khác biệt (màu, font, component state, copy...), cập nhật lại `cursus-design-system/SKILL.md` theo đúng master spec — đây là nguồn UI/UX duy nhất, không tự bịa thêm ngoài spec trừ khi ghi rõ đó là gợi ý thêm của agent (không phải yêu cầu từ tài liệu).
6. Giữ nguyên phần cảnh báo AI-slop (gradient tím/mascot) trong `cursus-design-system/SKILL.md` nếu spec mới không nói rõ hướng khác — đây là lớp kiểm duyệt thẩm mỹ độc lập với spec chức năng.
7. Xuất Artifact tóm tắt: đã đổi gì, vì sao, có gì cần user xác nhận thêm không.
