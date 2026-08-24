---
name: design-excellence
description: Dùng skill này TRƯỚC KHI viết bất kỳ dòng code UI/UX nào, ở mọi dự án — không riêng Cursus. Kích hoạt khi task có từ khoá "thiết kế", "landing page", "UI", "giao diện", "màn hình mới", "redesign".
---

# Design Excellence — chống "AI slop" trong thiết kế web

Tổng hợp từ kinh nghiệm thực chiến vibe-coding (100+ giờ) và nguyên tắc thiết kế chuyên nghiệp. Mục tiêu: web KHÔNG bị nhận ra ngay là "AI làm".

## 1. Nhận diện và TRÁNH các dấu hiệu AI-slop kinh điển

Nếu bản nháp đầu tiên rơi vào 1 trong các mẫu sau, đó là dấu hiệu bạn đang dùng mặc định của model chứ không phải lựa chọn có chủ đích — PHẢI sửa:

- Gradient xanh-tím (blue-to-purple) làm nền hero hoặc nút CTA.
- Icon rải rác khắp nơi chỉ để trang trí, không mang nghĩa.
- Button có hiệu ứng glow/shadow phát sáng quá đà.
- Animation xuất hiện tràn lan không phục vụ mục đích gì (mọi thứ đều fade-in/slide-in dù không cần).
- Mascot/illustration robot 3D bóng bẩy kiểu "AI thân thiện" chung chung.
- Nền kem (#F4F1EA) + serif tương phản cao + accent màu đất nung.
- Nền gần đen + 1 accent xanh lá/đỏ chói duy nhất.
- Layout kiểu báo in: hairline rule, bo góc = 0, cột dày đặc.

Việc này không có nghĩa CẤM TUYỆT ĐỐI các yếu tố trên — nếu brief thực sự đòi hỏi (ví dụ brand đã có sẵn màu tím), thì làm theo brief. Nhưng nếu KHÔNG ai yêu cầu mà agent tự chọn mặc định này, đó là dấu hiệu lười biếng cần sửa.

## 2. Quy tắc số 3 (Rule of Three)

- Tối đa 3 màu chủ đạo (không tính neutral/xám).
- Tối đa 3 font chữ khác nhau — lý tưởng nhất chỉ dùng 1-2 (1 font display + 1 font body, có thể cùng họ font khác weight).
- Không bắt người dùng nhìn quá 3 cụm thông tin cùng lúc trên 1 khu vực màn hình.
- KHÔNG dùng font mặc định hệ thống kiểu Arial/Times New Roman cho sản phẩm chuyên nghiệp — chọn font có cá tính (Inter, Manrope, Söhne, Public Sans... tuỳ định hướng).

## 3. Tối giản = vừa đủ, không phải = ít nhất

"Less is more" chỉ đúng khi mọi chi tiết còn lại đều CẦN THIẾT. Một trang chỉ có 1 dòng tagline mà không giải thích được sản phẩm khác gì đối thủ là tối giản sai cách — che giấu thiếu sót bằng cách xoá bớt.

Trước khi xoá 1 chi tiết, tự hỏi: "Chi tiết này có giúp trả lời 2 câu hỏi cốt lõi không — (1) câu chuyện sản phẩm đang kể là gì, (2) hành động nào tôi muốn người dùng làm?" Nếu không, xoá. Nếu có, giữ dù trông "rối" hơn 1 chút.

## 4. Animation phải có lý do

Trước khi thêm bất kỳ animation nào, tự trả lời: "Animation này giúp người dùng hiểu/điều hướng gì, hay chỉ để nhìn cho đẹp?" Ưu tiên 1 khoảnh khắc animation được dàn dựng kỹ (ví dụ: page-load sequence, 1 hiệu ứng khi hoàn thành task) hơn là animation rải rác ở mọi nơi — càng nhiều chuyển động ngẫu nhiên càng khiến trang có "mùi AI".

## 5. Quy trình 2 pha — KHÔNG one-shot

**Đừng bao giờ để bản thiết kế đầu tiên là bản cuối.** Quy trình bắt buộc:

**Pha 1 — Brainstorm & tự phê bình (làm trong đầu/artifact trước khi code):**
1. Viết ra 1 token system ngắn gọn: 4-6 mã màu (kèm tên), 2 font (kèm vai trò), 1 ý tưởng layout (mô tả bằng lời + ASCII wireframe nếu cần), và 1 "signature" — chi tiết độc nhất khiến người xem nhớ trang này.
2. Tự hỏi: "Nếu tôi nhận 1 brief tương tự khác, tôi có ra kết quả giống hệt thế này không?" Nếu có → đang dùng mặc định, phải sửa lại phần đó.

**Pha 2 — Build & tinh chỉnh nhiều vòng:**
3. Chỉ sau khi token system đã qua tự phê bình mới viết code.
4. KHÔNG kỳ vọng 1 prompt là xong. Chuẩn bị tinh thần sửa nhiều vòng: căn giữa lại chữ trong nút bị lệch, thay icon generic bằng icon có ý nghĩa, sửa các dòng không thẳng hàng — chính những chi tiết nhỏ này tạo cảm giác "chỉn chu" khác biệt.
5. Chụp ảnh (screenshot) kết quả và tự phê bình lại trước khi báo hoàn thành — 1 ảnh chụp đáng giá hơn nhiều so với chỉ đọc code.

## 6. Thiết kế dựa trên tham khảo thật (Reference-driven)

Đừng thiết kế từ trí nhớ. Trước khi code:
- Nếu có ảnh/URL tham khảo cụ thể được đưa ra, PHẢI xem kỹ và nêu rõ đang mượn pattern gì từ đâu.
- Nguồn tham khảo tốt tuỳ mục đích: Awwwards/Dribbble cho landing page và xu hướng thị giác; Behance cho case study đầy đủ (có rationale, không chỉ ảnh); Mobbin cho pattern UI app/SaaS thật đã lên sản xuất (có cả flow và animation, không chỉ ảnh tĩnh).
- Bắt đầu từ 1 template/pattern có sẵn rồi tinh chỉnh thường ra kết quả tốt hơn thiết kế từ con số 0, đặc biệt nếu không có background thiết kế.

## 7. Kỷ luật kỹ thuật đi kèm (để thiết kế đẹp không đi kèm code rác)

- Tự nhận vai "Senior Architect", không phải "code theo yêu cầu thô": trước khi code, tự chọn stack và cấu trúc thư mục rõ ràng (ví dụ `lib/`, `components/`, `types/`), không để AI tự bịa cấu trúc lộn xộn.
- Không dùng kiểu dữ liệu mơ hồ (`any` trong TypeScript hoặc tương đương) — luôn định nghĩa interface/type rõ ràng cho dữ liệu hiển thị.
- Sau mỗi thay đổi lớn, tự viết tóm tắt ngắn những gì đã đổi (có thể ghi vào 1 file `CHANGELOG.md` hoặc trong Artifact) để dễ theo dõi qua nhiều phiên làm việc.
- Luôn kiểm tra lại config (ví dụ domain ảnh được whitelist, biến môi trường đúng chỗ) khi có lỗi lạ — nhiều lỗi "kỳ quái" thực chất là do thiếu 1 dòng config chứ không phải bug logic.
