# Workflow: /self-review

> Đặt tại `.agents/workflows/self-review.md`. Sau khi code xong 1 hoặc nhiều màn hình, gõ `/self-review` để agent tự kiểm tra và tự sửa mà không cần bạn soát thủ công từng lỗi.

## Các bước agent phải thực hiện theo đúng thứ tự

1. **Chạy app** trong terminal tool (nếu chưa chạy).
2. **Mở browser tool**, lần lượt truy cập từng route/màn hình đã code.
3. Với mỗi màn hình, **chụp 4 phiên bản**: light mode, dark mode, tiếng Việt, tiếng Anh (tổng hợp tổ hợp cần thiết, ít nhất light+VI và dark+EN).
4. Với mỗi ảnh chụp, **đối chiếu từng dòng trong checklist "Definition of Done" ở AGENTS.md mục 5** và ghi lại: đạt / không đạt / lý do.
5. Nếu phát hiện: text hardcode chưa qua i18n, font-size không khớp type scale, dark mode bị vỡ giao diện, thiếu 1 trong 4 trạng thái dữ liệu, hoặc thiếu trang bắt buộc ở AGENTS.md mục 1 → liệt kê thành danh sách lỗi cụ thể (tên file, dòng nếu biết, mô tả lỗi).
6. **Tự sửa code** cho từng lỗi đã liệt kê.
7. **Chụp lại** màn hình vừa sửa để xác nhận đã đạt.
8. Lặp lại bước 3-7 tối đa 3 vòng. Nếu sau 3 vòng vẫn còn lỗi không tự sửa được (ví dụ cần quyết định thiết kế mới), dừng lại và liệt kê rõ trong Artifact để hỏi ý kiến user, không tự đoán.
9. Xuất kết quả cuối dưới dạng Artifact gồm: bảng checklist final (đạt hết hay còn gì), ảnh trước/sau của các màn có sửa lỗi.
