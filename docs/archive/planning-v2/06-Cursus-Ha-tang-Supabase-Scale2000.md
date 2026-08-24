# Cursus — Chốt Hạ tầng (có Supabase) + Đánh giá quy mô 2.000 người dùng + Bản đồ Docs

> File này là **bản chốt hạ tầng mới nhất**, ghi đè phần "Công nghệ" trong `00-Cursus-Playbook.md`. Phần tính năng vẫn giữ nguyên như đã thiết kế.
>
> **2.000 người dùng ở tiêu đề/mục 3 là bài kiểm tra dư địa hạ tầng, không phải mục tiêu KPI** — mục tiêu KPI chính thức vẫn là **1.000 SV** theo `01-Cursus-PRD.md` mục 6. Hai con số đo hai việc khác nhau, xem ghi chú đối chiếu ở PRD mục 6.

---

## 0. Chiến lược Repo & Deploy — xử lý vấn đề repo BTC cấp bị private

> **Cập nhật 11/08/2026 — ĐẢO QUYẾT ĐỊNH (xem `ADR-003` trong `docs/decisions/ADR.md`):** mục 0.2-0.6 bên dưới mô tả phương án "2 remote Git" từng được chốt nhưng **chưa từng thực thi thật** (repo local tới 11/08/2026 vẫn chỉ có 1 remote `origin` trỏ vào repo BTC) và giờ đã **quyết định KHÔNG làm** — chi phí vận hành 2 remote (dễ quên push 2 nơi, rủi ro `--force`/squash phá lịch sử) không đáng so với lợi ích (auto-deploy khi push). **Hướng đi thật đang áp dụng: chỉ 1 remote (repo BTC), deploy/migration chạy bằng CLI thủ công** — xem mục 0.7 mới thêm bên dưới. Giữ lại mục 0.1-0.6 nguyên văn để biết bối cảnh/lý do từng cân nhắc, nhưng **đừng làm theo các bước ở đây** trừ khi team đổi ý lại lần nữa.

### 0.1. Vấn đề thật đang gặp

BTC cấp 1 repo cho mỗi team khi chọn đề tài, repo này **private và team không có quyền hạ tầng** (không gắn được Vercel/Railway/Supabase trực tiếp vào — thường do repo thuộc tổ chức GitHub của BTC, team chỉ có quyền collaborator/push code, không có quyền admin để cấp OAuth cho bên thứ 3 kết nối CI/CD). Đây là tình huống phổ biến ở các cuộc thi/đồ án có BTC quản lý tập trung — không phải lỗi cấu hình của team.

### 0.2. (KHÔNG còn áp dụng — xem 0.7) Chiến lược cũ: 1 lịch sử commit dùng chung 2 remote — KHÔNG mất log ai commit gì

**Trả lời thẳng câu bạn hỏi:** không cần chọn giữa "code trên repo BTC để giữ log" **hoặc** "tạo repo riêng để deploy được" — làm được cả 2 cùng lúc, vì **git lưu tác giả + thời gian ngay bên trong từng commit** (metadata `author`, `committer`, `timestamp`), không phụ thuộc vào việc commit đó đang nằm trên server nào. Đẩy (push) 1 commit sang chỗ khác **không hề xoá hay đổi ai là người tạo ra nó** — khác hẳn việc "gộp" (squash) nhiều commit làm 1, cái đó mới thật sự làm mất log, và đây là điều PHẢI TRÁNH.

**Quy trình đúng (khác bản trước — clone từ repo BTC làm gốc ngay từ đầu, không tạo repo riêng rồi mới nối sau):**
1. **Clone thẳng từ repo BTC** làm bản gốc đầu tiên (`git clone <url-repo-BTC>`) — để lịch sử 2 bên thống nhất từ commit đầu tiên, tránh lỗi "unrelated histories" khi nối sau.
2. **Đổi tên remote gốc thành `btc`**: `git remote rename origin btc`.
3. **Thêm remote thứ 2 là repo riêng của team** (tạo trước 1 repo trống trên GitHub cá nhân/tổ chức team, có toàn quyền admin): `git remote add origin <url-repo-riêng>`.
4. **Code/commit bình thường như mọi ngày** — mỗi thành viên vẫn commit với đúng tên/email GitHub của mình (không đổi gì trong cách làm việc hàng ngày).
5. **Mỗi lần push, đẩy cả 2 nơi** (không phải "thỉnh thoảng đồng bộ"): `git push origin main && git push btc main` — cả 2 repo có **y hệt lịch sử commit, y hệt tác giả từng dòng code**, không lệch nhau. Vercel/Railway/Supabase kết nối vào `origin` (repo riêng, team có toàn quyền admin) để chạy CI/CD, deploy thật.
6. **Không bao giờ dùng `git push --force` hay squash merge** khi đẩy sang `btc` — 2 thao tác này viết lại lịch sử, đây mới là nguyên nhân thật gây mất log, không phải việc có 2 remote.

**Tại sao đây là giải pháp tốt hơn "chỉ code trên repo BTC":** nếu chỉ code trên repo BTC, team **vẫn gặp lại đúng vấn đề gốc** — không kết nối được Vercel/Railway/Supabase. Có 2 remote cùng lịch sử là cách duy nhất vừa giữ log đầy đủ trên repo BTC, vừa deploy được thật.

### 0.3. Đã xác nhận với BTC — KHÔNG bắt buộc deploy từ repo BTC cấp

**Đã hỏi và có câu trả lời:** BTC không bắt buộc deploy/CI-CD phải chạy trực tiếp từ repo họ cấp. Chiến lược 2 remote ở mục 0.2 chính thức áp dụng, không còn là giả định mở nữa — đã gỡ khỏi Assumptions ở `01-Cursus-PRD.md` mục 8.3.

### 0.6. Hướng dẫn Git chi tiết — vừa giữ log trên repo BTC, vừa deploy được (dành cho người mới dùng Git)

**Từ vựng cần biết trước:**
- **Repo (repository)** — 1 "kho" lưu code trên mạng (GitHub).
- **Remote** — địa chỉ 1 kho trên mạng mà máy bạn "biết tới". 1 máy biết được nhiều remote cùng lúc.
- **Commit** — 1 lần "lưu điểm" thay đổi code kèm ghi chú mô tả, có ghi lại ai lưu và lưu lúc nào.
- **Push** — đẩy các commit từ máy bạn lên 1 remote.
- **Clone** — tải toàn bộ 1 kho về máy lần đầu tiên.

**Bước 1 — Chuẩn bị 2 đường link:** link repo BTC cấp, và 1 repo trống mới tạo trên GitHub của team (New repository, **không tick** "Add README" để tránh xung đột lịch sử).

**Bước 2 — Clone từ repo BTC làm gốc:**
```
git clone https://github.com/ten-to-chuc-BTC/ten-repo.git cursus
cd cursus
```

**Bước 3 — Thiết lập 2 remote:**
```
git remote rename origin btc
git remote add origin https://github.com/team-ban/cursus.git
git push -u origin main
```

**Bước 4 — Làm việc hàng ngày (mỗi thành viên chạy trên máy mình):**
```
git add .
git commit -m "Mô tả ngắn đã làm gì"
git push origin main
git push btc main
```

**Bước 5 (tuỳ chọn, gộp 2 lệnh push thành 1) — chạy 1 lần duy nhất:**
```
git remote set-url --add --push origin https://github.com/team-ban/cursus.git
git remote set-url --add --push origin https://github.com/ten-to-chuc-BTC/ten-repo.git
```
Từ đó chỉ cần gõ `git push` (không ghi tên remote) là tự động đẩy lên cả 2 nơi.

**Lưu ý duy nhất cần nhớ:** không bao giờ dùng `git push --force` hay squash merge khi đẩy sang `btc` — 2 thao tác đó mới thật sự làm mất log, không phải việc có 2 remote. Vercel/Railway/Supabase kết nối vào `origin` (repo riêng của team) để deploy.

### 0.4. Vì sao KHÔNG nên chờ "khi nào deploy mới tạo repo riêng"

Ý định ban đầu ("khi nào deploy sẽ tạo repo riêng") có rủi ro: dồn việc setup hạ tầng (Vercel/Railway/Supabase, biến môi trường, CI/CD) vào phút chót ngay trước Gate 2 — đúng lúc áp lực code tính năng cao nhất. Setup hạ tầng 1 lần mất ~1-2 giờ (đã có sẵn quy trình chi tiết ở mục 2), nên **làm ngay từ 09/08 (hôm nay, theo `03-Cursus-Execution-Plan.md`)**, song song lúc code F1, để tới ngày deploy (12/08 theo lịch) chỉ còn việc trỏ code vào hạ tầng đã sẵn sàng, không phải vừa setup vừa debug deploy cùng lúc.

### 0.5. Custom domain — đã chốt mua, cần chọn tên cụ thể

**Đã quyết định mua** (ngân sách đã tính ở mục 2.2, ~$12-15/năm). Vì tôi không tra được tình trạng còn trống của tên miền theo thời gian thực, đề xuất 3 phương án — **team tự kiểm tra còn trống không tại Namecheap/Cloudflare Registrar trước khi mua**, ưu tiên theo thứ tự:
1. `cursus.app` — ngắn, gọn, đúng tên sản phẩm, đuôi `.app` bắt buộc HTTPS sẵn (hợp use case web app).
2. `getcursus.app` hoặc `usecursus.app` — dùng nếu `cursus.app` đã có người đăng ký.
3. `cursus-edu.com` hoặc `trycursus.com` — phương án dự phòng cuối, `.com` phổ biến, dễ nhớ hơn với người không quen `.app`.

**Việc cần làm:** thêm vào lịch `03-Cursus-Execution-Plan.md` ngày 09/08 (cùng lúc setup hạ tầng khác) — mua domain sớm, trỏ DNS về Vercel (frontend) ngay khi có, để URL demo dùng domain riêng xuyên suốt cả Gate 2 lẫn Mốc 3, không phải đổi link giữa chừng.

### 0.7. Hướng đi thật đang áp dụng (từ 11/08/2026) — 1 remote, deploy/migration bằng CLI thủ công

**Không tạo repo riêng.** Repo local chỉ có 1 remote (`origin` = repo BTC cấp). Supabase/Vercel/Railway **không kết nối GitHub App vào repo nào cả** — không cần, vì:

- **Supabase**: Auth + Data API + DB connection hoạt động đầy đủ chỉ bằng Project URL/anon key/connection string, không cần biết gì về GitHub. Tính năng "Connect to GitHub" trên dashboard Supabase (hay bị hỏi lúc tạo project) chỉ phục vụ migration-sync/preview branch — **bấm Skip/Not now**, không ảnh hưởng gì tới việc chạy Auth/DB thật.
- **Migration**: chạy tay `alembic upgrade head` từ máy local, trỏ `DATABASE_URL` vào Supabase Postgres — không cần CI job.
- **Deploy backend (Railway)**: `railway up` từ CLI mỗi khi có bản mới muốn đẩy lên, thay vì tự động khi push.
- **Deploy frontend (Vercel)**: `vercel --prod` từ CLI, tương tự.

**Đánh đổi đã chấp nhận:** mất auto-deploy/preview URL tự động mỗi PR — không cần thiết ở quy mô team 4 người. Bù lại: không phải nhớ push 2 remote, không có rủi ro `--force`/squash phá lịch sử repo BTC. Chi tiết lý do đầy đủ ở `ADR-003` (`docs/decisions/ADR.md`).

**Nếu sau này đổi ý** (VD thấy CLI thủ công phiền, hoặc cần preview URL cho PR): quay lại làm theo đúng mục 0.2-0.6 ở trên (tạo repo riêng, 2 remote, connect GitHub App vào repo riêng đó) — các bước đó vẫn đúng về mặt kỹ thuật, chỉ là team chọn không cần ở giai đoạn này.

---

## 1. Vì sao trước đó chưa đưa Supabase vào — và sau khi kiểm chứng, nên dùng

**Thành thật:** đây là thiếu sót thật, không phải Supabase không phù hợp mà mình chưa so sánh kỹ. Sau khi kiểm chứng (tìm kiếm giá + tài liệu chính thức 08/2026):

| Tiêu chí | Railway Postgres + tự viết Auth (bản cũ) | **Supabase (đề xuất mới)** |
|---|---|---|
| Postgres + pgvector | Có, nhưng tự setup extension, tự quản lý | **Có sẵn, bật pgvector bằng 1 click, không cấu hình gì thêm** |
| Auth (Google OAuth) | Phải tự viết bằng NextAuth.js, tự quản token | **Có sẵn trong Auth module, hỗ trợ 20+ social provider kể cả Google, chỉ cần bật** |
| Phân quyền theo role (SV/GV/Admin) | Phải tự check ở tầng code (app-level) — dễ quên check 1 chỗ nào đó | **Row Level Security (RLS) — chặn ở tầng database**, an toàn hơn hẳn vì dù code FE/BE có bug thì DB vẫn tự chặn sai quyền |
| Storage file syllabus gốc | Không có sẵn, phải tự nghĩ chỗ lưu | Có sẵn Storage module, lưu thẳng file Word/PDF gốc để đối chiếu |
| Giá miễn phí | Railway: **không có free tier vĩnh viễn**, $5/tháng sàn | **Free tier thật, không giới hạn thời gian** — 500MB DB, 50.000 MAU cho Auth, 1GB storage. Nhược điểm: project tạm dừng nếu không ai truy cập 7 ngày liên tục (chỉ cần 1 request là tự bật lại) |
| Khi cần trả phí | — | Pro $25/tháng/project khi vượt free tier (thường là lúc đã có SV thật dùng đông) |

**Kết luận: đổi sang Supabase cho phần DB+Auth+Storage.** Đây là quyết định tốt hơn bản trước, không phải vì Railway sai mà vì Supabase gộp 3 thứ (DB, Auth, Storage) làm 1, giảm số hệ thống phải tự quản lý — đúng tinh thần MVP tối giản mà chính PRD đã đặt ra từ đầu.

**Lưu ý quan trọng — Supabase KHÔNG thay được Railway hoàn toàn:** Supabase Edge Functions chạy Deno/JS, không hợp để chạy LangGraph agent bằng Python. **Vẫn cần Railway (hoặc tương đương) để chạy riêng phần Backend Python (FastAPI + LangGraph)** — Supabase chỉ thay phần DB+Auth+Storage, không thay phần "não" xử lý AI.

---

## 1.5. So sánh đầy đủ từng lớp hạ tầng — không chỉ Supabase, để biết TẠI SAO chọn đúng chứ không phải chọn đại

> Mục này trả lời trực tiếp: "nên dùng công cụ nào cho từng lớp, so với các lựa chọn khác trên thị trường ra sao". Mỗi bảng có tiêu chí: **miễn phí thật không, có pgvector/Python support không, độ khó setup, và khi nào NÊN đổi**.

### Lớp Frontend hosting

> Đã đối chiếu với bảng giá + kinh nghiệm thật của team (Vercel đã dùng nhiều lần, Netlify/Render/Firebase mới thử qua). Giá bản Pro chỉ cần trả khi vượt free tier phi thương mại — đồ án dùng free tier là đủ, ghi giá Pro ở đây để biết mốc khi nào cần nâng cấp thật (VD nếu sau này thương mại hoá).

| Công cụ | Free tier / Giá Pro | Ưu điểm | Nhược điểm | Khuyến nghị |
|---|---|---|---|---|
| **Vercel (đã chọn)** | Free (phi thương mại) / Pro $20/tháng/seat | Deploy Next.js gần như 0 cấu hình, không phải tự cấu hình Nginx/SSL/CDN/autoscaling (đúng như team đã ghi nhận), preview URL tự động mỗi PR, **team đã có kinh nghiệm thật** — giảm rủi ro so với công cụ mới | BE trên Vercel chỉ chạy được ở dạng serverless Functions, giới hạn thời gian chạy (10s free tier) — không hợp cho FastAPI + LangGraph (đúng nhận định team đã ghi) | **Giữ nguyên, chỉ dùng cho FE** — đúng công cụ cho đúng framework, có kinh nghiệm sẵn |
| Netlify | Free / Personal $9, Pro $20/tháng | Tương tự Vercel | Kém hơn Vercel cho Next.js (đúng như team nhận xét), BE cũng giới hạn tương tự | Không chọn — không có lý do đổi từ Vercel |
| Cloudflare Pages | Free, bandwidth không giới hạn | CDN nhanh, không giới hạn bandwidth | Next.js cần adapter riêng (`@cloudflare/next-on-pages`), 1 số API Node không tương thích 100% edge runtime | Chỉ cân nhắc nếu lo browser traffic thật đông vượt băng thông Vercel free — chưa cần ở quy mô đồ án |

### Lớp Backend compute (chạy Python FastAPI + LangGraph, cần chạy liên tục — không hợp serverless-function-only)

> Team đã tự tổng hợp khá sát — bổ sung thêm DigitalOcean App Platform và làm rõ hơn Google Cloud Run + lý do loại Firebase cho phần BE nặng.

| Công cụ | Free tier / Giá thật | Ưu điểm | Nhược điểm | Khuyến nghị |
|---|---|---|---|---|
| **Railway (đã chọn)** | Không free vĩnh viễn — Hobby $5/tháng sàn (+ usage), Pro $20/tháng | Setup nhanh nhất cho Python (Nixpacks tự nhận FastAPI), full-stack 1 project (BE+DB+Docker), private networking, dev experience tốt (đúng nhận định team) | **Chi phí khó dự đoán nếu chạy 24/7 hoặc có bug memory leak/vòng lặp vô hạn** (đúng rủi ro team đã lường trước) | **Giữ nguyên cho Gate 2/Mốc 3** — nhưng **bắt buộc bật Usage Alert/Budget cap trong Railway dashboard ngay từ ngày đầu setup** để chặn rủi ro chi phí bất ngờ team đã tự nhận ra |
| Render | Free (tự ngủ sau 15 phút, cold start 30-60s) / Pro $25/tháng, Scale $499/tháng | BE chạy liên tục ở bản trả phí, Docker tốt, deploy tự động | **Build cực chậm** (đúng như team ghi nhận), FE phải qua Node server riêng chứ không static-first như Vercel, **đắt nhất trong bảng ở bản Pro trở lên** | Không chọn — build chậm ảnh hưởng tốc độ lặp code lúc gấp Gate 2, chi phí Pro cao hơn hẳn Railway cho cùng nhu cầu |
| Fly.io | Free tier nhỏ (3 VM), dùng bao nhiêu trả bấy nhiêu | Scale ngang thật, region gần người dùng | Cấu hình phức tạp hơn (`fly.toml`, hiểu Docker sâu), **team chưa từng dùng** → rủi ro học công cụ mới giữa lúc gấp | Không chọn cho Gate 2 — cân nhắc cho Mốc 3 chỉ nếu có thời gian học trước |
| **Google Cloud Run** | Free tier 2 triệu request/tháng, sau đó trả theo compute-time thực tế (thường rẻ hơn Railway ở traffic thấp vì scale-to-zero) | **Serverless thật, tự scale về 0 khi rảnh (không tốn tiền lúc không ai dùng) và tự scale ngang khi tải cao** — đây là kiến trúc "chuẩn production" gần nhất trong toàn bộ bảng | Cần biết Docker + `gcloud` CLI, cold start vài giây, cần thẻ tín dụng để kích hoạt (free tier không bị trừ nếu ở trong hạn mức) | **Lựa chọn "chuẩn production" nhất nếu muốn nói chuyện nghiêm túc với giám khảo về khả năng scale thật** — chỉ đổi từ Railway nếu có ≥1 người từng dùng GCP, không học từ đầu giữa Gate 2 |
| DigitalOcean App Platform | Free tier rất hạn chế / Basic $5/tháng | Giá rẻ, dễ hiểu hơn AWS, có Managed Postgres riêng nếu cần | Hệ sinh thái AI/serverless kém hơn GCP/AWS, cộng đồng Python nhỏ hơn Railway | Phương án dự phòng nếu Railway hết ngân sách miễn phí, không phải lựa chọn đầu tiên |
| AWS App Runner / ECS Fargate | Free tier rất hạn chế | Enterprise-grade | Phức tạp nhất, dễ phát sinh chi phí ngoài ý muốn (IAM/VPC cấu hình sai) | Không khuyến nghị — over-engineering so với quy mô đồ án |
| Firebase (Cloud Functions cho BE) | Free (Spark) / Blaze trả theo usage | Nhanh có Auth built-in, hệ sinh thái Google tốt (đúng team đã thử) | **Cloud Functions không hợp BE nặng, long-running như FastAPI+LangGraph** (đúng nhận định team) — giới hạn thời gian chạy function, khó chạy Docker tuỳ ý; chi phí Blaze khó kiểm soát khi traffic tăng | **Không chọn cho BE chính** — đã tự loại đúng như team ghi nhận. **Có thể tận dụng phần Auth** nếu muốn, nhưng Supabase Auth đã thay được việc này (mục 1), không cần thêm Firebase chỉ để lấy Auth |

**Kết luận lớp này:** Railway đúng cho Gate 2/Mốc 3 — ưu tiên tốc độ setup + team đã quen dev experience. Rủi ro chi phí "khó dự đoán" mà team tự nhận ra là **có thật với Railway**, cách xử lý không phải đổi platform mà là **bật Usage Alert ngay từ đầu** (free, có sẵn trong Railway). Nếu sau này thương mại hoá thật (ngoài phạm vi đồ án), **Google Cloud Run là điểm đến hợp lý nhất** — ghi rõ đây là roadmap, không cần đổi ngay.

### Lớp LLM + Embedding API — đã chốt Google Gemini (trước đây để ngỏ "Anthropic/OpenAI")

| Nhà cung cấp | Giá tham khảo (US$/1M token, kiểm tra lại giá thật trước khi code vì đổi thường xuyên) | Free tier | Ưu điểm | Nhược điểm |
|---|---|---|---|---|
| **Google Gemini (đã chọn)** | **Cập nhật 10/08/2026** (giá `gemini-1.5-*` bản trước đã lỗi thời — dòng 1.5 ngừng hoạt động thật): `gemini-2.5-flash-lite` ~$0.10 input / $0.40 output · `gemini-2.5-flash` ~$0.30 input / $2.50 output — **rẻ nhất trong 3 nhà cung cấp**. Lưu ý: dòng 2.5 có lịch shutdown công bố 16/10/2026 (sau hạn nộp 23/08, không ảnh hưởng đồ án) | **Free tier hào phóng nhất** (đủ chạy toàn bộ Gate 2 + phần lớn Mốc 3 không tốn tiền thật) | Rẻ nhất, có luôn embedding (`gemini-embedding-001`, đổi từ `text-embedding-004` đã ngừng hoạt động) cùng hệ sinh thái — 1 API key, 1 hoá đơn, đúng tinh thần gộp hệ thống đã áp dụng với Supabase | Rate limit (request/phút) ở free tier chặt hơn — cần tính vào NFR-1 khi load test thật. Giá/tên model đổi rất nhanh — kiểm tra lại `ai.google.dev/gemini-api/docs/pricing` trước khi code |
| OpenAI | GPT-4o-mini: ~$0.15 input / $0.60 output · GPT-4o: ~$2.50 input / $10 output | Không có free tier (chỉ credit dùng thử ban đầu) | Hệ sinh thái mature nhất, tài liệu nhiều nhất, phổ biến nên dễ tìm hỗ trợ khi lỗi | Đắt hơn Gemini ~2x ở tier rẻ, không có free tier lâu dài |
| Anthropic Claude | Haiku: ~$0.80 input / $4 output · Sonnet: ~$3 input / $15 output | Không có free tier lâu dài | Chất lượng suy luận tốt, an toàn/guardrail-friendly | **Đắt nhất trong 3** ở cả 2 tier — không hợp ngân sách SV làm chính, có thể dùng làm fallback |

**Kết luận: chọn Google Gemini làm nhà cung cấp chính** — quyết định thuần tuý vì chi phí (rẻ nhất + free tier hào phóng nhất, đúng trọng tâm "chi phí có thể cân được" của team) và tiện lợi vận hành (1 nhà cung cấp cho cả LLM + embedding). OpenAI `gpt-4o-mini` giữ vai trò fallback dự phòng (mục 4.1 file `02-SRS.md`) vì phổ biến, dễ chuyển đổi qua lớp abstraction (LiteLLM/OpenRouter) nếu Gemini gặp sự cố.

### Lớp Database + Vector Search

| Công cụ | pgvector/vector support | Free tier | Ưu điểm | Nhược điểm | Khuyến nghị |
|---|---|---|---|---|---|
| **Supabase (đã chọn)** | pgvector có sẵn, bật 1 click | 500MB DB, không giới hạn thời gian | Gộp DB+Auth+Storage+RLS làm 1 (lý do đã chọn ở mục 1) | Compute vector search không mạnh bằng dịch vụ vector chuyên biệt khi dữ liệu lớn (>1 triệu vector) | **Giữ nguyên** — ở quy mô ~50-500 chunk/môn × vài chục môn, compute không phải vấn đề |
| Neon | pgvector có sẵn qua extension | Free tier hào phóng (branching DB miễn phí — hữu ích để test schema mới không sợ hỏng data thật) | Serverless Postgres, tự động scale-to-zero tiết kiệm chi phí hơn nữa | Không có Auth/Storage tích hợp sẵn như Supabase — phải tự ghép thêm (mất đúng lợi thế "gộp 3 thứ" đã chọn Supabase vì lý do này) | Chỉ chọn nếu KHÔNG cần Auth/Storage tích hợp (không phải trường hợp của Cursus) |
| Qdrant Cloud | Vector DB chuyên biệt, không phải Postgres | Free tier 1GB | **Nhanh hơn pgvector đáng kể ở quy mô lớn** (chỉ số HNSW tối ưu riêng cho vector, không phải extension gắn thêm vào Postgres) | Phải đồng bộ dữ liệu 2 nơi (metadata ở Supabase, vector ở Qdrant) — phức tạp hơn, đúng như đã quyết định loại bỏ ở bản v1 | Chỉ đáng cân nhắc nếu **thật sự ingest tới hàng trăm nghìn chunk** (quy mô đồ án hiện tại — vài nghìn chunk cho ~10-50 môn — chưa cần) |
| Pinecone | Vector DB chuyên biệt | Free tier có nhưng giới hạn mạnh (1 index) | Managed hoàn toàn, dễ dùng | Không có SQL, phải tự quản metadata riêng, hệ sinh thái đắt khi scale thật | Không cần cho quy mô này |

**Kết luận lớp này:** pgvector qua Supabase là lựa chọn đúng ở quy mô hiện tại (không phải vì rẻ mà vì đơn giản hoá kiến trúc — 1 DB thay vì 2 hệ thống phải đồng bộ). Đổi sang Qdrant/Pinecone chỉ hợp lý khi đã có bằng chứng thật (đo latency query vector chậm) — không đổi vì "nghe nói mạnh hơn".

### Lớp Cache

| Công cụ | Free tier | Ưu điểm | Nhược điểm | Khuyến nghị |
|---|---|---|---|---|
| **Upstash Redis (khuyến nghị)** | Có, 10.000 lệnh/ngày free | Serverless, không cần quản VM, tính phí theo request nên rẻ ở traffic thấp | Giới hạn số lệnh/ngày ở free tier | **Chọn cái này thay vì Railway Redis addon** — Railway Redis addon tính vào compute cost chung, Upstash tách riêng và có free tier rõ ràng hơn |
| Railway Redis addon | Không free vĩnh viễn (cộng vào bill Railway) | Cùng hạ tầng với Backend, latency thấp hơn 1 chút (cùng region) | Tốn thêm chi phí cố định | Chỉ chọn nếu đã dùng hết free tier Upstash |

### Lớp Observability (error tracking + monitoring)

| Công cụ | Free tier | Ưu điểm | Nhược điểm | Khuyến nghị |
|---|---|---|---|---|
| **Sentry (khuyến nghị — đã chốt ở `02-SRS.md` NFR-10)** | 5.000 error events/tháng free | Setup 5 phút (1 dòng SDK cho cả FastAPI và Next.js), alert email tự động, thấy được stack trace thật khi lỗi xảy ra ở production | Free tier giới hạn số event, không phải vấn đề ở quy mô demo | **Chọn** — đáp ứng đúng yêu cầu "theo dõi lỗi" của Quy định chung mục 4 với chi phí 0đ |
| Railway/Vercel built-in logs | Có sẵn, không cần cài thêm | Không tốn công setup | Chỉ là log thô, không group lỗi theo loại, không alert tự động | Dùng bổ sung (xem log nhanh), không thay được Sentry cho phần "biết ngay khi có lỗi mới" |
| Grafana + Prometheus (self-host) | Free nếu tự host | Mạnh, tuỳ biến sâu, đúng "chuẩn production" cấp doanh nghiệp | **Quá nặng cho quy mô đồ án** — tốn công setup/vận hành không tương xứng lợi ích | Không khuyến nghị — over-engineering rõ ràng, đúng tinh thần "Không cần cho production của riêng sản phẩm này" đã ghi ở `07` |

### Lớp CI/CD

| Công cụ | Free tier | Khuyến nghị |
|---|---|---|
| **GitHub Actions** | 2.000 phút/tháng free cho repo private (đủ dùng cho team nhỏ) | **Chọn** — chạy thẳng trên repo BTC hiện tại (chỉ cần quyền push, không cần quyền admin/OAuth như Vercel/Railway/Supabase — xem `0.7`), test tự động mỗi lần push, không cần thêm tài khoản dịch vụ khác |

---

## 2. Stack hạ tầng chốt cuối (bản thay thế bảng cũ)

| Thành phần | Chọn | Vai trò |
|---|---|---|
| Frontend | Next.js trên **Vercel** (Hobby, free — phi thương mại) | Giao diện |
| **Database + pgvector + Auth + Storage** | **Supabase** (Free tier, nâng Pro $25/tháng khi cần) | DB, vector search, đăng nhập (mặc định email+mật khẩu, Google OAuth tuỳ chọn — mục 4.A), phân quyền RLS, lưu file syllabus gốc |
| Backend compute (FastAPI + LangGraph agent) | **Railway** (Hobby, ~$5-15/tháng thực tế) | Chạy logic Planner/Doer/Reflector/Guardrail — Supabase không chạy được phần này |
| LLM + Embedding API | **Google Gemini** (`gemini-2.5-flash-lite` + `gemini-2.5-flash` + `gemini-embedding-001`) — đã chốt, xem so sánh chi phí mục 1.5 (cập nhật 10/08/2026, tên model cũ đã ngừng hoạt động thật) | Model routing theo `02-SRS.md` mục 4.1, fallback OpenAI `gpt-4o-mini` nếu cần |
| Reranker (Mốc 3 — Must, xem `02-SRS.md` FR-3.1/4.1) | `bge-reranker-v2-m3` qua HuggingFace Inference API (free tier đủ cho quy mô demo) | Vượt naive RAG, bắt buộc cho PLO3 |
| Cache (Should, làm nếu dư giờ Mốc 3) | **Upstash Redis** (free tier — xem so sánh mục 1.5) | Giảm chi phí câu hỏi lặp lại |
| Observability (Mốc 3 — Must) | **Sentry** (free tier — xem mục 1.5) | Error tracking BE+FE, đáp ứng Quy định chung mục 4 |
| CI/CD | **GitHub Actions** (free, chạy trực tiếp trên repo BTC — xem mục 0.7) | Test tự động khi push code |

### 2.1. Ngân sách chi phí tổng — 3 giai đoạn (trả lời trực tiếp "chi phí có thể cân được")

| Giai đoạn | Vercel | Supabase | Railway | Gemini API | Reranker/Sentry/Upstash | **Tổng/tháng** |
|---|---|---|---|---|---|---|
| **Gate 2** (~60% dự án — Plan/QA+reranker, Reflect, Dashboard GV, guardrail nâng cấp, Sentry, RAGAS, ≤20 concurrent) | $0 (free) | $0 (free tier) | ~$8-15 (Hobby, có Usage Alert chặn vượt) | ~$1-3 (nằm trong free tier Gemini phần lớn, reranker qua HF free tier) | $0 (Sentry free tier) | **~$8-18/tháng** |
| **Mốc 3** (hoàn thiện — Admin Console, Auth thật, mở rộng ingest/eval, LLM-as-Judge, load test) | $0 | $0 | ~$10-15 | ~$2-5 (LLM-as-Judge gọi thêm) | $0 (tất cả free tier) | **~$12-20/tháng** |
| **Nếu 1.000 SV thật dùng (ngoại suy, KHÔNG phải chi phí hiện tại)** | $20 (Pro, nếu vượt bandwidth free) | $25 (Pro, cần compute mạnh hơn) | $20-40 (Pro + resource cao hơn) | ~$20-60 (tuỳ tần suất hỏi thật/SV/tuần — biến động lớn nhất, cần model routing nghiêm ngặt để giữ mức này) | ~$5-10 (Upstash/Sentry vượt free tier) | **~$90-155/tháng** |

**Kết luận ngân sách:** chi phí thật trong suốt giai đoạn đồ án (Gate 2 → Mốc 3) nằm trong khoảng **$5-20/tháng**, hoàn toàn trong tầm 1 sinh viên tự trả nếu cần. Mức "1.000 SV thật" chỉ là ngoại suy minh hoạ (đúng NFR-1b/1c ở `02-SRS.md`), không phải chi phí phải trả bây giờ — nhưng có con số này sẵn để trả lời tự tin nếu giám khảo hỏi "vậy sau này chi phí thế nào".

### 2.2. Team có ngân sách 8.000.000đ (~$310, một lần, dùng dần cho cả đồ án) — nên phân bổ thế nào

> Với mức chi thật ~$5-20/tháng ở trên, ngân sách $310 **dư sức chi cho toàn bộ Gate 2 → Mốc 3 (14 ngày, hạn nộp 23/08) ngay cả ở mức free tier**, tức là **không bắt buộc phải nâng cấp gì để "đủ tiền chạy"** — ngân sách này nên dùng để **mua độ tin cậy khi demo/nộp bài**, không phải để chạy được, vì free tier vốn đã đủ chạy.

| Nâng cấp nên mua bằng ngân sách này | Chi phí | Lý do đáng mua (giải quyết đúng gap còn "chưa có" ở `07`) |
|---|---|---|
| **Supabase Pro ($25/tháng, chỉ cần trả 1 tháng ≈ $25 vì deadline chỉ 14 ngày)** | Ưu tiên #1 | Giải quyết 2 rủi ro thật: (1) **free tier tự tạm dừng project sau 7 ngày không ai truy cập** — nguy hiểm nếu giám khảo chấm bài cách ngày nộp vài ngày, project có thể đang "ngủ", lần request đầu chậm hoặc lỗi; (2) **có backup tự động hàng ngày (point-in-time recovery)** — giải quyết thẳng mục "Backup & Disaster Recovery" đang để trống ở `07-Production-Readiness-Checklist.md` |
| **Custom domain (~$12-15/năm, VD `cursus-app.com` hoặc `.io`)** | Rất rẻ | URL demo nhìn "sản phẩm thật" thay vì `xxx.vercel.app`/`xxx.up.railway.app` — ấn tượng đầu tiên với giám khảo, chi phí không đáng kể so với ngân sách |
| **Railway Pro ($20/tháng × 1-2 tháng ≈ $20-40, chỉ nâng lúc gần Gate 2/Mốc 3)** | Nếu cần | Resource cao hơn, priority support, ổn định hơn khi giám khảo test đúng lúc cao điểm — không bắt buộc nếu Hobby vẫn chạy mượt khi test thử |
| **HuggingFace Inference Endpoint riêng cho reranker (~$0.05-0.1/giờ, bật lúc cần demo, tắt lúc không dùng ≈ $10-20 tổng)** | Nếu muốn chắc chắn | Free tier Inference API có thể cold-start/rate-limit đúng lúc demo — endpoint riêng trả theo giờ, chỉ bật quanh thời điểm Gate 2/Mốc 3/pitch, tắt ngay sau đó để không tốn phí |
| **Credit Gemini trả phí cho load test k6 2.500 concurrent (~$25-50, chỉ bật đúng khung giờ chạy test ở Mốc 3)** | Bắt buộc cho NFR-1c | Dù đã có 5-10 API key xoay vòng (`02-SRS.md` mục 4.2 lớp 1, miễn phí) nhân hạn mức lên nhiều lần, 2.500 concurrent vẫn có thể chạm trần tổng — cần thêm credit trả phí làm lớp dự phòng cuối cùng, tắt lại ngay sau khi test xong |
| **Còn dư (~$120-180)** | Dự phòng | Giữ lại làm quỹ dự phòng nếu phát sinh chi phí ngoài dự kiến (VD cần đổi sang Google Cloud Run, hoặc chi phí LLM vượt dự kiến ở giai đoạn khác) |

**Không nên dùng ngân sách để mua:** Kubernetes/AWS enterprise-grade services, multi-region deploy, GPU riêng để tự host reranker/LLM — tất cả đều over-engineering so với quy mô đồ án, đã loại rõ ở `07` mục 2 "Không cần cho production của riêng sản phẩm này". Có ngân sách không có nghĩa nên tiêu hết — chi đúng chỗ quan trọng hơn chi nhiều.

---

## 3. Đánh giá ở quy mô 2.000 người dùng — từng lớp một

> Đây là đánh giá **để biết trước sẽ vướng ở đâu**, không phải việc phải làm ngay — tới Gate 2 vẫn theo đúng quy mô demo nhỏ.

| Lớp | Ở quy mô demo (~12-50 người, tương ứng ≤20 request đồng thời theo NFR-1 trong `02-Cursus-SRS.md`) | Ở quy mô 2.000 người | Cần làm gì để lên được mức 2.000 |
|---|---|---|---|
| Vercel (FE) | Free tier đủ dư | Free tier có thể chạm giới hạn băng thông/function invocation nếu 2.000 người dùng đồng thời | Nâng Pro ($20/tháng), tự động scale, không cần đổi kiến trúc |
| Supabase (DB+Auth) | Free tier dư sức | Auth: 2.000 MAU vẫn nằm rất xa dưới ngưỡng 50.000 MAU free tier — **không phải nâng cấp vì lý do Auth**. DB: cần theo dõi dung lượng (500MB) — text chunk syllabus khá nhẹ, khả năng vẫn đủ, nhưng nên nâng Pro để có compute mạnh hơn cho truy vấn vector đồng thời nhiều | Nâng Supabase Pro ($25/tháng) chủ yếu vì **compute** (tốc độ query vector khi nhiều người hỏi cùng lúc), không phải vì hết dung lượng |
| Railway (Backend Python) | 1 instance nhỏ đủ chạy | **Đây là điểm nghẽn thật sự** — Railway không tự động scale ngang như serverless, phải tự tăng RAM/CPU (vertical) hoặc tự dựng nhiều instance (horizontal, phức tạp hơn). LangGraph agent giữ state per-request có thể tốn RAM nếu nhiều phiên đồng thời | Cần: (1) đo tải thật bằng load test trước khi khẳng định con số, (2) tách các tác vụ nặng (sinh embedding, gửi notification) ra hàng đợi (queue) chạy nền thay vì xử lý đồng bộ trong request, (3) cân nhắc caching câu hỏi lặp lại (Redis) để giảm số lần phải gọi LLM+DB |
| Chi phí LLM | Vài đô/tuần | **Đây là chi phí tăng nhanh nhất, không phải hạ tầng** — 2.000 SV hỏi + lập kế hoạch + phản tư hàng tuần có thể lên hàng trăm đô/tháng nếu không kiểm soát | Bắt buộc: model routing (việc đơn giản dùng model rẻ), giới hạn tần suất gọi model đắt (Reflect 1 lần/tuần/SV — đã có trong SRS), cache câu hỏi phổ biến |
| Guardrail/RAG chất lượng | Test bằng tay vài chục câu là đủ tin | Cần bộ test lớn hơn, theo dõi tỷ lệ lỗi theo thời gian thực (không chỉ test 1 lần) | Bổ sung eval pipeline chạy định kỳ (không chỉ chạy 1 lần lúc bàn giao) |

**Kết luận về "2.000 người":** hạ tầng đã chọn (Vercel+Supabase+Railway) **không cần đổi kiến trúc** để lên 2.000 người — chỉ cần nâng cấp gói trả phí đúng chỗ (chủ yếu Railway compute + kiểm soát chi phí LLM), không phải viết lại từ đầu. Đây là điểm cộng khi giám khảo hỏi "sao biết scale được" — có thể trả lời đúng bằng bảng này thay vì chỉ nói "chắc được".

---

## 4. Gate 2 — cái gì đã chốt Must, cái gì còn là lựa chọn thêm giờ dư

> **Đã nâng phạm vi Gate 2 lên ~60% dự án** (xem `01-Cursus-PRD.md` mục 8.1, `03-Cursus-Execution-Plan.md`) — Reflect, Dashboard GV, reranker, guardrail nâng cấp giờ đều là **Must ở Gate 2**, không còn là "nâng cấp tuỳ chọn" như bản trước. Dùng Supabase cho DB+pgvector+Storage (mục 2) đã chốt từ đầu — chi phí setup gần như bằng tự host, không có lý do thật để trì hoãn. Bảng dưới đây chỉ còn liệt kê các hạng mục **thật sự tuỳ chọn** (không ảnh hưởng tới việc coi Gate 2 là đạt).

> **Đã vượt qua (12/08/2026):** cả 2 lựa chọn A/B dưới đây đều đã làm — nhưng theo hướng khác với dự kiến ban đầu (invite-only, không phải form tự đăng ký công khai). Xem `ADR-007` và `10-Cursus-Auth-Onboarding-Sandbox-Spec.md`. Giữ nguyên bảng dưới để biết lý do cân nhắc ban đầu, không xoá lịch sử.

| Nâng cấp có thể thêm vào Gate 2 nếu dư giờ | Lợi ích | Cái giá phải trả (thời gian/rủi ro) | Gợi ý khi nào nên chọn |
|---|---|---|---|
| **A. Bật Auth Google OAuth qua Supabase Auth** (thay vì demo-login chọn role không mật khẩu) | Nhìn "production" hẳn, không cần sửa lại ở Mốc 3 nữa | Cần ~1-2 giờ setup (cấu hình Google OAuth trong Supabase) | Nên chọn nếu Người A/C đã từng dùng Supabase Auth/Google OAuth trước đây; nếu chưa ai dùng qua, có rủi ro học công cụ mới giữa lúc gấp — **mặc định Gate 2 vẫn là demo-login (F1, xem `00`), Auth 3 role thật để dành Mốc 3** |
| **B. Auth thật (không hardcode) nhưng KHÔNG dùng Google** — form đăng ký/đăng nhập email thường qua Supabase Auth | Nhìn thật hơn "chọn role" nhưng không tốn công OAuth | Vẫn cần code form + validate (Supabase Auth tự lo hash password) | Chọn nếu muốn "thật" mà không muốn cấu hình OAuth gấp |
| **C. Notification bell tĩnh** (không có logic thật, chỉ hiện UI có sẵn 1-2 thông báo mẫu) | Cho thấy có nghĩ tới tính năng này mà không tốn công backend | ~30 phút FE | Gần như luôn nên làm — chi phí thấp, hiệu quả demo cao |
| **D. Biểu đồ GV chi tiết hơn** (thêm filter theo tuần, hover xem số liệu) — bổ sung cho Dashboard GV đã là Must | Dashboard nhìn chuyên nghiệp hơn | ~1-2 giờ FE, cần thư viện chart (Recharts/Chart.js) | Chọn nếu Người C code UI nhanh, còn dư giờ sau khi Dashboard cơ bản đã xong |

**Gợi ý cách chọn:** ưu tiên **C** (rẻ, hiệu quả cao), rồi **B** hoặc **A** tuỳ năng lực team, **D** chỉ nếu Dashboard GV cơ bản đã ổn định và còn dư giờ thật sự.

---

## 5. Cách xử lý kỹ thuật cho từng tính năng — MENU lựa chọn, không chốt 1 hướng

> Đây là phần bạn phàn nàn đúng nhất — lần trước mình chốt cứng 1 cách (VD "tạm dùng in-memory cosine similarity"). Giờ liệt kê phương án thật, có đánh đổi, để Người A/B tự quyết theo năng lực thật của mình.

### Retrieval (tìm đoạn syllabus liên quan cho F2/F3)

**Gate 2 (Must, đầy đủ ngay từ đầu):** pgvector qua Supabase + reranker `bge-reranker-v2-m3` (fallback in-memory chỉ nếu setup pgvector vượt quá 30 phút — xem `03-Cursus-Execution-Plan.md` ngày 09/08). Kiến trúc đầy đủ ở `02-SRS.md` mục 1.4.

| Phương án | Ưu điểm | Nhược điểm | Trạng thái |
|---|---|---|---|
| **pgvector qua Supabase + reranker `bge-reranker-v2-m3`** | Chuẩn production, vượt naive RAG (bắt buộc PLO3), reranker free qua HF Inference API | Cần biết viết SQL query có `<->` (cosine distance) + thêm 1 lệnh gọi API rerank (~200-500ms latency thêm, chấp nhận được vì vẫn trong ngưỡng NFR-1 ≤5s) | **Đã chọn, làm ngay từ Gate 2** |
| pgvector qua Supabase, không reranker | Đơn giản hơn, latency thấp hơn | Naive RAG thuần — không đạt PLO3 | Chỉ chấp nhận tạm thời nếu 09-10/08 chưa kịp tích hợp reranker, PHẢI bổ sung trước khi coi Gate 2 hoàn thành |
| In-memory (Python list + numpy cosine) | Không cần setup DB, code nhanh trong 30 phút | Không scale được, phải viết lại hoàn toàn | Chỉ dùng làm fallback tạm thời ngày 09/08 nếu bí giờ, PHẢI chuyển sang pgvector trước khi hết Gate 2 |
| Elasticsearch/Qdrant riêng + reranker | Mạnh hơn cho tìm kiếm phức tạp ở quy mô lớn | Thừa thãi ở quy mô demo hiện tại (xem so sánh chi tiết mục 1.5) | Không chọn — over-engineering so với quy mô dữ liệu thật (vài nghìn chunk) |

### Guardrail (chặn "làm hộ bài")
| Phương án | Ưu điểm | Nhược điểm |
|---|---|---|
| Rule-based (regex/keyword list) | Code trong 30 phút, dễ giải thích cho giám khảo (minh bạch) | Dễ bị lách bằng cách diễn đạt khác đi |
| Rule-based + LLM classifier nhẹ (gọi model rẻ hỏi "đây có phải yêu cầu làm hộ bài không") | Bắt được nhiều biến thể hơn | Tốn thêm 1 lần gọi LLM mỗi câu hỏi (chi phí + độ trễ tăng nhẹ) |
| Dùng sẵn moderation API của nhà cung cấp LLM (nếu có) | Không tự viết logic, được maintain sẵn | Có thể không đúng chuyên biệt cho "làm hộ bài học thuật" (moderation API thường bắt nội dung độc hại chung, không chuyên bắt gian lận học thuật) |

**Khuyến nghị:** Gate 2 dùng luôn rule-based + LLM classifier (đã nâng phạm vi — `02-SRS.md` mục 3.5); Mốc 3 chỉ còn việc tinh chỉnh threshold/prompt tới khi đạt ≥90%.

### Sinh task từ syllabus (F2 — Plan), cách viết prompt cho Planner node

> Trước đây chỉ ghi "LLM chia 3-7 task kèm ước lượng thời gian" mà không nói cách đảm bảo LLM không bịa việc ngoài syllabus — bổ sung 3 phương án.

| Phương án | Cách làm | Ưu điểm | Nhược điểm |
|---|---|---|---|
| **Structured output bắt buộc trích `chunk_id` nguồn cho mỗi task (khuyến nghị)** | Prompt yêu cầu LLM trả JSON, mỗi task PHẢI có field `source_chunk_id` trỏ đúng 1 trong các chunk đã đưa vào context; sau khi LLM trả lời, code kiểm tra lại `source_chunk_id` có nằm trong tập chunk đã retrieval không — nếu không, loại task đó khỏi kết quả (không hiển thị task không có nguồn hợp lệ) | Chặn được việc LLM "bịa" task không liên quan tới chunk thật — đúng tinh thần chống bịa của cả sản phẩm | Cần thêm 1 bước validate sau khi nhận response LLM, không phải trả thẳng cho FE |
| Prompt tự do, tin tưởng LLM tự trích đúng | Chỉ yêu cầu LLM "chia task kèm nguồn", không validate lại | Code đơn giản, nhanh | Rủi ro LLM tự ghi `source_label` không khớp chunk thật (hallucination nguồn) — vi phạm trực tiếp yêu cầu "mọi câu trả lời RAG bắt buộc có trích nguồn" đúng nghĩa ở `02` mục 1.3 |
| Retrieval + rule-based template (không dùng LLM sinh task tự do) | Mỗi chunk có sẵn 1 template task cố định (VD chunk "Session X — Project" → luôn sinh task "Đọc yêu cầu Session X và bắt đầu Project") | Không có rủi ro bịa, chi phí LLM = 0 cho bước này | Task cứng nhắc, không phản ánh đúng mục tiêu tự nhiên SV gõ vào — đi ngược yêu cầu "chia nhỏ theo mục tiêu SV nhập" của FR-3.1 |

**Khuyến nghị:** dùng phương án 1 (structured output + validate `source_chunk_id`) — chi phí thêm không đáng kể so với rủi ro bịa nguồn, và đây là đúng NFR-3 (guardrail/validate trước khi trả kết quả cuối).

### Notification (job quét deadline 48h)
| Phương án | Ưu điểm | Nhược điểm |
|---|---|---|
| Cron job đơn giản trong chính Railway (APScheduler/Python) | Không cần thêm hạ tầng | Nếu Railway service restart, job có thể bị gián đoạn (chấp nhận được ở quy mô demo) |
| Supabase Edge Function + pg_cron | Chạy trong chính Supabase, không cần Railway lo | Cần học thêm 1 công cụ mới (pg_cron), có thể không đáng ở giai đoạn gấp |
| Queue thật (Celery/Redis) | Chuẩn production, sẵn sàng cho 2.000 người | Quá nặng cho tới Gate 2, chỉ nên cân nhắc ở Mốc 3 nếu thật sự cần |

---

## 6. Bản đồ toàn bộ docs — bộ 9 file chốt, đã dọn sạch bản nháp

| # | File | Dùng để làm gì |
|---|---|---|
| 00 | `00-Cursus-Playbook.md` | **Đọc đầu tiên khi bắt tay code cho Gate 2** — feature spec F1-F7 đầy đủ input/output, tech stack, quy trình dữ liệu, phân công 4 người, kịch bản demo chính + kịch bản demo lỗi |
| 01 | `01-Cursus-PRD.md` | Phạm vi sản phẩm, MVP theo mốc (Gate 2 → Mốc 3), value proposition, persona |
| 02 | `02-Cursus-SRS.md` | Đặc tả FR/NFR chi tiết cấp hệ thống |
| 03 | `03-Cursus-Execution-Plan.md` | Lịch trình (Gate 2 → Mốc 3 hoàn thiện) |
| 04 | `04-Cursus-Terminology.md` | Thuật ngữ, onboard người mới vào team |
| 05 | `05-Cursus-Competitive-Analysis.md` | Đối thủ, câu trả lời khi bị hỏi lúc pitch |
| 06 | `06-Cursus-Ha-tang-Supabase-Scale2000.md` (**file này**) | Hạ tầng chốt cuối, đánh giá quy mô 2.000 người, menu lựa chọn kỹ thuật |
| 07 | `07-Cursus-Production-Readiness-Checklist.md` | Đánh giá kỹ thuật — docs còn thiếu gì để "chuẩn production" (Mốc 3) |
| 08 | `08-Cursus-Deliverables-Checklist.md` | Tra cứu nhanh 10 deliverable BTC + thang điểm 50 (tách từ `07` ngày 10/08/2026) |

**Không còn file nháp/deprecated nào trong thư mục** — 3 bản cũ (đặc tả sản xuất chi tiết riêng, tech stack bản đầu, đánh giá quy trình riêng) đã được gộp thẳng vào file `00` và `06` ở trên, đã xoá khỏi thư mục để tránh đọc nhầm bản cũ. `08` là file mới tách ra (không phải nháp) — xem lý do tách ở đầu file đó.

**File dữ liệu/code đi kèm (không đổi):** `flm_parser.py`, `gen_seed_students.py`, `courses_BIT_SE_K20D_K21A.json`, `chunks_SSA101.json`, `seed_students_SSA101.json`.

**Thứ tự đọc nếu bắt đầu từ đầu:** `00` (việc cần làm ngay) → `01-02-03` (bối cảnh sản phẩm/kỹ thuật/lịch trình) → `06` (hạ tầng) → `04-05-07-08` (tham khảo khi cần).

---

*File dữ liệu không đổi, vẫn dùng: `flm_parser.py`, `courses_BIT_SE_K20D_K21A.json`, `chunks_SSA101.json`, `seed_students_SSA101.json`, `gen_seed_students.py`.*
