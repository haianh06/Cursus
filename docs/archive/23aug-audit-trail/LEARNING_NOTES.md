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
6. **"Bản audit của 1 AI khác" là tài liệu tham khảo, không phải sự thật mặc định.** Trong phiên sửa landing page, nhiều "mega-prompt"/bài audit dán vào (nói RLS bị lộ, nói "Phản tư" là từ dở, nói nên đổi màu mascot sang xanh dương generic...) — một phần đúng, một phần sai hoặc mâu thuẫn với quyết định đã chốt trước đó. **Bài học: khi nhận 1 bản đánh giá/prompt từ nguồn khác (kể cả do 1 AI khác viết), luôn đối chiếu lại với code thật và với quyết định đã chốt trước khi làm theo — không phải cứ "nghe có vẻ chuyên nghiệp" là đúng.**
7. **1 quyết định chốt hôm nay có thể cần nhắc lại ở lượt sau — đừng ngại hỏi lại khi thấy mâu thuẫn.** Ví dụ thật: chốt giữ "Không bịa" ở lượt này, một prompt dán vào ở lượt sau lại yêu cầu xoá đúng cụm đó — nếu không đối chiếu lại quyết định cũ, dễ tự ý đổi theo yêu cầu mới nhất mà quên mất lý do đã chốt trước.

---

## Phần 5 — Hiệu năng, Accessibility, SEO (rút ra từ đợt audit + sửa landing page)

### 5.1 Đo hiệu năng web (Web Performance)

| Từ | Nghĩa | Ví dụ trong Cursus | Vì sao cần biết |
|---|---|---|---|
| **Core Web Vitals** | Bộ 3 chỉ số Google dùng để đánh giá trải nghiệm tải trang thật | LCP, CLS, (I)NP — xem 3 dòng dưới | Ảnh hưởng trực tiếp thứ hạng SEO và cảm giác "web có mượt không" của người dùng thật |
| **LCP** (Largest Contentful Paint) | Thời gian phần tử lớn nhất trên màn hình (thường là ảnh/video hero) hiển thị xong | Ảnh poster hero — đo được 3.5s trên mobile (throttled), ngưỡng chuẩn Google là **<2.5s** | Số càng thấp càng tốt — đây là chỉ số người dùng "cảm nhận được" rõ nhất (trang có vẻ tải xong nhanh hay chậm) |
| **CLS** (Cumulative Layout Shift) | Đo mức độ bố cục trang "nhảy" trong lúc tải (ảnh load sau làm chữ bị đẩy xuống) | Đo được 0.001 — gần như hoàn hảo, ngưỡng chuẩn là **<0.1** | CLS cao gây khó chịu thật (bấm nhầm nút vì nó vừa nhảy chỗ) |
| **FCP / TBT** | FCP = lúc pixel đầu tiên hiện lên; TBT = tổng thời gian main thread bị chặn không phản hồi được tương tác | Đo qua Lighthouse cùng lúc với LCP/CLS | Bổ sung góc nhìn cho LCP — trang có thể "thấy chữ sớm" (FCP thấp) nhưng vẫn "đơ" khi bấm (TBT cao) |
| **Lighthouse** | Công cụ Google đo Core Web Vitals + gợi ý sửa, chạy được qua CLI hoặc Chrome DevTools | `npx lighthouse <url> --output json` | **Chỉ đo trên bản `vite build` (production), không đo trên `npm run dev`** — dev server không nén/không bundle nên số liệu vô nghĩa (đã từng đo nhầm ra LCP 57 giây do đo nhầm vào dev server) |
| **`requestAnimationFrame` (rAF)** | Hàm trình duyệt gọi lại đúng nhịp trước mỗi lần vẽ khung hình (~60 lần/giây nếu mượt) | Dùng để tự đo "mỗi khung hình cách nhau bao nhiêu ms" khi cuộn trang, phát hiện khung hình >32ms (dưới 30fps) | Cách đo "giật khi cuộn" bằng số liệu thật thay vì cảm giác — 1 khung hình quá 16.6ms là đã trễ nhịp 60fps |
| **`<link rel="preload">`** | Gợi ý cho trình duyệt tải trước 1 tài nguyên quan trọng, không cần đợi JS chạy xong mới biết tới nó | Ảnh poster hero mobile — thêm preload giúp LCP giảm được 500ms thật (đo trước/sau) | Đặc biệt quan trọng cho SPA (React) — ảnh/video quan trọng nằm trong JSX nên trình duyệt "không thấy" được cho tới khi JS chạy xong, phải preload thủ công |
| **Render-blocking resource** | Tài nguyên (CSS, font ngoài) chặn trình duyệt vẽ trang cho tới khi tải xong | Google Fonts `<link rel="stylesheet">` — Lighthouse chỉ đích danh tốn ~450ms | `rel="preconnect"` chỉ giúp mở kết nối sớm, không loại bỏ hẳn việc file đó vẫn chặn render |
| **Decode cost của video** | Chi phí CPU/GPU để giải mã video đang phát, kể cả khi video không hiện trên màn hình | 2 video ngày/đêm của hero vẫn chạy dù cuộn xuống hàng nghìn px — đo được góp phần gây giật khi cuộn | Video/audio nền phải tự pause khi cuộn khỏi màn hình (dùng `IntersectionObserver`) — "ẩn đi" (CSS `opacity:0`) không có nghĩa là nó ngừng tốn tài nguyên |

### 5.2 `IntersectionObserver` — cơ chế đứng sau rất nhiều hiệu ứng cuộn trang

`IntersectionObserver` là API trình duyệt để biết 1 phần tử **có đang hiện trong khung nhìn hay không**, không cần tự tính toán vị trí cuộn bằng tay (`scroll` event + đo `getBoundingClientRect` thủ công vừa tốn hiệu năng vừa dễ sai).

Trong Cursus, 1 API này đứng sau **3 tính năng tưởng như khác nhau**:
- Nav bar tự tô sáng mục đang xem khi cuộn trang (`LandingPage.jsx`)
- Section "Cách hoạt động" tự đổi nội dung khung sticky bên phải theo bước đang cuộn tới (`LandingWorkflow.jsx`)
- Video hero tự dừng khi cuộn ra khỏi màn hình (`LandingHero.jsx`)

**Bug thật đã gặp:** thêm 1 section mới vào giữa trang (Bento grid) mà section đó không nằm trong danh sách theo dõi của `IntersectionObserver` → có 1 khoảng ~1200px cuộn qua mà **không mục nav nào được sáng** (không phải do section mới, mà do logic cũ set lại trạng thái theo bất kỳ section nào đang hiện, kể cả section không có nút nav tương ứng). **Bài học: mỗi lần thêm 1 section mới vào giữa 1 luồng đang có logic cuộn/nav, phải tự hỏi "section này có nằm trong phạm vi observer đang theo dõi không, và nếu không thì nav sẽ hiển thị gì khi cuộn qua nó?"** — không tự nhiên đúng, phải test bằng cách cuộn thật qua toàn trang.

### 5.3 Accessibility (khả năng tiếp cận — WCAG)

| Từ | Nghĩa | Ví dụ trong Cursus | Vì sao cần biết |
|---|---|---|---|
| **WCAG** (Web Content Accessibility Guidelines) | Bộ tiêu chuẩn quốc tế cho "web dùng được cho người khuyết tật" — mức phổ biến nhất là **AA** | Contrast chữ/nền, focus state, ARIA | Nhiều nơi (kể cả gói thầu B2B) yêu cầu bắt buộc, không chỉ là "điểm cộng" |
| **Focus trap** | Khi mở 1 popup/menu, phím Tab chỉ nên chạy quanh trong popup đó, không "lọt" ra ngoài trang phía sau | Menu mobile của navbar, khung chat nổi | Thiếu focus trap → người dùng bàn phím Tab ra khỏi popup mà không biết, mất luôn ngữ cảnh đang làm gì |
| **`aria-expanded` / `aria-controls`** | Thuộc tính báo cho screen reader biết 1 nút có đang mở rộng 1 khối nội dung khác không, và khối đó là khối nào | Nút hamburger, accordion FAQ | Không có 2 thuộc tính này, người dùng screen reader không biết bấm nút có tác dụng gì |
| **`aria-live`** | Đánh dấu 1 vùng nội dung "tự thay đổi" để screen reader tự đọc to phần mới, không cần người dùng bấm gì | Khung chat — tin nhắn AI mới phải được đọc ra ngay | Thiếu `aria-live`, người dùng screen reader không biết AI đã trả lời xong |
| **Skip link** | Link ẩn (chỉ hiện khi Tab tới) cho phép nhảy thẳng qua navbar vào nội dung chính | `landing-skip-link` → nhảy tới `#main-content` | Không có skip link, người dùng bàn phím phải Tab qua hết navbar ở **mọi trang** trước khi vào nội dung |
| **`prefers-reduced-motion`** | Cờ hệ điều hành người dùng tự bật khi không muốn thấy hiệu ứng chuyển động (say sóng thị giác, động kinh do ánh sáng nhấp nháy...) | Toàn bộ animation mascot/hero phải tắt khi cờ này bật | Đây không phải "làm cho vui" — với 1 số người dùng thật, bỏ qua cờ này gây khó chịu/hại thật |
| **Contrast ratio** | Tỉ lệ tương phản màu chữ/nền, đo bằng số (ví dụ 4.5:1) | Text phải đạt ≥4.5:1 với nền theo WCAG AA | Màu "nhìn có vẻ đủ rõ" bằng mắt thường có thể vẫn fail chuẩn đo — phải đo bằng công cụ, không đoán bằng mắt |

### 5.4 SEO (Search Engine Optimization) cho web dạng SPA (React)

| Từ | Nghĩa | Ví dụ trong Cursus | Vì sao cần biết |
|---|---|---|---|
| **SPA** (Single Page Application) | Web chỉ tải 1 trang HTML gốc, mọi nội dung sau đó do JavaScript (React) tự vẽ ra | Toàn bộ Cursus frontend | Hệ quả SEO quan trọng nhất: nội dung **không có sẵn trong HTML gốc**, bot không chạy JS sẽ không thấy gì |
| **SSR** (Server-Side Rendering) / **Prerendering** | Server tự render sẵn HTML có đủ nội dung trước khi gửi cho trình duyệt/bot, thay vì để JS vẽ sau | Next.js làm được, Vite (Cursus đang dùng) thì không có sẵn | Đánh đổi lớn: đổi sang SSR = đổi framework, không phải 1 tính năng thêm vào nhanh được |
| **`robots.txt`** | File khai báo cho bot tìm kiếm biết được phép/không được phép quét trang nào | Chặn `/student`, `/admin`... (trang riêng tư sau đăng nhập) | Không phải "khoá bảo mật" — chỉ là lời đề nghị lịch sự với bot tử tế, không chặn được người cố tình truy cập |
| **`sitemap.xml`** | Danh sách URL công khai, gợi ý bot nên index — không bắt buộc bot phải nghe theo | Bị thiếu `/privacy`, `/terms` dù 2 trang này công khai thật — bug thật đã tìm và sửa | Sitemap không tự cập nhật — mỗi khi thêm 1 route công khai mới, phải tự nhớ thêm vào |
| **Canonical URL** | Khai báo "đây là URL chính thức" của 1 trang, tránh bị tính là nội dung trùng lặp nếu có nhiều URL dẫn tới cùng nội dung | `<link rel="canonical">` | Quan trọng khi 1 trang truy cập được qua nhiều URL khác nhau (có/không có `www`, có/không có query string...) |
| **`hreflang`** | Khai báo "bản ngôn ngữ khác của trang này nằm ở URL nào" | Cursus **chưa có** — vì VI/EN hiện chỉ là nút chuyển đổi phía client, dùng chung 1 URL, không có URL riêng `/en/...` | Chỉ có tác dụng khi mỗi ngôn ngữ có **URL riêng** — đổi ngôn ngữ mà không đổi URL thì hreflang không có gì để trỏ tới |
| **OG tags** (Open Graph) | Bộ thẻ meta quyết định link được share lên Facebook/Zalo/Slack hiện ảnh/tiêu đề gì | `og:title`, `og:description`, `og:image` | Thiếu hoặc sai kích thước `og:image` → link share lên bị cắt ảnh xấu, dù trang web thật vẫn đẹp |
| **Tỉ lệ ảnh OG chuẩn** | 1200×630px (tỉ lệ ~1.91:1) | Ảnh cũ 1024×1024 (vuông) bị Facebook/Zalo tự cắt méo — bug thật đã tìm và sửa | Sai tỉ lệ không báo lỗi gì cả — trang vẫn chạy bình thường, chỉ có link share nhìn xấu, rất dễ bị bỏ sót |
| **Structured data / JSON-LD** | Đoạn dữ liệu có cấu trúc nhúng trong trang, giúp Google hiểu "đây là loại nội dung gì" (tổ chức, sản phẩm, bài viết...) | `<script type="application/ld+json">` khai loại `WebSite` | Chọn sai loại (ví dụ khai `SoftwareApplication` mà không có rating/giá thật) có thể bị Google coi là thông tin sai lệch |

### 5.5 Bảo mật tầng hạ tầng (Security headers)

| Từ | Nghĩa | Vì sao cần biết |
|---|---|---|
| **`X-Frame-Options`** | Chặn trang bị nhúng vào `<iframe>` của site khác | Chống **clickjacking** — kẻ xấu nhúng trang thật vào 1 trang giả để lừa người dùng bấm nhầm |
| **`X-Content-Type-Options: nosniff`** | Chặn trình duyệt tự đoán loại file khác với khai báo `Content-Type` thật | Chống 1 số kiểu tấn công lợi dụng trình duyệt "đoán nhầm" file là script |
| **`Referrer-Policy`** | Kiểm soát trang web gửi bao nhiêu thông tin "tôi đến từ đâu" khi người dùng bấm link ra ngoài | Tránh rò rỉ URL nội bộ (có thể chứa thông tin nhạy cảm) cho trang đích |
| **`Permissions-Policy`** | Khai báo trang **chủ động từ chối** quyền truy cập camera/mic/vị trí dù trình duyệt có hỗ trợ | Giảm bề mặt tấn công — tắt hẳn quyền mà app không cần dùng tới |
| **CSP** (Content-Security-Policy) | Header mạnh nhất — khai báo chính xác trang được phép tải script/ảnh/font từ những domain nào | **Cursus chưa bật** — vì cần test kỹ với Supabase/video/Google Fonts trước, bật ẩu dễ tự chặn nhầm tài nguyên của chính mình | Đây là header khó nhất, nên làm sau cùng và test kỹ — không phải cứ thêm càng nhiều header càng an toàn nếu chưa hiểu nó chặn gì |

### 5.6 CSS cascade — bug "đã set class mà không có tác dụng"

**Hiện tượng thật gặp 2 lần trong 1 phiên:** thêm class Tailwind (`pl-9`, `text-base`) vào 1 phần tử, nhưng style không đổi — vì đã có sẵn 1 class CSS thường (`.input`, `.body-text`, viết tay trong `index.css`, không phải Tailwind) đặt cùng thuộc tính bằng cú pháp rút gọn (`padding: ...` thay vì chỉ `padding-left: ...`).

**Vì sao xảy ra:** Tailwind v4 xếp toàn bộ utility class vào 1 "cascade layer" riêng, và layer đó **mặc định có độ ưu tiên thấp hơn** CSS thường viết tay ở ngoài layer — bất kể utility class nằm sau trong file hay được thêm sau trong code. Cảm giác "tôi mới thêm, sao style cũ vẫn thắng" là dấu hiệu kinh điển của việc này.

**Cách tự chẩn đoán khi gặp lại:** mở DevTools → chọn phần tử → tab Styles → xem giá trị nào đang bị gạch ngang (bị override) và bởi rule nào. Nếu thấy 1 class Tailwind bị gạch bởi 1 class thường viết tay dùng thuộc tính rút gọn (shorthand) — đúng là bug này.

**Cách sửa an toàn (đã áp dụng thật):** không sửa lại class dùng chung (`.input`, `.body-text` còn dùng ở nhiều chỗ khác) — chỉ ghi đè bằng `style={{ ... }}` inline (độ ưu tiên luôn thắng) hoặc tạo 1 class mới hẹp phạm vi, tránh gây ảnh hưởng ngược tới những chỗ khác đang dùng đúng class cũ.

---

## Phần 6 — Kỹ thuật frontend: gộp component, tái dùng, tránh phá vỡ

### 6.1 Gộp 2 component gần giống nhau thành 1 (component consolidation)

Cursus từng có **2 mascot khác nhau**: 1 bản "đầu tròn đơn giản" (dùng ở chỗ nhỏ như icon header) và 1 bản "robot chi tiết" (dùng ở chỗ lớn như trang login) — 2 file, 2 bộ SVG, 2 bộ màu, không đồng bộ với nhau (đúng vấn đề "màu mè như AI" đã ghi ở Phần 1: mỗi lần cần 1 icon mới, AI vẽ thêm 1 bản mới thay vì tái dùng bản đã có).

**Cách gộp đúng (đã làm thật — `CursusMascot.jsx`):**
1. Chọn **1 bộ hình học SVG duy nhất** làm bản chuẩn (không giữ song song 2 bản).
2. Thêm 1 prop `size` — component tự quyết định mức độ chi tiết dựa theo `size` đó, thay vì người gọi phải tự chọn "dùng bản nào".
3. Ở size nhỏ (icon, launcher góc màn hình): **ẩn bớt chi tiết phụ** (tay, chân, đồ vật bay xung quanh...) và đổi `viewBox` để crop cận vào phần đầu/mặt — vẫn cùng 1 file SVG, chỉ khác "khung nhìn" (giống crop ảnh, không phải vẽ ảnh khác).
4. Xoá hẳn 2 file cũ sau khi mọi nơi gọi đã chuyển sang dùng bản mới — không giữ lại "phòng khi cần", vì giữ lại là y hệt vấn đề gộp docs ở Phần 3 (2 nguồn sự thật song song, dễ lệch nhau lần sau).

**Bài học tổng quát:** khi thấy 2 component/file làm cùng 1 việc nhưng hơi khác nhau (thường do được tạo ở 2 thời điểm khác nhau, mỗi lần "cần nhanh 1 cái tương tự"), đó là dấu hiệu nên gộp — không phải cứ để "phòng khi khác biệt có ý nghĩa" mà không kiểm tra thật.

### 6.2 Tái dùng code/CSS có sẵn nhưng bị bỏ quên — luôn kiểm tra trước khi viết mới

Khi cần làm 1 "bento grid" (bố cục ô vuông không đều kiểu Notion/Linear) cho phần landing page, việc đầu tiên **không phải viết CSS mới** mà là `grep` xem trong `index.css` đã có class `.bento-grid`/`.bento-cell` chưa — hoá ra **đã có sẵn từ trước**, chỉ là component cũ dùng nó (`LandingPrivacy.jsx`) đã đổi sang bố cục khác từ lâu, để lại CSS "mồ côi" (không còn ai gọi, nhưng vẫn nằm trong file, dễ bị tưởng nhầm là "đang dùng" nếu chỉ đọc comment mà không grep JSX thật).

**Bài học:** trước khi viết CSS/component mới, luôn `grep` tên class/tên component nghi ngờ đã có sẵn — vừa tránh viết trùng, vừa "hồi sinh" được công sức cũ thay vì bỏ phí. Nhưng phải verify bằng cách grep **cách dùng thật trong JSX**, không tin comment mô tả trong CSS (comment có thể đã lỗi thời, y hệt bài học ADR ở Phần 3).

### 6.3 SVG `viewBox` — mẹo làm icon "co giãn" theo nghĩa đúng

`viewBox="minX minY width height"` định nghĩa "khung nhìn" vào bên trong 1 hệ toạ độ SVG cố định. Đổi `viewBox` (không đổi path bên trong) tương đương với **crop/zoom vào 1 vùng của cùng 1 hình**, khác hẳn với co giãn (`scale`) toàn bộ hình nhỏ lại. Đây là cách mascot ở size nhỏ "nhìn như đang đứng gần camera hơn" thay vì "cùng 1 cảnh nhưng bé tí, mờ chi tiết".

### 6.4 Tránh nhảy layout khi đổi ngôn ngữ (VI ⇄ EN)

Chữ tiếng Việt và tiếng Anh **không cùng độ dài** cho cùng 1 ý (ví dụ "Dành cho giảng viên" dài hơn "For Teachers"). Nếu 1 nút/link co giãn theo đúng độ dài chữ, chuyển ngôn ngữ sẽ làm cả thanh nav "nhảy" sang trái/phải — nhìn giật, thiếu chuyên nghiệp.

**Cách Cursus xử lý (đã có sẵn, đáng học lại):** tính trước `minWidth` cho mỗi nút = độ rộng của bản **dài hơn** trong 2 ngôn ngữ (đo thật bằng công cụ, không đoán) + chút đệm — rồi gán cứng `minWidth` đó cho nút, để nút không bao giờ co lại nhỏ hơn khi ngôn ngữ ngắn hơn hiện ra. Bài học tổng quát: **với bất kỳ UI đa ngôn ngữ nào, phải tự hỏi "phần tử này có kích thước cố định hay co giãn theo nội dung — và nếu co giãn, đổi ngôn ngữ có làm nó nhảy vị trí không?"**

---

## Phần 7 — Kiểm thử & gỡ lỗi với AI coding assistant: đo thật thay vì đoán

### 7.1 Vì sao phải tự dựng công cụ đo thay vì chỉ đọc code

Nhiều lỗi trong phiên làm việc này **đọc code không thấy được**, chỉ hiện ra khi mô phỏng đúng hành vi người dùng thật:

| Lỗi thật đã tìm ra | Cách tìm ra (không phải đọc code suông) |
|---|---|
| Nav mất highlight khi cuộn qua vùng mới thêm | Script tự cuộn dần qua toàn trang (mỗi 100px), ghi lại mục nav nào đang sáng ở mỗi vị trí — lỗi chỉ hiện ra khi cuộn **liên tục**, cuộn nhảy cóc tới 1 điểm bất kỳ sẽ không thấy vì logic phụ thuộc lịch sử cuộn |
| Chatbot trả lời sai câu hỏi (nhầm "đăng nhập" thành "đăng ký") | Gõ thật 1 câu hỏi mẫu vào ô chat, đọc đúng câu trả lời trả về — lỗi do 2 danh sách từ khoá bị trùng, chỉ lộ ra khi có 1 câu chứa cả 2 từ khoá cùng lúc |
| Icon kính lúp đè lên chữ trong ô tìm kiếm | Đọc code Tailwind (`pl-9`) tưởng đúng — chỉ khi đo `padding-left` **đã tính toán thật** trên trình duyệt mới thấy nó bị 1 class khác ghi đè về 14px |
| Video nền vẫn chạy dù cuộn ra xa | Đọc thuộc tính `paused` của thẻ `<video>` thật sau khi cuộn, không phải đoán "chắc nó tự dừng" |

**Bài học chung:** đọc code cho biết **ý định**, đo bằng công cụ thật cho biết **thực tế** — 2 thứ không phải lúc nào cũng khớp nhau, nhất là khi có nhiều lớp CSS/logic chồng lên nhau.

### 7.2 Vài kỹ thuật đo cụ thể đã dùng

- **`getBoundingClientRect()`** — lấy vị trí/kích thước thật của 1 phần tử trên màn hình (top, left, width, height) tại đúng thời điểm gọi, kể cả sau khi cuộn/animation. Dùng để đo phần tử có bị tràn ra ngoài khung nhìn không (`rect.bottom > window.innerHeight` = tràn đáy).
- **`getComputedStyle()`** — lấy giá trị CSS **cuối cùng sau khi mọi rule/lớp đã tính toán xong** (khác với đọc `style` viết tay trong code, vì CSS ngoài/class dùng chung có thể đã ghi đè).
- **Chrome headless (`--headless=new`) điều khiển qua Puppeteer** — mở được 1 trình duyệt thật không cần giao diện, cho phép: gõ chữ vào ô input thật, bấm nút thật, cuộn trang thật, chụp ảnh 1 vùng cụ thể (`clip`) — tất cả đều là hành vi **giống hệt người dùng thật** làm, không phải suy luận từ code.
- **So sánh đo trước/sau khi sửa** — luôn ghi lại số liệu (vị trí, ms, fps...) **trước khi sửa** rồi đo lại **sau khi sửa** bằng đúng phương pháp — có bằng chứng "đã cải thiện thật" thay vì chỉ tin logic sửa là đúng.

### 7.3 Một bẫy đo dễ mắc: đo nhầm môi trường

Đo hiệu năng (Lighthouse) trên `npm run dev` (dev server) ra kết quả **vô nghĩa** (LCP tới 57 giây) — vì dev server phục vụ hàng trăm file JS chưa gộp/chưa nén, hoàn toàn khác với trải nghiệm thật của người dùng cuối (chạy bản đã `npm run build`). **Bài học: luôn xác định rõ đang đo trên môi trường nào, và môi trường đó có đại diện cho trải nghiệm thật không** — áp dụng cho mọi loại đo lường, không riêng hiệu năng (ví dụ đo bảo mật trên môi trường dev có bật debug mode cũng dễ cho kết quả sai lệch tương tự).

---

## Phần 8 — Phán đoán sản phẩm & UX (product judgment)

### 8.1 Giao diện "hứa" nhiều hơn thực tế làm được — lỗi tin cậy (trust gap)

Khung chat của Cursus **trông y hệt** 1 ứng dụng chat thật (avatar, bong bóng hội thoại, hiệu ứng "đang gõ...") nhưng ban đầu **không có ô nhập chữ** — chỉ có 5 nút câu hỏi dựng sẵn. Người dùng nhìn giao diện sẽ theo phản xạ tìm chỗ gõ chữ, không tìm thấy → cảm giác "app bị lỗi", dù thực ra tính năng vẫn hoạt động (chỉ hoạt động theo cách khác với những gì giao diện gợi ý).

**Bài học tổng quát:** 1 giao diện phải **hứa đúng những gì nó làm được** — nếu chỉ hỗ trợ vài câu hỏi cố định (không phải AI hội thoại tự do thật), nên thiết kế rõ ràng là "menu FAQ" (ví dụ dùng thẻ/nút lớn, không dùng khung bong bóng chat), thay vì mượn hình thức của 1 chat thật rồi làm ít hơn hình thức đó ngụ ý. Dấu hiệu nhận biết lỗi này: xem lại 1 giao diện và tự hỏi "nếu người dùng thử làm đúng điều giao diện này gợi ý họ có thể làm, họ có làm được không?"

### 8.2 Đồng nhất trải nghiệm trên mọi trang, không chỉ trang chính

Toggle đổi ngôn ngữ/giao diện sáng-tối có sẵn ở trang chủ và mọi trang dashboard sau đăng nhập — nhưng bị thiếu ở các trang `/login`, `/onboarding`, `/demo/select-role`... (không ai để ý vì mỗi trang được code ở thời điểm khác nhau). **Bài học: khi 1 tính năng được coi là "luôn có" (core affordance) của sản phẩm, phải tự kiểm tra nó có mặt ở **mọi** điểm chạm công khai, không chỉ trang được xem/test nhiều nhất** — lỗi loại này rất dễ sống sót lâu vì từng trang riêng lẻ nhìn vẫn "đúng", chỉ lộ ra khi so sánh chéo giữa các trang.

### 8.3 Khi nào nên giữ nguyên, khi nào nên đổi mới theo yêu cầu mới

Gặp nhiều yêu cầu "redesign lại toàn bộ theo phong cách X" (dán kèm ảnh/mô tả 1 web khác) trong phiên này. Cách xử lý đã áp dụng: **tách riêng phần "vấn đề thật, đáng sửa"** (ví dụ: mascot chìm nghỉm ở dark mode — có thật, nên sửa) ra khỏi **phần "gu thẩm mỹ khác, không phải lỗi"** (ví dụ: đổi hẳn sang nền đen kiểu Vercel/Linear — không phải Cursus "sai", chỉ là 1 phong cách khác). Chỉ áp dụng phần đầu ngay, phần sau cần hỏi lại rõ ràng trước khi làm — vì đổi theo phong cách mới có thể xoá bỏ công sức đã tinh chỉnh trước đó (màu sắc đã kiểm tra contrast, bố cục đã responsive...) mà không chắc người yêu cầu thực sự muốn đánh đổi điều đó.

### 8.4 Khi không tái hiện được lỗi đã được báo — vẫn phải để lại "lưới an toàn"

Người dùng chụp được 1 khung hình lộ watermark ("KlingAI") của công cụ tạo video AI ngay trên video nền hero — rõ ràng là lỗi thật (lộ thương hiệu bên thứ ba trên sản phẩm của mình). Nhưng khi rà lại **toàn bộ** 2 video (ngày/đêm), lấy mẫu mỗi 0.5 giây suốt cả đoạn ~5 giây, cộng cả 2 ảnh poster tĩnh — không tìm thấy watermark ở bất kỳ khung hình nào. Bằng chứng phụ: file video ban đêm có thời gian sửa đổi **mới hơn hẳn** mọi asset khác — dấu hiệu file rất có thể đã được xuất lại (re-export) để xoá watermark trước khi tôi kiểm tra.

**Bài học:** không tái hiện được lỗi không có nghĩa là lỗi không có thật (người dùng không tự bịa ra ảnh chụp) — cũng không có nghĩa phải cố tái hiện bằng mọi giá khi bằng chứng gián tiếp (mốc thời gian sửa file) đã gợi ý lỗi có thể đã được xử lý ở nơi khác. Cách xử lý an toàn: (1) báo cáo trung thực những gì đã kiểm tra và tìm thấy/không tìm thấy, kèm bằng chứng (mốc thời gian file), thay vì im lặng bỏ qua hoặc giả vờ đã sửa xong; (2) vẫn thêm 1 lớp phòng vệ rẻ tiền (vignette làm tối góc dưới-phải — nơi watermark hay xuất hiện) dù không chắc chắn 100% cần thiết, vì chi phí thêm gần như bằng 0 còn lợi ích là tránh phải lặp lại việc rà soát này nếu watermark xuất hiện lại ở 1 bản render tương lai.

