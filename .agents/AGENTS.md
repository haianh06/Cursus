# AGENTS.md — Hiến pháp dự án Cursus (v2)

> File này Antigravity đọc ở ĐẦU MỖI phiên làm việc. Mọi task, dù nhỏ, đều phải tuân theo đây.

## 0.1 Bản đồ tài liệu dự án — đọc mục này trước tiên

Dự án có 2 nguồn tài liệu tách biệt, KHÔNG trộn lẫn:

- **`docs/archive/planning-v2/`** — spec sản phẩm chính thức (PRD, SRS, UI/UX master spec, hạ tầng...). Nguồn hiện hành DUY NHẤT. Điều hướng chi tiết ở skill `.agents/skills/cursus-product-docs/SKILL.md` (tự load khi task liên quan tính năng/UI/hạ tầng).
- **`docs/guide/`** — kiến thức kỹ thuật/kiến trúc chung (architecture, patterns, anti-patterns, langgraph, testing, devops...). Tham khảo để nâng chất lượng code, KHÔNG được ghi đè quyết định đã chốt ở `docs/planning/v2`. Điều hướng chi tiết ở skill `.agents/skills/cursus-engineering-guide/SKILL.md`.

**KHÔNG coi là nguồn hiện hành:** `docs/planning/v1/**` và `docs/archive/planning-v2/ui-ux-brief.md` (đã bị thay bởi file `08-Cursus-UI-UX-Master-Spec.md`) — chỉ đọc nếu user chủ động yêu cầu tham khảo lịch sử.

Skill thiết kế UI vẫn load thêm:
`.agents/skills/design-excellence/SKILL.md` (nguyên tắc chống AI-slop, áp dụng mọi dự án)
`.agents/skills/cursus-design-system/SKILL.md` (design token riêng Cursus — PHẢI khớp với `08-Cursus-UI-UX-Master-Spec.md`, chạy `/sync-docs` nếu nghi ngờ lệch)

---

## 0. Nguyên tắc làm việc chung

- KHÔNG đánh dấu bất kỳ màn hình/tính năng nào "hoàn thành" nếu chưa qua đủ checklist ở mục 6.
- KHÔNG tự ý đổi kiến trúc/stack đã chốt ở mục 1 — nếu thấy lựa chọn khác tốt hơn, đề xuất và giải thích, không tự ý đổi.
- Mọi tính năng mới đi qua chu trình **Red → Green → Refactor** ở mục 5, không code thẳng rồi báo xong.
- Nếu 1 phiên làm việc bị lặp lỗi 2 vòng liên tiếp không tiến triển (sửa A hỏng B, sửa B lại hỏng A) — DỪNG LẠI, báo rõ hiện tượng, đề nghị reset thay vì cố sửa tiếp trong ngữ cảnh đã rối.

## 1. Stack đã chốt (không tự ý đổi)

- Frontend: React + TailwindCSS.
- Không thêm dependency ngoài danh sách đã duyệt nếu chưa hỏi user trước.
- Trước khi dùng bất kỳ package/SDK mới, đọc tài liệu chính thức trước (không đoán API); nếu không có quyền truy cập docs, hỏi user thay vì tự bịa cú pháp.
- Không dùng kiểu dữ liệu mơ hồ (`any` trong TypeScript hoặc tương đương) — luôn định nghĩa interface/type rõ ràng.

## 2. Những trang/tính năng BẮT BUỘC có trong MỌI web app

- [ ] Trang **Đăng nhập** và **Đăng ký** TÁCH RIÊNG (không gộp 1 form ẩn/hiện).
- [ ] Đăng ký có xác thực input rõ ràng (email hợp lệ, độ mạnh mật khẩu), thông báo lỗi cụ thể.
- [ ] Có route "quên mật khẩu" ở dạng UI tối thiểu.
- [ ] Có nút **Đăng xuất** dễ tìm.
- [ ] Có trang 404 / trang lỗi chung.
- [ ] Có toggle **Sáng/Tối**, lưu lựa chọn (localStorage/cookie), áp dụng nhất quán toàn site.
- [ ] Có chuyển đổi **Ngôn ngữ VI/EN** qua hệ thống i18n, không hardcode chuỗi trong component.
- [ ] Mọi khối dữ liệu có đủ 4 trạng thái: Loading / Empty / Success / Error (kèm nút thử lại).
- [ ] Không hardcode API key/secret — luôn dùng biến môi trường (`.env`), và `.env` nằm trong `.gitignore`.
- [ ] Ảnh từ domain ngoài phải khai báo whitelist rõ ràng trong config, không để lỗi ảnh vỡ âm thầm.

## 3. Typography, màu sắc, animation

Chi tiết token màu/spacing/animation riêng của Cursus nằm ở `cursus-design-system/SKILL.md`. Nguyên tắc chung (rule of 3, tránh AI-slop, quy trình 2 pha) nằm ở `design-excellence/SKILL.md` — đọc cả hai trước khi thiết kế bất kỳ màn nào.

## 4. Quy trình bắt đầu 1 tính năng mới — qua 2 tài liệu trước khi code

Khi user yêu cầu 1 tính năng mới (không phải sửa nhỏ), tạo 2 artifact trước khi đụng code:

1. **Mini-PRD** — tính năng này giải quyết vấn đề gì, cho ai, thành công trông như thế nào.
2. **Mini-TRD** — component nào, state nào, data shape nào, ảnh hưởng màn hình nào khác.

Chỉ sau khi 2 tài liệu này được duyệt (user xác nhận) mới bắt đầu code.

### Ticket template — dùng khi giao 1 task cụ thể cho agent

```
Context: <tại sao cần làm, liên quan phần nào của Cursus>
To do:
- <việc cụ thể 1>
- <việc cụ thể 2>
Not to do:
- <phạm vi KHÔNG động vào>
Acceptance Criteria:
- <tiêu chí đo được để biết đã xong>
```

## 5. Chu trình Red → Green → Refactor cho MỌI tính năng

1. **Red** — Viết Acceptance Criteria trước (ticket template mục 4). Đây là "hợp đồng" agent phải thoả mãn.
2. **Green** — Code tối thiểu để đạt tiêu chí. Không tối ưu sớm, không thêm ngoài phạm vi "To do".
3. **Refactor** — Bắt buộc, không được bỏ qua. Dùng workflow `/self-review`: chạy app thật, chụp màn hình, đối chiếu chuẩn (mục 2, 3, và design-excellence), sửa lỗi, rồi mới coi là xong.
4. Sau khi Refactor đạt, commit với message rõ ràng kiểu `feat: <mô tả>` trước khi chuyển task tiếp theo.

## 6. Definition of Done

1. Đã qua đủ Red-Green-Refactor chưa?
2. Đã test đủ 4 trạng thái dữ liệu, cả dark/light mode, cả VI/EN chưa?
3. Đã test responsive 3 breakpoint và test bằng bàn phím (Tab) chưa?
4. Font-size/weight có đúng type scale đã định nghĩa không?
5. Có rơi vào dấu hiệu AI-slop nào ở `design-excellence/SKILL.md` mục 1 không?
6. **Đã chạy `/verify-tokens` chưa và có sạch 0 vi phạm không?** — đây là bước BẮT BUỘC, không được bỏ qua dù UI "nhìn có vẻ ổn". Lỗi từng xảy ra thật: build ra tím-indigo + mascot dù spec đã chốt Ink & Citrine — chỉ nhìn bằng mắt không phát hiện được nếu agent tự tin nhầm.
7. Đã commit Git với message rõ ràng chưa?

Nếu bất kỳ mục nào chưa đạt, KHÔNG báo cáo hoàn thành — tự sửa trước.

## 7. Self-improvement loop

Khi user gõ `/retro`, tự nhìn lại phiên vừa rồi và đề xuất cập nhật cho chính AGENTS.md này (lỗi hay lặp lại là gì, quy tắc nào nên thêm).
