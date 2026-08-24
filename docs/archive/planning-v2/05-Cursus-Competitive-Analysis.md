# Cursus — Competitive & Gap Analysis (v2.0 — hợp nhất & cập nhật)

> Hợp nhất 2 nguồn trước đây (`Cursus-Competitive-Gap-Analysis.md` và file Excel "StudyMate X" — cùng 1 sản phẩm, tên đã chốt là **Cursus**). File Excel có dữ liệu **mới hơn và đáng tin hơn** (quét 07/08/2026), nên kết luận dưới đây ưu tiên theo Excel, không theo bản .md cũ.

## 1. Kết luận nhanh — ĐÃ CẬP NHẬT (thay cho kết luận cũ đã lỗi thời)

Bản .md cũ kết luận "không sản phẩm quốc tế nào có đủ 3 yếu tố" và khuyến nghị dừng nghiên cứu thị trường. **Kết luận này không còn đúng.** Dữ liệu Excel (mới hơn, chi tiết hơn, có bằng chứng/số liệu cụ thể) cho thấy thị trường đã đông hơn nhiều, đặc biệt có 1 đối thủ cấu trúc nguy hiểm mới xuất hiện. Cursus **vẫn có gap thật**, nhưng phải định vị chính xác hơn — xem mục 3.

## 2. Top đối thủ theo mức đe dọa (từ dữ liệu Excel, đầy đủ hơn ở file gốc)

| Hạng | Sản phẩm | Mức đe dọa /10 | Vì sao nguy hiểm với Cursus |
|---|---|---|---|
| 1 | **Canvas IgniteAI Agent** (Instructure) | 9.5 | Agent chạy trên 500+ API Canvas, xây trên Claude/MCP, nhúng thẳng vào assignment. Chưa có companion cấp cá nhân SV, chưa có reflect có cấu trúc — đây là khe hở Cursus khai thác. |
| 2 | **Shovel** | 9 | Đã có "The Cushion" — về bản chất là Risk Score rule-based tương tự Cursus. Không có RAG/citation, không có guardrail liêm chính, không có dashboard GV. |
| 3 | **ChatGPT Study Mode** | 8.5 | Không biết deadline/syllabus, không có state xuyên tuần, guardrail do người dùng tự bật/tắt. |
| 4 | **Gemini Guided Learning** | 8.3 | Không có kế hoạch/deadline, không có bên thứ ba (giảng viên) trong luồng. |
| 5 | **AI Hay** (Việt Nam) | 8 | **Rủi ro phân phối, không phải tính năng** — đã hợp tác thẳng với chính FPT University qua chương trình S-Edu. Không có kế hoạch/tiến độ, và "giải bài tập" được quảng bá công khai — đối lập với ràng buộc liêm chính của đề bài. |
| 6 | DormWay | 7.8 | Chỉ dừng ở nhắc deadline, không có reflect/dashboard GV. |
| 7 | Notion AI (3.x Agents) | 7.5 | Có memory có state (điểm trùng đáng chú ý), nhưng không tích hợp LMS, không có guardrail liêm chính — ngược lại được thiết kế để "làm hộ". |

*(Xem đầy đủ 26 đối thủ trong `Team093_Project_Management-1.xlsx` gốc — không lặp lại toàn bộ ở đây để tránh trùng lặp dữ liệu.)*

## 3. Định vị lại Value Proposition (đã đưa vào PRD mục 4)

Cursus không tuyên bố "chưa ai làm planner AI" hay "chưa ai làm hỏi-đáp grounded" — cả hai đã có. Cursus định vị ở **giao điểm 3 yếu tố** (grounded trên đúng curriculum 1 trường + Reflect có cấu trúc/memory xuyên tuần + Dashboard GV có HITL) mà **chưa 1 đối thủ nào trong bảng trên có đủ cả 3 cùng lúc** — kể cả Canvas IgniteAI Agent (thiếu companion cấp SV + reflect) và Shovel (thiếu RAG/guardrail/dashboard GV).

## 4. Câu trả lời chuẩn bị sẵn khi bị hỏi trong lúc pitch

**"Sao không dùng AI Hay/ChatGPT cho rồi?"** → AI Hay và ChatGPT là công cụ hỏi-đáp một lượt, không giữ kế hoạch/deadline xuyên học kỳ, không có giảng viên trong luồng. Cursus giải quyết bài toán quản trị workflow học tập, không cạnh tranh ở "trả lời nhanh 1 câu hỏi".

**"Canvas sắp có AI agent rồi, Cursus còn ý nghĩa gì?"** → IgniteAI Agent hiện hướng tới giảng viên/quản trị viên, chưa có companion cá nhân hoá cho SV, và phụ thuộc hoàn toàn vào việc trường có mua Canvas. FPT không dùng Canvas — đây chính là khoảng trống Cursus lấp vào bằng dữ liệu FLM thật.

**"Thị trường Việt Nam chưa ai làm, có phải vì không có nhu cầu?"** → Nhu cầu có thật (deadline dày, SV quên nộp bài phổ biến). Rào cản chính là tích hợp dữ liệu curriculum riêng từng trường (không có API mở như Canvas) — đây cũng là lý do Cursus chọn ingest tĩnh từ FLM thay vì chờ tích hợp hoàn chỉnh.

---

*Đọc cùng `01-Cursus-PRD.md` mục 4 (Value Proposition) và mục 11 (Risk Register).*
