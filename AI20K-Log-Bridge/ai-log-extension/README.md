# AI20K Log Bridge — Chrome/Edge extension

Bắt prompt AI trên **mọi trang chat**, cho bạn **duyệt trước**, rồi gửi thẳng lên
grading server. Không cần terminal, không cần `git push`, không bó vào một AI nào.

## Tại sao phải là extension

Cách hiển nhiên hơn — một trang HTML tự `fetch()` lên server — **không chạy được**.
Server chặn mọi origin của browser:

```
$ curl -X OPTIONS https://ai-logs.note.transformerlabs.ai/api/ingest \
       -H "Origin: null" -H "Access-Control-Request-Method: POST"
HTTP/1.1 400 Bad Request
Disallowed CORS origin
```

Đã thử `null` (file://), `localhost:3000`, `localhost:8000`, `127.0.0.1:5500`,
`claude.ai`, `chatgpt.com` — không origin nào được cấp `Access-Control-Allow-Origin`.

Extension đi vòng qua: service worker khai báo `host_permissions` thì request của
nó **không chịu ràng buộc CORS**. Server không cần đổi gì. Đó là lý do mọi lệnh
`fetch` đều nằm trong `background.js` — content script chạy dưới origin của trang
nên vẫn bị chặn y như trang HTML thường.

## Cài đặt

Mở popup → mục **Bắt đầu** có checklist trực tiếp và hướng dẫn từng bước. Dưới
đây là bản đầy đủ.

### Bước 1 — nạp extension

1. Mở `chrome://extensions` (Edge: `edge://extensions`)
2. Bật **Developer mode** (góc phải trên)
3. **Load unpacked** → chọn thư mục `tools/ai-log-extension`
4. Kiểm tra **ID** hiện ra phải đúng `cheofncpckkpmfjoeflampnmainmblac`

ID khác nghĩa là trường `key` trong `manifest.json` không được đọc — native host
sẽ **im lặng không trả lời**, vì nó chỉ cho phép đúng ID này.

### Bước 2 — server và API key

Click icon → **Cấu hình** → điền:

| Ô | Lấy ở đâu |
|---|---|
| Server URL | `.env`, dòng `AI_LOG_SERVER` |
| API Key | `.env`, dòng `AI_LOG_API_KEY` |

**Lưu cấu hình** → **Test kết nối**. Đúng thì hiện `HTTP 202`.

Không có `.env` thì hỏi BTC hai giá trị này. Đây là hai ô duy nhất bắt buộc gõ tay.

### Bước 3 — native host: một lệnh, vừa cài vừa kiểm tra

Không có nó thì commit lấy từ GitHub — chỉ thấy commit **đã push**. Có nó thì lấy
đúng commit trên máy kể cả chưa push, và tự điền repo, branch, email.

```
tools\ai-log-extension\setup.cmd --server
```
```bash
bash tools/ai-log-extension/setup.sh --server     # macOS / Linux
```

Trên Windows nhấn đúp vào `setup.cmd` cũng chạy được.

Lệnh này cài rồi **kiểm tra ngay 14 mục**: Python, git, đường dẫn repo có đúng
gốc không, host trả lời được không, launcher, manifest native, đăng ký cho Chrome
và Edge, extension ID đã ghim, `.env`, và gọi thử grading server. Mục nào hỏng đều
kèm cách sửa. Chạy lại bao nhiêu lần cũng được.

| Tuỳ chọn | Làm gì |
|---|---|
| `--check` | chỉ kiểm tra, không ghi gì |
| `--server` | gọi thử grading server (batch rỗng, không ghi log nào) |
| `--repo "D:\duong\dan"` | repo ở chỗ khác — phải là **gốc repo**, thư mục chứa `.git` |
| `--uninstall` | gỡ đăng ký native host |

Sau đó **khởi động lại trình duyệt**. Bắt buộc: Chrome chỉ đọc đăng ký native
host lúc khởi động, không restart thì vẫn báo "chưa cài" dù đã cài xong.

### Bước 4 — quay lại popup

Mục **Bắt đầu** → **Kiểm tra tất cả**. Nó soi từ phía trình duyệt: cấu hình,
server, repo, native host, site đang bật, và trang bạn đang mở có được ghi log
không. Mục nào hỏng hiện luôn cách sửa ngay dưới.

Đủ xanh là xong. Mục màu vàng là tuỳ chọn, không chặn.

Cần Chrome/Edge **111+**.

## Khi có gì đó không chạy

Hai công cụ, soi từ hai phía:

| | Xem được gì |
|---|---|
| `setup.cmd --check` (terminal) | phía máy: Python, git, registry, launcher, manifest, đường dẫn repo |
| **Kiểm tra tất cả** (popup) | phía trình duyệt: cấu hình, server, native host có trả lời không, site đang bật |

Cả hai đều liệt kê từng mục kèm cách sửa, thay vì một dòng lỗi chung chung.

Chi tiết hơn nữa xem [TESTING.md](TESTING.md) — quy trình 7 tầng, mỗi tầng cô lập
đúng một chỗ có thể hỏng.

## Bật / tắt

Hai công tắc, cả hai **ăn ngay, không cần tải lại trang**:

- **Công tắc tổng** ở header — tắt là ngừng bắt trên mọi site. Badge hiện `off`
  màu xám để bạn không quên mình đang tắt.
- **Công tắc theo site** ở đầu popup — chỉ ngừng cho đúng trang bạn đang mở.
  Hợp với trường hợp "riêng cuộc này là chuyện riêng".

Tắt còn xoá luôn bản nháp đang theo dõi, nên câu bạn gõ dở trước lúc tắt cũng
không nổi lên sau đó. Log nhập tay trong popup vẫn gửi được kể cả khi đang tắt —
nó là hành động chủ ý.

## Kết nối repo

Ba cách, chọn cách nào cũng được. Cái gì máy tự trả lời được thì đừng gõ tay.

### Tự quét (không cần làm gì)

Có native host thì lúc cài extension và mỗi lần mở trình duyệt, nó tự đọc repo,
branch, email, commit **và cả link GitHub** (suy từ `git remote origin`).

Quy tắc ghi đè cố ý không đối xứng:

| Trường | Hành vi |
|---|---|
| `commit`, và `branch` ở chế độ auto | luôn bám theo repo — chúng cũ đi từng phút |
| `repo`, `student`, link GitHub, đường dẫn | chỉ điền khi đang trống |

Nghĩa là bạn sửa tay một trường thì lần khởi động sau **không** bị ghi đè lại.

### Dán link (không cần native host)

Dán link từ thanh địa chỉ vào ô **Link repo GitHub** rồi bấm **Kết nối**. Nhận
mọi dạng: `https://github.com/o/r`, `o/r`, `git@github.com:o/r.git`,
`https://github.com/o/r/tree/feature/x`.

Link dạng `/tree/<branch>` thì ghim luôn branch đó. Link tới file trong branch
cũng được — `/tree/feature/x/src/app.js` vẫn ra branch `feature/x`, vì phần đuôi
được đối chiếu với danh sách branch thật thay vì đoán chỗ cắt.

Nút **Kiểm tra** cho biết link trỏ tới đâu — repo nào, mấy branch, private hay
không, có khớp repo đang lưu không — mà **không sửa gì**. Dùng để soi trước khi
quyết định.

### Lấy từ repo trên máy

Nút **Hoặc lấy từ repo trên máy** ghi đè toàn bộ bằng giá trị thật của checkout.
Đây là hành động chủ ý nên nó ghi đè cả trường đã có.

## Commit tự lấy

Hai nguồn, thử theo thứ tự.

### Nguồn 1 — native host (chính xác tuyệt đối)

Cài một lần bằng `setup.cmd` (xem Bước 3), khởi động lại trình duyệt, rồi mở
popup → Cấu hình → **Lấy từ repo trên máy**.

Nó điền **cả bốn trường** cùng lúc — repo, branch, email, commit — bằng đúng
những lệnh `git` mà `log_hook.py` chạy, nên hai đường không bao giờ lệch nhau vì
gõ nhầm. Thấy được cả commit **chưa push**, và báo thêm repo có đang dirty không.

Cài đặt ghi 3 thứ, đều ở cấp user, không cần quyền admin:

| Thứ | Ở đâu |
|---|---|
| `run_host.bat` | cạnh script, trỏ tới Python của `.venv` |
| `host_config.json` | đường dẫn repo mặc định |
| Khoá registry `HKCU` | `Software\Google\Chrome\NativeMessagingHosts\com.ai20k.gitinfo` (và Edge) |

Extension ID được **ghim** bằng trường `key` trong `manifest.json`
(`cheofncpckkpmfjoeflampnmainmblac`), nên installer không phải hỏi bạn ID và ID
giống nhau trên mọi máy.

Ba file này chứa đường dẫn tuyệt đối của từng máy nên đã bị `.gitignore` — commit
vào là đồng đội nhận đường dẫn máy bạn và host trỏ sai chỗ.

Cài xong là kiểm tra luôn trong cùng một lệnh, vì một khoá registry trỏ vào
launcher hỏng trông y hệt một cái đang chạy tốt — cho tới khi Chrome âm thầm bỏ
cuộc vài tuần sau.

**Đường dẫn phải là gốc repo.** `git rev-parse --is-inside-work-tree` đi ngược
lên cây thư mục, mà thư mục home nhiều người lại là một git repo (dotfiles) — nên
gõ sai đường dẫn sẽ khiến host báo commit của một project hoàn toàn khác. Host bắt
buộc `toplevel == path` để sai là báo lỗi thay vì trả số sai.

### Nguồn 2 — GitHub API (dự phòng)

Không có native host thì dán link repo rồi **Kết nối**; repo private cần thêm
token scope `repo:read`. Tự làm mới mỗi 30 phút.

Giới hạn: đó là commit **đã push**. Có commit chưa push thì nó trễ hơn commit
thật. Popup ghi rõ nguồn là *từ máy* hay *từ GitHub* để bạn biết mình đang nhìn
con số nào.

### Chọn branch

Branch **không còn là ô gõ tay**. Bấm **Nạp lại** để lấy danh sách branch thật —
từ repo trên máy nếu có native host, không thì từ GitHub — rồi chọn trong
dropdown. Gõ sai tên branch từng là lỗi im lặng: commit sai, không báo gì.

Hai chế độ:

| | Theo branch đang dùng (mặc định) | Ghim một branch |
|---|---|---|
| Branch nào | branch repo đang checkout | branch bạn chọn |
| Đổi branch trên máy | log đi theo, không phải sửa gì | giữ nguyên branch đã ghim |
| Đọc được branch chưa checkout | không | có |

Dropdown hiện luôn commit của từng branch, chấm `•` đánh dấu branch đang
checkout, và dòng dưới cho biết branch đó **chưa có upstream** hay đang **ahead
mấy commit chưa push** — tức khoảng cách giữa commit thật và commit mà GitHub
nhìn thấy.

Chọn branch không tồn tại thì báo lỗi rõ, **không** âm thầm rơi về GitHub để lấy
đại một commit khác.

## Hai chế độ

Chuyển bằng nút ở góc trên popup.

| | Chờ duyệt (mặc định) | Tự động |
|---|---|---|
| Prompt bắt được | vào danh sách chờ, **chưa gửi đi đâu** | gửi ngay |
| Bạn làm gì | tick mục muốn gửi → **Gửi mục đã chọn** | không cần làm gì |
| Mục không muốn gửi | **Xoá mục đã chọn** — không bao giờ rời máy | — |

Chế độ **Chờ duyệt** là mặc định, vì hỏi AI một câu riêng tư rồi mới nhận ra nó
đã lên server thì không rút lại được.

Riêng log nhập tay trong popup thì gửi thẳng, không qua bước duyệt — bạn gõ nó ra
đã là hành động chủ ý rồi.

## Bắt log thế nào

Extension chỉ đọc **một thứ: ô soạn bạn gõ vào**.

```
Bạn gõ prompt rồi gửi
   ├─ Enter trên ô soạn            → bắt ngay
   └─ ô soạn bị xoá trắng sau khi  → xác nhận đã gửi (mọi site,
      bấm phím hoặc click            bất kể nút gửi trông thế nào)
                 ↓
         service worker: khử trùng, gắn 13 trường, xếp hàng
                 ↓
         chờ duyệt  →  hàng đợi gửi  →  server (202)
```

**Chỉ đọc ô soạn, không đọc request của trang.** Từng có một đường thứ hai bọc
`fetch`/XHR để đọc body request đi ra. Nó bị bỏ vì không phân biệt được prompt của
bạn với traffic nội bộ của site — trong thực tế nó ghi cả `Turn exchange complete`
và `Failed to fetch persisted textdocs` lẫn vào prompt thật.

Đọc ô soạn thì không thể sinh ra thứ bạn không gõ. Đánh đổi: mất khả năng bắt
prompt gửi bằng cơ chế lạ, và model phải đọc từ giao diện thay vì từ payload.
Đúng thì quan trọng hơn đủ.

Việc xoá trắng ô soạn là tín hiệu **phổ quát** — mọi chat UI đều làm vậy sau khi
gửi — nên site mới vẫn bắt được mà không cần viết selector riêng.

### Model

Đọc từ widget chọn model trên trang, theo selector trong `adapters.js`. Site chưa
có selector thì trường `model` để trống — thà trống còn hơn điền sai.

## Site nào bị bắt log

Chỉ site trong danh sách **Site đang bật**. Bật sẵn: ChatGPT, Claude.ai (gồm
`claude.ai/code`), Gemini, AI Studio, Perplexity, DeepSeek, Grok.

**Chuyển sang AI chat mới thì không cần khai báo trước.** Một detector nhẹ chạy
trên mọi trang và chỉ đọc **cấu trúc** — có ô soạn lớn không, có nút gửi không,
có khối hội thoại lặp lại không, hostname trông thế nào. Nó không đọc nội dung,
không đụng request body, không gửi gì đi đâu. Khi thấy trang giống AI chat, popup
hiện *"Bật log cho site này?"* — bấm một cái là xong.

Chỉ **sau khi bạn bật**, script bắt log và hook mạng mới được đăng ký cho domain
đó. Ngân hàng, email, nội bộ công ty không bao giờ bị đọc body.

## Không mất log

- **Ghi hàng đợi trước, gửi sau.** Entry chỉ rời hàng đợi khi server đã xác nhận.
- **Mất mạng** → giữ nguyên, tự thử lại mỗi phút, badge vàng.
- **Sai tên repo** → server trả `mismatched_repos`, entry chuyển sang mục *Từ chối*
  (badge đỏ) chứ không bị vứt. Sửa repo rồi bấm **Gửi lại**.
- **Chưa cấu hình** → không POST nhưng vẫn giữ entry.
- Badge: đỏ = bị từ chối, xanh dương = chờ duyệt, vàng = chờ gửi.

## Lịch sử

Mục **Lịch sử đã gửi** liệt kê những gì đã lên server, kèm trạng thái. Nút xoá ở
đó chỉ xoá danh sách hiển thị — **log đã gửi lên server thì không thu hồi được**,
nên nếu có thứ không muốn gửi thì dùng chế độ Chờ duyệt.

## Chạy test

```bash
node tools/ai-log-extension/test/run.js
```

Stub `chrome.*` và `fetch` nên **không gửi gì lên server thật**. Hai bộ:

- `giturl.test.js` — 30 điểm: mọi dạng link người ta hay dán, tách branch khỏi
  link `/tree/`, từ chối host không phải github.com.
- `extract.test.js` — 32 điểm: các dạng payload thật, lấy đúng lượt user cuối,
  từ chối system prompt / API key / telemetry, nhận diện model.
- `composer.test.js` — 17 điểm: phân biệt "gửi đi" với "tự xoá tay", cửa sổ chủ ý,
  editor thay node thay vì xoá.
- `popup-dom.test.js` — 7 điểm: mọi id popup.js gọi đều tồn tại trong
  popup.html, và mọi file khai báo trong manifest hay đăng ký lúc chạy đều có
  thật. Bắt loại lỗi mà `node --check` không thấy.
- `background.test.js` — 157 điểm: chờ duyệt, xoá mục không gửi, khử trùng
  DOM/network, bổ sung model, công tắc bật/tắt, inject vào tab đang mở, native
  host thắng GitHub, kết nối bằng link, kiểm tra link không ghi gì, tự quét
  không ghi đè trường đã sửa, chọn branch (auto/ghim), branch sai báo lỗi thay
  vì rơi về GitHub, checklist chẩn đoán (mọi mục hỏng đều có cách sửa), giữ log
  khi mất mạng, sai repo.

Native host có bộ test Python riêng, chạy host như subprocess thật qua đúng
giao thức khung 4-byte:

```bash
.venv/Scripts/python.exe -m pytest tests/test_git_info_host.py -q
```

15 điểm, gồm hai thứ chỉ lộ ra khi chạy thật: khung bị hỏng do Windows đổi
`\n` thành `\r\n`, và byte lạ lọt lên stdout làm lệch mọi message sau đó.

## Cấu trúc file

| File | Chạy ở đâu | Việc |
|---|---|---|
| `detector.js` | mọi trang, isolated | chỉ đoán "có phải AI chat" từ cấu trúc |
| `content.js` | site đã bật, isolated | bắt nội dung ô soạn lúc gửi |
| `composer.js` | cùng content | quyết định "vừa rồi có phải một lần gửi không" |
| `adapters.js` | content + popup | selector riêng cho site đã biết |
| `background.js` | service worker | khử trùng, hàng đợi, **chỗ duy nhất gọi mạng** |
| `popup.*` | popup | duyệt, cấu hình, lịch sử, quản lý site |

## Bảo mật

API key nằm trong `chrome.storage.local` — trang web không đọc được (khác
`localStorage` của một trang HTML thường). Đừng commit key, đừng đóng gói
extension kèm key gửi cho người khác.

Extension xin quyền trên mọi site để detector chạy được. Đánh đổi này là có thật,
và nó được giới hạn bằng cách: detector chỉ đọc cấu trúc, còn hook mạng chỉ tồn
tại trên domain bạn đã bật.

## Tạo lại icon

```bash
python tools/ai-log-extension/icons/make_icons.py tools/ai-log-extension/icons
```
