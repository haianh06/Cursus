# Quy trình test AI Log Bridge

Bảy tầng, xếp từ rẻ tới đắt. Mỗi tầng cô lập **một** chỗ có thể hỏng — chạy đúng
thứ tự thì khi fail bạn biết ngay lỗi nằm đâu, thay vì phải đoán giữa năm khả năng.

Đừng bỏ qua tầng trước để nhảy tới tầng sau. Tầng 3 fail mà chưa chạy tầng 2 thì
không biết là do bắt log hỏng hay do server không kết nối được.

---

## Tầng 0 — Logic (30 giây, không cần trình duyệt)

```bash
node tools/ai-log-extension/test/run.js
.venv/Scripts/python.exe -m pytest -q
```

**Đạt:** `All suites passed` và `22 passed`.

Phủ: phân biệt gửi thật với xoá tay, hàng đợi chờ duyệt, khử trùng, giữ log khi
mất mạng, phân tích link repo, giao thức native host.

**Không** phủ: bất cứ thứ gì cần Chrome thật. Đó là lý do còn 6 tầng nữa.

---

## Tầng 1 — Cài đặt và ID

```powershell
tools\ai-log-extension\setup.cmd --server
```

**Đạt:** in ra các dòng `PASS`, rồi `repo : P-093` và `commit : <sha>` đúng với
`git rev-parse --short HEAD`.

Sau đó `chrome://extensions` → Developer mode → Load unpacked → chọn
`tools/ai-log-extension`.

**Kiểm tra bắt buộc — ID phải đúng:**

```
cheofncpckkpmfjoeflampnmainmblac
```

ID khác đi nghĩa là trường `key` trong `manifest.json` không được đọc. Native
host sẽ **im lặng không trả lời**, vì `allowed_origins` chỉ cho phép đúng ID này.

---

## Tầng 2 — Native host qua trình duyệt

Khởi động lại Chrome (bắt buộc — Chrome chỉ đọc registry lúc khởi động).

Popup → **Cấu hình** → **Lấy từ repo trên máy**.

**Đạt:** bốn ô tự điền — Repo `P-093`, Branch `main`, Email, Commit — và banner
báo `Đã lấy từ D:\Lab Vin AI\team-T093`.

**Fail thường gặp:**

| Hiện tượng | Nguyên nhân |
|---|---|
| "Chưa cài native host" | chưa restart Chrome, hoặc chưa chạy `setup.cmd` |
| "Đường dẫn không phải gốc repo" | chạy `setup.cmd --repo "D:\duong\dan"` |
| Không phản hồi gì | ID extension không khớp (xem tầng 1) |

Xem log lỗi: `chrome://extensions` → **service worker** → tab Console.

---

## Tầng 3 — Kết nối server

Popup → **Test kết nối**.

**Đạt:** `Kết nối OK — server trả HTTP 202`.

Đây là tầng **quan trọng nhất chưa từng được chứng minh**. Nó trả lời đúng một
câu hỏi: service worker có thực sự vượt được CORS không. Trang HTML thường bị
chặn ở đây (`400 Disallowed CORS origin`) — nếu extension cũng nhận 400 thì toàn
bộ cách tiếp cận sai, và mọi tầng sau vô nghĩa.

Cú gọi này gửi `entries: []` nên không ghi gì lên server.

---

## Tầng 4 — Bắt log trên site thật

Đảm bảo đang ở chế độ **Chờ duyệt** (mặc định) để không lỡ gửi rác lên server.

Mở `chatgpt.com`, gõ một câu **có dấu tiếng Việt**, gửi.

**Đạt:** toast góc phải dưới hiện `AI20K · Chờ bạn duyệt`, badge extension +1 màu
xanh dương.

Mở popup, mục **Chờ duyệt**:

| Kiểm | Mong đợi |
|---|---|
| Nội dung prompt | đúng nguyên văn, dấu tiếng Việt không lỗi |
| Tool | `chatgpt` |
| Dòng meta cuối | có `dom:enter` hoặc `dom:sent` |

**Trường `via` là công cụ chẩn đoán chính.** Nó nói trigger nào đã bắt được:

- `dom:enter` — bắt lúc bấm Enter
- `dom:sent` — bắt lúc ô soạn bị xoá trắng sau một phím/click (đường phổ quát)

Chỉ có hai giá trị này. Thấy bất kỳ giá trị nào khác — nhất là `net:*` — nghĩa là
bạn đang chạy bản cũ có đường đọc request; bản đó ghi cả log nội bộ của trang vào
hàng đợi. Reload extension.

**Không có toast nào** → không bắt được. Mở Console của trang để xem lỗi.

---

## Tầng 5 — Duyệt và gửi

Tick mục vừa bắt → **Gửi mục đã chọn**.

**Đạt:** `Đã gửi 1 mục — server nhận 1.`

**Đây là con số cần nhìn.** `server nhận 0` nghĩa là server đã nhận request nhưng
**không ghi entry nào** — thường do sai tên repo. Ngó thống kê *Từ chối*: khác 0
thì sửa Repo trong Cấu hình rồi bấm **Gửi lại**.

Sau đó kiểm mục **Lịch sử đã gửi** — phải có đúng mục vừa gửi, trạng thái `đã gửi`.

Test luôn chiều ngược lại: bắt thêm một prompt, tick, bấm **Xoá mục đã chọn**.
Nó phải biến mất khỏi Chờ duyệt và **không** xuất hiện trong Lịch sử.

---

## Tầng 6 — Đếm để biết có đủ không

Bốn tầng trên chỉ chứng minh "bắt được", chưa chứng minh "bắt **đủ**". Muốn biết
đủ thì phải đếm.

1. Popup → chuyển sang **Tự động**
2. Trên một site, gửi đúng **5 prompt** khác nhau, đánh số: `test 1` … `test 5`
3. Popup → **Lịch sử đã gửi**

**Đạt:** đúng 5 mục, không thiếu, không trùng.

Thiếu mục nào thì ghi lại **prompt đó gửi bằng cách gì** — bấm nút, Enter, hay
Ctrl+Enter. Đó chính là đường đang hở.

Lặp lại trên từng site bạn thực sự dùng. Mỗi site là một cách bắt khác nhau, đạt
ở ChatGPT không nói lên gì về Gemini.

Nhớ chuyển lại **Chờ duyệt** khi xong.

---

## Tầng 7 — Các ca biên

Làm sau khi 0–6 đã xanh.

| Ca | Cách làm | Mong đợi |
|---|---|---|
| **Gõ tiếng Việt có dấu** | gõ "chào bạn" bằng Telex, Enter giữa lúc bỏ dấu | không ghi log sớm; chỉ ghi khi gửi thật |
| **Xoá tay không gửi** | gõ một câu rồi Ctrl+A, Delete | **không** có log nào |
| **Mất mạng** | DevTools → Network → Offline → duyệt và gửi | badge vàng, banner "chờ gửi"; bật mạng lại → tự gửi trong 1 phút |
| **Tắt toàn bộ** | gạt công tắc header | badge `off`; gửi prompt → không có toast |
| **Tắt theo site** | gạt công tắc ở dòng site | site đó im, site khác vẫn ghi, **không cần tải lại trang** |
| **Bật site đang mở** | tắt rồi bật lại site hiện tại | ăn ngay, không cần F5 |
| **Sai repo** | sửa Repo thành `SAI-123`, gửi | badge đỏ, vào mục Từ chối; sửa lại rồi **Gửi lại** → gửi được |
| **Site lạ** | mở một AI chat chưa có trong danh sách | popup gợi ý "Bật log cho site này?" |
| **Trang thường** | mở báo, ngân hàng, Gmail | **không** gợi ý gì; không có toast |

Ca cuối quan trọng nhất về mặt riêng tư: detector chấm điểm nhầm trang thường
thành AI chat là dấu hiệu ngưỡng quá thấp, phải nâng `THRESHOLD` trong
`detector.js`.

---

## Khi có gì đó hỏng

| Xem ở đâu | Thấy được gì |
|---|---|
| `chrome://extensions` → **service worker** → Console | lỗi hàng đợi, lỗi gửi, lỗi native host |
| Console của trang (F12) | lỗi content script, lỗi bắt DOM |
| `chrome://extensions` → **Errors** | lỗi lúc nạp extension |
| `tools/ai-log-extension/native/host.log` | lỗi native host (`setup.cmd --debug` để bật) |
| `setup.cmd --check` | toàn bộ phía máy: đăng ký, launcher, đường dẫn repo |

Sửa xong nhớ bấm **Reload** ở `chrome://extensions`, rồi **F5 lại tab** đang mở —
service worker nạp lại không tự tiêm lại content script vào tab cũ.

---

## Tóm tắt

| Tầng | Chứng minh điều gì | Chưa chứng minh |
|---|---|---|
| 0 | logic đúng | Chrome |
| 1 | cài đặt + ID khớp | host trả lời được |
| 2 | native messaging thông | mạng |
| 3 | **vượt được CORS** | bắt log |
| 4 | bắt được trên site thật | bắt đủ |
| 5 | server thật sự ghi nhận | tính đầy đủ |
| 6 | **bắt đủ, không sót** | ca biên |
| 7 | ca biên và riêng tư | — |
