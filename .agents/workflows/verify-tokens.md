# Workflow: /verify-tokens

> Đặt tại `.agents/workflows/verify-tokens.md`. Chạy lệnh này SAU MỖI lần build/sửa UI, trước khi báo hoàn thành — không tin vào "nhìn thấy ổn", phải grep thật vào code.

## Vì sao cần workflow này

Đã từng xảy ra: agent build ra UI tím-indigo + mascot robot dù spec chính thức (`08-Cursus-UI-UX-Master-Spec.md`) đã chốt bảng "Ink & Citrine" (`#B7791F` làm accent, nền giấy ấm `#FAF8F3`, không mascot). Tự đánh giá bằng mắt không đủ tin cậy — cần bước kiểm tra máy móc.

## Danh sách token ĐƯỢC PHÉP (allowlist — mọi hex khác đều là lỗi)

```
#15181C #5B5647 #948E7C #FAF8F3 #FFFFFF #E6E2D8 #D6D1C2
#B7791F #9C6414 #F7ECD6 #2F6B3A #E6EFE2 #9B3B34 #F6E6E4
```
(cộng các biến thể opacity của các mã trên, ví dụ `#B7791F1A`, và các mã xám trung tính chuẩn Tailwind như `#F9FAFB`...`#111827` cho neutral scale nếu cần).

## Các bước

1. Grep toàn bộ source code UI (`.tsx`, `.jsx`, `.css`, `.ts` có style, config Tailwind) tìm mọi mã hex dạng `#[0-9A-Fa-f]{3,8}`.
2. Với mỗi mã tìm được, đối chiếu allowlist ở trên. Đặc biệt cảnh giác các mã thuộc dải tím/indigo/violet kinh điển của AI-slop (`#6366F1`, `#4F46E5`, `#7C3AED`, `#8B5CF6`, hoặc bất kỳ mã nào không có trong allowlist) — đây chính là lỗi vừa xảy ra.
3. Liệt kê từng vi phạm: file, dòng, mã hex sai, mã đúng nên thay (tra theo vai trò — ví dụ nếu đang dùng làm nút CTA chính → thay bằng `--accent #B7791F`).
4. Kiểm tra riêng: có còn ảnh/SVG mascot robot 3D nào được import/hiển thị không — nếu có, xoá hoặc thay bằng hướng đã thống nhất ở `cursus-design-system/SKILL.md` (line-art tối giản hoặc data-driven hero, không mascot bóng bẩy).
5. Kiểm tra font: heading có đang dùng Source Serif 4 chưa (không phải font sans mặc định)? Số liệu/citation/mã môn có đang dùng IBM Plex Mono chưa?
6. Tự sửa toàn bộ vi phạm tìm được.
7. Chạy lại bước 1-2 một lần nữa để xác nhận sạch hoàn toàn (0 hex ngoài allowlist).
8. Xuất Artifact: bảng trước/sau, số lượng vi phạm đã sửa, ảnh chụp màn hình sau khi sửa để đối chiếu trực quan với mô tả "Ink & Citrine" ở `08`.

Nếu bước 7 vẫn còn vi phạm sau 2 vòng tự sửa, DỪNG và báo cáo cụ thể cho user thay vì tiếp tục đoán.
