# Hướng dẫn cài đặt và sử dụng — AI20K Log Bridge

Tài liệu này đi từ đầu đến cuối: cài, cấu hình đường dẫn cho đúng, dùng hằng
ngày, và tra lỗi. Phần **đường dẫn** được viết kỹ nhất vì đó là chỗ sai nhiều
nhất, và sai kiểu âm thầm — không báo lỗi, chỉ ghi nhầm dữ liệu.

- [1. Tool này làm gì](#1-tool-này-làm-gì)
- [2. Cần có sẵn gì](#2-cần-có-sẵn-gì)
- [3. Cài đặt](#3-cài-đặt)
- [4. Đường dẫn — phần quan trọng nhất](#4-đường-dẫn--phần-quan-trọng-nhất)
- [5. Cấu hình trong popup](#5-cấu-hình-trong-popup)
- [6. Dùng hằng ngày](#6-dùng-hằng-ngày)
- [7. Kiểm tra đã đúng chưa](#7-kiểm-tra-đã-đúng-chưa)
- [8. Tra lỗi](#8-tra-lỗi)
- [9. Chuyển sang thư mục hoặc máy khác](#9-chuyển-sang-thư-mục-hoặc-máy-khác)
- [10. Gỡ cài đặt](#10-gỡ-cài-đặt)

---

## 1. Tool này làm gì

Bạn chat với AI trên web (ChatGPT, Claude, Gemini…). Extension bắt lại **prompt
bạn gõ**, cho bạn duyệt, rồi gửi lên grading server của BTC kèm thông tin repo /
branch / commit.

Nó **chỉ đọc ô soạn thảo bạn gõ vào**. Không đọc câu trả lời của AI, không đọc
request của trang, không đọc trang nào ngoài danh sách bạn bật.

Có hai phần rời nhau:

| Phần | Chạy ở đâu | Bắt buộc? |
|---|---|---|
| **Extension** | trong Chrome/Edge | Có |
| **Native host** | một script Python trên máy | Không, nhưng nên có |

Native host chỉ để lấy **commit thật trên máy**. Không có nó thì commit lấy qua
GitHub API — chỉ thấy commit **đã push**, nên nếu bạn có commit chưa push thì số
đó trễ hơn thực tế.

---

## 2. Cần có sẵn gì

| Thứ | Yêu cầu | Kiểm tra bằng |
|---|---|---|
| Chrome hoặc Edge | phiên bản **111 trở lên** | `chrome://version` |
| Python | **3.8+** (chỉ cần cho native host) | `python --version` |
| Git | bất kỳ bản nào | `git --version` |
| File `.env` của repo | có `AI_LOG_SERVER` và `AI_LOG_API_KEY` | mở file ra xem |

Không có `.env` thì hỏi BTC hai giá trị đó. Đây là hai thứ duy nhất bạn phải gõ
tay — còn lại tool tự lấy.

---

## 3. Cài đặt

### Bước 1 — Nạp extension vào trình duyệt

1. Mở `chrome://extensions` (Edge: `edge://extensions`)
2. Bật **Developer mode** ở góc phải trên
3. Bấm **Load unpacked**
4. Chọn thư mục `ai-log-extension` (thư mục có file `manifest.json` bên trong)

**Kiểm tra ngay:** ID hiện dưới tên extension phải đúng chuỗi này:

```
cheofncpckkpmfjoeflampnmainmblac
```

ID khác nghĩa là Chrome không đọc được trường `key` trong `manifest.json`. Hậu
quả: native host sẽ **im lặng không trả lời** — không báo lỗi gì cả — vì nó chỉ
cho phép đúng ID này gọi tới.

### Bước 2 — Cài native host bằng một lệnh

Mở terminal **tại thư mục gốc repo**, rồi:

```
tools\ai-log-extension\setup.cmd --server
```

macOS / Linux:

```bash
bash tools/ai-log-extension/setup.sh --server
```

Trên Windows nhấn đúp vào `setup.cmd` cũng chạy được.

Lệnh này **vừa cài vừa kiểm tra**. Chạy lại bao nhiêu lần cũng được — nó ghi đè
bằng giá trị đúng chứ không nhân bản.

Kết quả mong đợi:

```
TAT CA DAT (14 muc OK)
```

Nếu ra `CON n MUC HONG` thì mỗi mục hỏng đều in kèm cách sửa — làm theo rồi chạy
lại.

### Bước 3 — Khởi động lại trình duyệt

**Bắt buộc, không bỏ qua được.** Chrome chỉ đọc đăng ký native host lúc khởi
động. Không restart thì popup vẫn báo "chưa cài native host" dù bạn đã cài xong,
và bạn sẽ mất thời gian tìm lỗi không tồn tại.

Đóng **tất cả** cửa sổ Chrome rồi mở lại. Ẩn xuống khay hệ thống không tính.

### Bước 4 — Điền server và API key

Bấm icon extension → mục **Cấu hình**:

| Ô | Lấy ở đâu |
|---|---|
| Server URL | `.env`, dòng `AI_LOG_SERVER=` |
| API Key | `.env`, dòng `AI_LOG_API_KEY=` |

Bấm **Lưu cấu hình**, rồi **Test kết nối**. Đúng thì hiện `HTTP 202`.

### Bước 5 — Lấy thông tin repo

Vẫn trong Cấu hình, bấm **Hoặc lấy từ repo trên máy**. Nó điền một lúc:
repo, branch, email, commit — bằng đúng những lệnh `git` mà pipeline Python chạy.

Không có native host thì dán link GitHub vào ô **Link repo GitHub** rồi bấm
**Kết nối**.

### Bước 6 — Kiểm tra tổng thể

Mục **Bắt đầu** → **Kiểm tra tất cả**. Đủ xanh là xong. Mục vàng là tuỳ chọn,
không chặn gì.

---

## 4. Đường dẫn — phần quan trọng nhất

### 4.1. Quy tắc số một: phải là GỐC repo

Đường dẫn repo phải trỏ vào **thư mục chứa `.git`**, không phải thư mục con.

```
D:\Lab Vin AI\team-T093\          ← ĐÚNG (có .git ở đây)
D:\Lab Vin AI\team-T093\src\      ← SAI (bị từ chối)
D:\Lab Vin AI\                    ← SAI (không phải repo)
```

**Vì sao khắt khe vậy?** Lệnh `git rev-parse` **dò ngược lên cây thư mục**. Nếu
bạn trỏ vào một thư mục bất kỳ, git sẽ leo lên các thư mục cha cho tới khi gặp
một repo nào đó — và trả về commit của **repo đó**.

Đây không phải giả thuyết. Trên máy này:

```
$ cd C:/Users/ADMIN/AppData/Local/Temp
$ git rev-parse --show-toplevel
C:/Users/ADMIN            ← thư mục home đang là một git repo
```

Rất nhiều người version-control thư mục home (dotfiles). Nghĩa là gõ nhầm đường
dẫn thành gần như bất kỳ chỗ nào trong `C:\Users\<tên>\` sẽ khiến tool báo commit
của repo dotfiles, và **mọi log của bạn mang commit sai mà không có cảnh báo
nào**.

Nên host bắt buộc `toplevel == đường dẫn bạn đưa`. Sai thì báo lỗi rõ ràng thay
vì trả về một con số trông có vẻ đúng.

### 4.2. Khi nào phải chỉ rõ `--repo`

`setup.cmd` mặc định đoán repo là **thư mục cha hai cấp** của chính nó:

```
<repo>/tools/ai-log-extension/setup.cmd   →  đoán <repo>
```

Đúng khi extension nằm trong repo theo bố cục chuẩn. Các trường hợp khác phải
chỉ rõ:

```
tools\ai-log-extension\setup.cmd --repo "D:\duong\dan\repo"
```

| Tình huống | Cần `--repo`? |
|---|---|
| Extension ở `<repo>/tools/ai-log-extension/` | Không |
| Extension để ngoài repo (Desktop, Downloads…) | **Có** |
| Muốn theo dõi repo khác với repo chứa extension | **Có** |
| Có nhiều repo, muốn đổi qua lại | **Có**, chạy lại mỗi lần đổi |

Đường dẫn có dấu cách thì phải bọc trong nháy kép — `D:\Lab Vin AI\team-T093` là
ví dụ điển hình.

### 4.3. Ba file sinh ra lúc cài

`setup.cmd` tạo ba file trong `ai-log-extension/native/`. Cả ba đều **nhúng cứng
đường dẫn tuyệt đối của máy bạn**:

| File | Chứa gì |
|---|---|
| `host_config.json` | đường dẫn repo mặc định |
| `run_host.bat` (hoặc `.sh`) | đường dẫn tới Python và tới `git_info_host.py` |
| `com.ai20k.gitinfo.json` | đường dẫn tới launcher ở trên |

Ví dụ thật:

```json
{
  "repo": "D:\\Lab Vin AI\\team-T093",
  "debug": false
}
```

**Ba file này đã bị `.gitignore` và bị loại khỏi file zip.** Commit hoặc gửi
chúng cho đồng đội là đưa họ đường dẫn máy bạn — trên máy họ những đường dẫn đó
không tồn tại, host sẽ chết hoặc tệ hơn là đọc nhầm repo.

Nguyên tắc: **mỗi máy tự chạy `setup.cmd` một lần.**

### 4.4. Đăng ký với trình duyệt nằm ở đâu

Đây là chỗ Chrome tra để biết native host tồn tại:

**Windows** — khoá registry (cấp user, không cần quyền admin):

```
HKCU\Software\Google\Chrome\NativeMessagingHosts\com.ai20k.gitinfo
HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.ai20k.gitinfo
```

Giá trị mặc định của khoá = đường dẫn tuyệt đối tới `com.ai20k.gitinfo.json`.

**macOS**

```
~/Library/Application Support/Google/Chrome/NativeMessagingHosts/
~/Library/Application Support/Microsoft Edge/NativeMessagingHosts/
```

**Linux**

```
~/.config/google-chrome/NativeMessagingHosts/
~/.config/microsoft-edge/NativeMessagingHosts/
```

Vì đăng ký trỏ tới đường dẫn tuyệt đối, **di chuyển hay đổi tên thư mục
`ai-log-extension` sẽ làm hỏng liên kết**. Chạy lại `setup.cmd` ở vị trí mới là
xong.

### 4.5. Đường dẫn Python

`setup.cmd` ưu tiên `.venv` của repo:

```
<repo>\.venv\Scripts\python.exe      (Windows)
<repo>/.venv/bin/python              (macOS/Linux)
```

Không có venv thì dùng Python trong PATH. Đường dẫn đó được ghi cứng vào
`run_host.bat`, nên **xoá hoặc tạo lại venv thì phải chạy lại `setup.cmd`** —
launcher sẽ trỏ vào một file python không còn tồn tại.

### 4.6. Bảng tra nhanh

| Bạn vừa làm gì | Phải làm gì |
|---|---|
| Di chuyển thư mục `ai-log-extension` | chạy lại `setup.cmd` |
| Đổi tên thư mục repo | chạy lại `setup.cmd` |
| Xoá / tạo lại `.venv` | chạy lại `setup.cmd` |
| Chuyển sang theo dõi repo khác | `setup.cmd --repo "<gốc repo mới>"` |
| Cài trên máy thứ hai | chạy `setup.cmd` trên máy đó |
| Chỉ `git switch` sang branch khác | **không cần làm gì** — tool tự theo |
| Cập nhật code extension | Reload ở `chrome://extensions` |

---

## 5. Cấu hình trong popup

### Server và API key

Hai ô bắt buộc, lấy từ `.env`. Sai key thì **Test kết nối** trả 401/403.

### Repo — ba cách, chọn một

| Cách | Cần gì | Được gì |
|---|---|---|
| **Tự quét** | native host | tự chạy lúc mở trình duyệt, không phải bấm gì |
| **Dán link GitHub** | không | repo + danh sách branch, nhưng chỉ thấy commit đã push |
| **Lấy từ repo trên máy** | native host | ghi đè toàn bộ bằng giá trị thật của checkout |

Tự quét có quy tắc ghi đè **cố ý không đối xứng**:

| Trường | Hành vi |
|---|---|
| `commit`, và `branch` ở chế độ auto | luôn cập nhật — chúng cũ đi từng phút |
| `repo`, `student`, link GitHub, đường dẫn | **chỉ điền khi đang trống** |

Nghĩa là bạn sửa tay một trường thì lần khởi động sau không bị ghi đè lại.

### Branch — hai chế độ

| | Theo branch đang dùng *(mặc định)* | Ghim một branch |
|---|---|---|
| Lấy branch nào | branch repo đang checkout | branch bạn chọn |
| `git switch` sang branch khác | log tự đi theo | giữ nguyên |
| Đọc được branch chưa checkout | không | có |

Branch là dropdown lấy từ danh sách thật, không phải ô gõ tay — gõ sai tên branch
từng là lỗi im lặng.

### Tên repo phải khớp

Trường **Repo** phải đúng tên BTC cấp (ví dụ `P-093`). Sai thì server trả
`mismatched_repos` và **bỏ entry**. Extension bắt được điều này: entry chuyển
sang mục *Từ chối*, badge đỏ, sửa lại rồi bấm **Gửi lại**.

---

## 6. Dùng hằng ngày

### Hai chế độ

| | Chờ duyệt *(mặc định)* | Tự động |
|---|---|---|
| Prompt bắt được | vào danh sách chờ, **chưa gửi đi đâu** | gửi ngay |
| Bạn làm gì | tick mục muốn gửi → **Gửi mục đã chọn** | không cần làm gì |
| Không muốn gửi | **Xoá mục đã chọn** — không bao giờ rời máy | — |

Mặc định là Chờ duyệt vì hỏi AI một câu riêng tư rồi mới nhận ra nó đã lên server
thì không rút lại được.

Bấm vào một dòng log để xem **toàn văn prompt** cùng repo/branch/commit sẽ được
ghi kèm.

### Hai công tắc, đều ăn ngay không cần F5

- **Công tắc tổng** ở header — ngừng bắt trên mọi site. Badge hiện `off` màu xám.
- **Công tắc theo site** — chỉ ngừng cho trang đang mở.

Tắt còn xoá bản nháp đang theo dõi, nên câu gõ dở trước lúc tắt không nổi lên sau.

### Site được bắt log

Bật sẵn: ChatGPT, Claude.ai, Gemini, AI Studio, Perplexity, DeepSeek, Grok.

Mở một AI chat lạ thì popup tự gợi ý *"Bật log cho site này?"* — bấm một lần là
xong, không cần khai báo trước.

---

## 7. Kiểm tra đã đúng chưa

### Từ terminal

```
tools\ai-log-extension\setup.cmd --check
```

Kiểm 14 mục phía máy: Python, git, đường dẫn repo có đúng gốc không, host trả lời
được không, launcher, manifest, đăng ký Chrome/Edge, extension ID, `.env`. Thêm
`--server` để gọi thử grading server (gửi batch rỗng, không ghi log nào).

### Từ popup

Mục **Bắt đầu** → **Kiểm tra tất cả**. Kiểm phía trình duyệt: cấu hình, server có
trả lời không, native host, site đang bật, và trang đang mở có được ghi log không.

Hai chỗ này bù nhau — terminal thấy registry và đường dẫn mà browser không thấy;
popup thấy service worker có gọi được host không mà terminal không thấy.

### Kiểm tra bắt đủ hay không

Bốn bước trên chỉ chứng minh "bắt được". Muốn biết **bắt đủ** thì phải đếm:

1. Chuyển sang chế độ **Tự động**
2. Gửi đúng 5 prompt đánh số `test 1` … `test 5`
3. Mở **Lịch sử đã gửi** — phải đúng 5 mục

Thiếu mục nào thì ghi lại prompt đó gửi bằng cách gì (Enter, bấm nút, Ctrl+Enter)
— đó là đường đang hở. Lặp lại trên từng site bạn thực sự dùng.

Quy trình đầy đủ 7 tầng: xem [TESTING.md](TESTING.md).

---

## 8. Tra lỗi

| Hiện tượng | Nguyên nhân thường gặp | Cách sửa |
|---|---|---|
| "Chưa cài native host" | chưa restart trình duyệt | đóng hết cửa sổ, mở lại |
| Vẫn "chưa cài" sau khi restart | ID extension không khớp | xem lại Bước 1 |
| "Đường dẫn không phải gốc repo" | trỏ vào thư mục con | `setup.cmd --repo "<gốc repo>"` |
| Commit sai / lạ hoắc | trỏ nhầm repo khác | xem mục 4.1 |
| Test kết nối trả 401 hoặc 403 | API key sai | lấy lại từ `.env` |
| Test kết nối trả 404 | Server URL sai | lấy lại từ `.env` |
| `server nhận 0`, mục Từ chối tăng | tên repo không khớp | sửa Repo, bấm **Gửi lại** |
| Gõ prompt mà không có toast | site chưa bật, hoặc công tắc đang tắt | kiểm hai công tắc |
| Bắt được cả nội dung không phải prompt | đang chạy **bản cũ** | Reload extension |
| Popup báo lỗi lạ | code cũ còn trong bộ nhớ | Reload extension **và** F5 tab |

### Xem log lỗi ở đâu

| Nơi | Thấy được gì |
|---|---|
| `chrome://extensions` → **service worker** | lỗi hàng đợi, lỗi gửi, lỗi gọi native host |
| Console của trang (F12) | lỗi content script, lỗi bắt DOM |
| `chrome://extensions` → **Errors** | lỗi lúc nạp extension |
| `native/host.log` | lỗi native host — bật bằng `setup.cmd --debug` |

### Sau khi sửa code

Bấm **Reload** ở `chrome://extensions`, rồi **F5 lại các tab đang mở**. Service
worker nạp lại không tự tiêm content script vào tab cũ.

---

## 9. Chuyển sang thư mục hoặc máy khác

1. Chép cả thư mục `ai-log-extension` sang chỗ mới
2. **Xoá ba file sinh ra** trong `native/` nếu có: `host_config.json`,
   `run_host.bat` / `run_host.sh`, `com.ai20k.gitinfo.json`
3. Chạy `setup.cmd` ở vị trí mới (thêm `--repo` nếu extension không nằm trong
   repo cần theo dõi)
4. Khởi động lại trình duyệt
5. `chrome://extensions` → gỡ bản cũ → **Load unpacked** thư mục mới

Bước 2 không bắt buộc — `setup.cmd` ghi đè cả ba — nhưng xoá trước thì chắc chắn
không sót đường dẫn cũ.

Extension ID **không đổi** khi di chuyển, vì nó được ghim bằng trường `key` trong
`manifest.json` chứ không suy từ đường dẫn. Nhờ vậy đăng ký native host vẫn khớp
và bạn không phải sửa gì thêm.

Cấu hình trong popup (server, API key, repo…) nằm trong `chrome.storage` của
extension, **không nằm trong thư mục**, nên gỡ rồi nạp lại cùng ID thì vẫn còn.

---

## 10. Gỡ cài đặt

```
tools\ai-log-extension\setup.cmd --uninstall
```

Xoá đăng ký native host khỏi Chrome và Edge. Sau đó vào `chrome://extensions` gỡ
extension.

Ba file sinh ra trong `native/` và file `host.log` thì xoá tay nếu muốn dọn sạch.

Log đã gửi lên server **không thu hồi được** — gỡ tool không xoá dữ liệu đã nộp.
