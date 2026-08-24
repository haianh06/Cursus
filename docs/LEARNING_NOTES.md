# Kiến thức nền — thuật ngữ, khái niệm, bài học

**Mục đích:** file này để **bạn học**, không phải hồ sơ nộp cho BTC (không đưa vào 10 deliverable). Gộp lại toàn bộ thuật ngữ đã dùng trong quá trình làm Cursus, giải thích bằng ví dụ thật của chính dự án — để lần sau gặp lại từ đó, bạn hiểu chứ không chỉ nhớ mặt chữ. Đọc xong 1 phần, thử giải thích lại bằng lời của mình — nếu giải thích được cho người khác thì mới thật sự hiểu.

---

## Phần 1 — Thiết kế giao diện (UI/UX)

### 1.1 Thuật ngữ cơ bản

| Từ | Nghĩa | Ví dụ trong Cursus | Vì sao cần biết |
|---|---|---|---|
| **CTA** (Call To Action) | Nút/link mời làm 1 hành động cụ thể tiếp theo | "Bắt đầu ngay", "Xác nhận kế hoạch" | 1 màn hình nên chỉ có **1 CTA chính** — nhiều CTA cùng nổi bật ngang nhau làm người dùng không biết bấm gì trước |
| **Audit** | Rà soát toàn bộ 1 thứ để liệt kê hiện trạng, chưa sửa vội | Audit `index.css` = liệt kê hết màu/hiệu ứng đang có | Luôn audit trước khi sửa lớn — sửa mà không audit dễ sửa nhầm chỗ không phải vấn đề gốc |
| **Gradient** | Màu chuyển dần từ màu này sang màu khác | Nút CTA cam đậm → cam nhạt | Dùng ít, có chủ đích — gradient ở khắp nơi là dấu hiệu "AI tự trang trí không kiểm soát" |
| **Glow/shadow** | Hiệu ứng phát sáng/đổ bóng quanh phần tử | `box-shadow` quanh bong bóng chat | Giống gradient — 1-2 chỗ thì sang, khắp nơi thì rối |
| **Hover / Active / Focus state** | 3 trạng thái tương tác: hover = rê chuột vào (chưa bấm), active = đang bấm giữ, focus = đang được chọn bằng bàn phím (Tab) | Nút phóng to khi hover, viền sáng khi focus | Focus state hay bị quên — thiếu nó thì người dùng bàn phím/khiếm thị không dùng được |
| **Animation / Motion** | Chuyển động theo thời gian | Mascot chớp mắt, nút "pop" khi xuất hiện | Animation phải **có lý do** (báo trạng thái, dẫn mắt) — animation chỉ để "cho sinh động" là thứ đầu tiên nên cắt khi màu mè quá |
| **Typography** | Cách dùng chữ (font, cỡ, độ đậm, dòng) để tạo cảm giác/phân cấp | Heading to đậm, body nhỏ hơn | Sản phẩm "trông đắt tiền" thường nhờ typography tốt, không phải nhờ màu |
| **Visual hierarchy** (phân cấp thị giác) | Thứ tự mắt nhìn thấy cái gì trước | CTA chính nổi hơn CTA phụ | Nếu mọi thứ đều nổi bật ngang nhau → không còn hierarchy → mắt không biết nhìn đâu |
| **Whitespace / Spacing** | Khoảng trắng giữa các phần tử — cố tình để trống | Card cách đều nhau, không dồn sát | Thiết kế "thoáng" thường do dùng nhiều whitespace hơn, không phải do bớt nội dung |
| **Design tokens** | Giá trị thiết kế (màu, khoảng cách, bo góc) đặt tên thành biến, dùng lại khắp nơi | `--accent`, `--radius-md` trong `index.css` | Đổi 1 biến = đổi cả app — không phải sửa từng chỗ hardcode màu |
| **Component** | 1 khối giao diện tái dùng được | `Sidebar`, `SourceDrawer`, `Toast` | Nghĩ theo component giúp giao diện nhất quán — sửa 1 nơi, áp dụng mọi nơi dùng nó |
| **IA** (Information Architecture) | Cách tổ chức "trang nào có khối gì" trước khi vẽ chi tiết | Bảng "Dashboard gồm NextBestAction, WeekProgress..." | Làm IA trước khi làm giao diện chi tiết — tránh vẽ đẹp rồi phát hiện thiếu thông tin quan trọng |
| **Mockup / Wireframe** | Bản phác thảo — wireframe = khung thô (không màu), mockup = gần giống thật | Khung "app window" giả trên landing | Wireframe trước giúp chốt bố cục nhanh, không sa vào màu sắc quá sớm |
| **Responsive** | Giao diện tự thích ứng nhiều kích thước màn hình | Layout 3 cột → 1 cột trên mobile | 1 trong các tiêu chí BTC chấm điểm trực tiếp (thang điểm ghi rõ "responsive + dark mode") |
| **Dark mode** | Bảng màu tối riêng, không phải đảo màu tự động | `.dark` trong `index.css` | Dark mode làm ẩu (chỉ đảo màu) thường bị chê contrast kém — cần thiết kế riêng, không suy ra máy móc từ light mode |

### 1.2 Bài học rút ra từ chính Cursus — vì sao bị chê "màu mè như AI"

**Chẩn đoán cụ thể (đã soát qua `index.css`/`Mascot.jsx`):**
1. Quá nhiều màu cạnh tranh: teal + gold + indigo + violet + xanh lá + đỏ + 5 màu chart, không có 1 màu "chủ" rõ ràng.
2. Chồng nhiều animation trên cùng 1 component (mascot có tới 7 animation chạy đồng thời) — dấu hiệu AI luôn *thêm* khi được yêu cầu "sinh động hơn", không bao giờ tự *bớt*.
3. Gradient/glow xuất hiện ở nhiều nơi độc lập, cộng dồn lại thành cảm giác "cái gì cũng phát sáng".

**Bài học tổng quát (áp dụng ngoài Cursus, cho mọi dự án sau này):**
- "Trông không ấn tượng" gần như luôn là do **thừa**, không phải **thiếu**. Bản năng khi bị chê là thêm hiệu ứng mới — sai hướng, nên làm ngược lại: cắt bớt trước.
- Chọn đúng 1 "signature moment" (1 điểm nhấn đặc trưng) thay vì làm mọi thứ đều động đậy.
- Để typography + spacing gánh phần "trông chuyên nghiệp" — màu chỉ nên là điểm nhấn cuối, không phải công cụ tạo phân cấp chính.
- Tham khảo đúng loại sản phẩm: sản phẩm học thuật/năng suất nên học Linear/Notion/Vercel (tiết chế), không nên học các AI chatbot demo (dễ trôi về "gradient tím-xanh + mascot robot" — kiểu mẫu số đông ai cũng làm giống nhau).

---

## Phần 2 — Sản phẩm, dữ liệu & AI Engineering

| Từ | Nghĩa | Ví dụ trong Cursus |
|---|---|---|
| **PRD** (Product Requirements Document) | Tài liệu mô tả sản phẩm làm gì, cho ai, giải quyết vấn đề gì — góc nhìn nghiệp vụ | Nội dung PRD cũ đã gộp vào `docs/PROJECT_CONTEXT.md` |
| **SRS** (Software Requirements Specification) | Đặc tả kỹ thuật chi tiết hơn PRD — chức năng cụ thể (FR) + yêu cầu phi chức năng (NFR: tốc độ, bảo mật...) | Đã gộp vào `docs/PROJECT_CONTEXT.md` mục 13-22 |
| **ADR** (Architecture Decision Record) | 1 bản ghi ngắn/quyết định kỹ thuật lớn: **Quyết định – Vì sao – Đánh đổi** | `docs/decisions/ADR.md` — ví dụ ADR-001 chọn Supabase |
| **RAG** (Retrieval-Augmented Generation) | AI tra cứu tài liệu thật rồi mới trả lời, thay vì bịa từ trí nhớ mô hình | Lý do Curi trả lời kèm trích nguồn syllabus SSA101 |
| **Chunk / Chunking** | Cắt tài liệu dài thành nhiều đoạn nhỏ để AI tìm đúng đoạn liên quan | 72 chunk từ syllabus SSA101 |
| **Reranker** | Bước lọc lại kết quả tìm kiếm cho chính xác hơn, sau bước tìm thô | `bge-reranker-v2-m3` — top-5 tìm thô, rerank xuống top-3 |
| **Guardrail** | Cơ chế chặn AI làm việc không nên làm | Chặn "làm hộ bài", chuyển sang gợi ý tự làm |
| **HITL** (Human-In-The-Loop) | Con người vẫn là người quyết định cuối, AI chỉ đề xuất/cảnh báo | Giảng viên tự bấm "đã can thiệp" — AI không tự nhắn sinh viên |
| **Provenance** | Nguồn gốc của 1 dữ liệu (thật/mô phỏng/người dùng nhập/AI suy ra) | `official_document`, `simulated`, `user_entered`, `ai_suggested` |
| **Multi-tenant** | 1 hệ thống phục vụ nhiều tổ chức riêng biệt, dữ liệu phải cách ly | Mỗi trường 1 `organization_id` |
| **RLS** (Row Level Security) | Cơ chế của database tự chặn truy vấn sai quyền ngay ở tầng DB, không cần code app tự lọc | RLS đã bật ở Cursus nhưng **bị bypass** vì role DB có `BYPASSRLS` — bài học: bật tính năng bảo mật không có nghĩa nó có tác dụng thật, phải kiểm tra tận nơi |
| **CORS** | Cơ chế trình duyệt kiểm soát trang A có được gọi API của domain B không | Cần cấu hình đúng khi frontend (Vercel) và backend (Railway) khác domain |
| **Cookie `SameSite`** | Thuộc tính cookie quyết định có gửi kèm request khác domain hay không (`Strict`/`Lax`/`None`) | Deploy 2 domain khác nhau mà quên set `None` → login "thành công" nhưng cookie không được gửi lại, trông như bug ngẫu nhiên |
| **Deploy** | Đưa sản phẩm lên chạy thật trên internet | Vercel (frontend) + Railway (backend) + Supabase (DB) |
| **Fixture** | Bộ dữ liệu mẫu cố định dùng để test/demo | `gate2_demo_v1` — sinh viên/lớp/kế hoạch mẫu |
| **Eval / Benchmark** | Đo chất lượng AI bằng bộ câu hỏi/tiêu chí cụ thể, ra con số | 25 câu RAG eval, 30 câu guardrail eval |
| **Precision / Recall** | 2 chỉ số đo độ chính xác: precision = trong số AI báo đúng, bao nhiêu % thật sự đúng; recall = trong số case đúng thật, AI bắt được bao nhiêu % | Dùng để báo chất lượng guardrail thay vì tuyên bố "100% chính xác" |
| **Acceptance criteria** | Danh sách điều kiện cụ thể để coi 1 tính năng "làm xong đúng" | "Generate trả 4-6 task, mỗi task có estimate + source" |
| **DoD** (Definition of Done) | Định nghĩa "thế nào là xong" cho cả 1 giai đoạn, không chỉ 1 tính năng | Mục 22 trong `PROJECT_CONTEXT.md` |
| **Vibe coding** | Để AI viết phần lớn/toàn bộ code theo mô tả bằng lời, thay vì tự gõ tay từng dòng | Cách làm bắt buộc của chương trình AI20K (PLO8) |

---

## Phần 3 — Bài học quản lý tài liệu dự án (rút ra từ lần gộp docs vừa làm)

1. **Gộp docs giảm rủi ro lệch nhau, nhưng phải làm cẩn thận vì blast radius lớn hơn tưởng.** Khi xoá `docs/archive/planning-v2/`, hoá ra `roles/` và `progress/` bên trong đang được `Makefile` (`make progress`) và `scripts/progress_report.py` dùng thật — xoá nhầm sẽ phá 1 hệ thống đang chạy. **Bài học: trước khi xoá bất kỳ file/folder nào, `grep` xem có chỗ nào khác đang tham chiếu tới nó không**, đừng chỉ nhìn tên file đoán là "cũ thì bỏ được".
2. **Archive khác xoá.** Đưa 1 bộ tài liệu vào thư mục `archive/` (không xoá) là đủ để nó hết "gây nhiễu" — không cần xoá hẳn mới gọi là gọn. Xoá hẳn chỉ nên làm khi chắc chắn 100% không còn giá trị tham chiếu.
3. **Sửa 1 file thường kéo theo phải sửa nhiều file khác trỏ tới nó.** Xoá/đổi tên `docs/product/blueprint.md` làm hỏng link ở 6 file khác (README, DOCS_GUIDE, run-guide...). **Bài học: `grep -rl "đường-dẫn-cũ"` toàn repo sau mỗi lần xoá/đổi tên file docs**, đừng để link chết âm thầm.
4. **ADR nên ghi ngay lúc quyết định, không chờ cuối kỳ viết lại.** Càng để lâu càng quên "vì sao" — lý do ADR-006 của Cursus tồn tại (bài học rút ra sau khi phát hiện tên model AI đã lỗi thời trong docs mà không ai biết từ khi nào).
5. **Con số cụ thể luôn đáng tin hơn "đã kiểm thử".** Ghi rõ "guardrail 30/30, RAG citation 24/25" (dù chưa hoàn hảo) đáng tin hơn nhiều so với ghi chung chung "đã test kỹ".

---

## Phần 4 — Làm việc hiệu quả với AI coding assistant (vibe coding có kiểm soát)

1. **Ra lệnh bằng giới hạn, không bằng mong muốn.** "Làm đẹp hơn" → AI hiểu là thêm hiệu ứng. "Chỉ dùng 1 màu accent cho mọi CTA, không thêm animation ngoài hover" → AI khó lạm dụng hơn nhiều.
2. **Audit trước, sửa sau — 2 bước tách rời.** Bắt AI liệt kê hiện trạng (màu/hiệu ứng/file đang có) trước khi cho phép nó sửa — gộp chung 2 việc "vừa audit vừa thêm" thì AI sẽ luôn ưu tiên thêm.
3. **Dán ảnh tham khảo cụ thể tốt hơn mô tả bằng lời.** AI bắt chước theo ảnh Linear/Vercel/Notion tốt hơn nhiều so với yêu cầu "tối giản, chuyên nghiệp" chung chung.
4. **Hỏi ngược AI để tự nó lộ ra phần thừa.** Sau khi AI code xong, hỏi "nếu phải xoá bớt 30% chi tiết trang trí ở đây để chuyên nghiệp hơn, xoá cái gì trước" — buộc AI tự phản biện lại chính nó.
5. **Luôn kiểm tra bằng chứng thật (code/git), không tin mô tả sẵn có.** Nhiều ADR trong Cursus (ADR-011, ADR-013) tồn tại chỉ vì lúc đọc lại thấy mô tả cũ không khớp code thật — thói quen tốt là verify trước khi tin, kể cả tin chính docs của mình.
