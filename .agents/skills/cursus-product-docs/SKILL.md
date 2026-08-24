---
name: cursus-product-docs
description: Dùng skill này khi task liên quan đến phạm vi sản phẩm, tính năng, yêu cầu nghiệp vụ (FR/NFR), lịch trình mốc, hạ tầng/Supabase, hoặc thiết kế UI/UX của Cursus. Kích hoạt khi thấy từ khoá "tính năng mới", "PRD", "SRS", "mốc", "Supabase", "hạ tầng", "UI", "màn hình", "thiết kế", "đối thủ", "pitch", "checklist production".
---

# Bản đồ tài liệu sản phẩm Cursus (docs/planning/v2)

## Nguồn duy nhất được coi là hiện hành

`docs/archive/planning-v2/` là bộ tài liệu chính thức. Đọc đúng file theo loại task, KHÔNG đọc tràn lan cả 9 file mỗi lần — tốn context và dễ lẫn thông tin cũ/mới.

| Task đang làm | Đọc file nào trước |
|---|---|
| Tổng quan lần đầu vào dự án | `@docs/archive/planning-v2/00-Cursus-Moc1-Playbook.md` |
| Thêm/sửa 1 tính năng — cần hiểu phạm vi, persona | `@docs/archive/planning-v2/01-Cursus-PRD.md` |
| Thêm/sửa 1 tính năng — cần chi tiết FR/NFR | `@docs/archive/planning-v2/02-Cursus-SRS.md` |
| Câu hỏi về timeline, mốc nào làm gì | `@docs/archive/planning-v2/03-Cursus-Execution-Plan.md` |
| Không chắc 1 thuật ngữ nghĩa là gì | `@docs/archive/planning-v2/04-Cursus-Terminology.md` |
| Viết nội dung pitch, so sánh đối thủ | `@docs/archive/planning-v2/05-Cursus-Competitive-Analysis.md` |
| Quyết định liên quan hạ tầng, DB, quy mô scale | `@docs/archive/planning-v2/06-Cursus-Ha-tang-Supabase-Scale2000.md` |
| Chuẩn bị/rà soát cho Mốc 3, không biết mở file nào | `@docs/archive/planning-v2/07-Cursus-Production-Readiness-Checklist.md` |
| **BẤT KỲ task thiết kế/code UI nào** | `@docs/archive/planning-v2/08-Cursus-UI-UX-Master-Spec.md` — đây là nguồn UI/UX DUY NHẤT, tự đủ, không cần đọc thêm |

## TUYỆT ĐỐI không dùng làm nguồn hiện hành

- `docs/planning/v1/**` — bản nháp cũ, chỉ tham khảo lịch sử nếu user CHỦ ĐỘNG yêu cầu so sánh, không tự ý lấy thông tin từ đây để code.
- `docs/archive/planning-v2/ui-ux-brief.md` — bản nháp trước file `08`, không còn cập nhật. Nếu vô tình thấy file này trong context, ưu tiên `08` nếu có mâu thuẫn.

## Dữ liệu mẫu/seed

- `docs/planning/v2/data/*.json` — dùng làm dữ liệu thật khi code demo/test (không tự bịa dữ liệu khác nếu đã có sẵn ở đây).
- `docs/planning/v2/scripts/*.py` — script sinh/parse dữ liệu ở trên, chỉ động vào khi task liên quan trực tiếp tới việc tạo/parse seed data.

## Khi 2 nguồn mâu thuẫn nhau

Thứ tự ưu tiên khi có xung đột thông tin: `08` (UI/UX) > `02` (SRS) > `01` (PRD) > các file còn lại. Nếu mâu thuẫn không tự giải quyết được logic, dừng lại và hỏi user thay vì tự chọn 1 bên.
