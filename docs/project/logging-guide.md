# 📋 Hướng Dẫn Log Toàn Diện — AI20K Build Phase

> **Mục tiêu:** Hướng dẫn chi tiết từng bước để log đúng cách, đúng thời điểm, đúng công cụ — đảm bảo đủ điểm deliverables và theo dõi tiến độ dự án một cách chuyên nghiệp.

---

## 📌 Tổng Quan — Có 2 Hệ Thống Log Song Song

Trong dự án này tồn tại **hai hệ thống log hoàn toàn khác nhau** — cả hai đều bắt buộc:

| Hệ thống | File/Folder | Ai quản lý | Mục đích |
|---|---|---|---|
| **AI Usage Log** | `.ai-log/session.jsonl` | Script tự động + thủ công khi dùng web tool | Chứng minh sử dụng AI (deliverable #4) |
| **Worklog hàng ngày** | `WORKLOG.md` | Bạn tự điền tay | Ghi ai làm gì, kết quả gì |
| **Weekly Journal** | `JOURNAL.md` | Bạn tự điền tay | Tổng kết tuần: học gì, khó khăn gì |

> [!IMPORTANT]
> **Không nhầm lẫn hai hệ thống này.** `.ai-log/session.jsonl` ghi prompt AI, còn `WORKLOG.md` và `JOURNAL.md` ghi công việc của con người. Cả hai đều được chấm điểm.

---

## 🚀 Phần 1 — Khi Mở Folder Project Lần Đầu

### Bước 1.1 — Kiểm tra môi trường

Ngay khi mở folder project (sau khi clone hoặc pull về máy mới), chạy lần lượt:

```powershell
# Windows PowerShell — kiểm tra đã cài hook chưa
Test-Path .git/hooks/pre-push
```

Nếu kết quả là `False` → **Bắt buộc phải chạy Bước 1.2** trước khi làm bất cứ điều gì.

Nếu kết quả là `True` → Hook đã cài, chuyển sang Bước 1.3.

---

### Bước 1.2 — Cài AI Logging Hook (CHỈ cần làm 1 lần)

Hook này là "cơ chế" tự động ghi log mọi AI usage vào `.ai-log/session.jsonl` khi bạn `git push`. **Không cài hook = không có log = mất điểm deliverable #4.**

```powershell
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1
```

**Kết quả mong đợi:**
```
[ai-log] Git pre-push hook installed.
[ai-log] Setup complete. Configure AI_LOG_SERVER in your .env file.
```

Sau đó kiểm tra lại:
```powershell
Test-Path .git/hooks/pre-push  # → phải trả về True
```

> [!TIP]
> Nếu bạn làm việc trên nhiều máy (máy cá nhân + máy lab), bạn phải chạy lệnh setup này **trên từng máy** vì git hooks không được sync qua git.

---

### Bước 1.3 — Kiểm tra file `.env`

File `.env` cần có đủ các key sau để log hoạt động đúng:

```bash
# Mở .env và đảm bảo có 3 dòng này
AI_LOG_SERVER=https://ai-logs.note.transformerlabs.ai/api/ingest
AI_LOG_API_KEY=<key do BTC cung cấp — không phải placeholder>
AI_LOG_DIR=.ai-log
```

Kiểm tra nhanh:
```powershell
Select-String -Path .env -Pattern "AI_LOG_API_KEY"
```

Nếu value vẫn là placeholder (ví dụ: `your-key-here`) → cập nhật ngay bằng key thật từ BTC.

---

### Bước 1.4 — Kiểm tra file `.ai-log/session.jsonl`

```powershell
# Xem nội dung hiện tại của file log
Get-Content .ai-log/session.jsonl
```

- **File chưa tồn tại / trống** → bình thường nếu chưa có session nào.
- **File có dữ liệu** → đọc 1-2 dòng để đảm bảo đúng format JSON Lines.

---

### Bước 1.5 — Checklist mở project (copy-paste vào terminal)

```powershell
# === PROJECT OPEN CHECKLIST ===
if (Test-Path .git/hooks/pre-push) { Write-Host "✅ Hook: Installed" } else { Write-Host "❌ Hook: MISSING — chạy: powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1" }
if (Select-String -Quiet -Path .env -Pattern "AI_LOG_API_KEY=f") { Write-Host "✅ .env: Key set" } else { Write-Host "⚠️  .env: Kiểm tra AI_LOG_API_KEY" }
if (Test-Path .ai-log) { Write-Host "✅ Log dir: Exists" } else { Write-Host "⚠️  Log dir: Chưa có" }
```

---

## 🤖 Phần 2 — AI Usage Log: Log Cái Gì, Khi Nào, Như Thế Nào

### 2.1 — Bảng phân loại theo từng Tool

| AI Tool | Cách log | Bạn cần làm gì |
|---|---|---|
| **Antigravity IDE** (tool này) | Tự động khi `git push` | **Không cần làm gì** — chỉ cần push |
| **Claude Code** | Tự động qua `.claude/settings.json` | **Không cần làm gì** |
| **Cursor** | Tự động qua `.cursor/hooks.json` | **Không cần làm gì** |
| **Gemini CLI** | Tự động qua `.gemini/settings.json` | **Không cần làm gì** |
| **OpenAI Codex CLI** | Tự động qua `.codex/hooks.json` | **Không cần làm gì** |
| **GitHub Copilot** | Tự động qua `.github/hooks/` | **Không cần làm gì** |
| **ChatGPT** (web) | ❌ Không có hook | **Phải log thủ công** |
| **Gemini Web** (web) | ❌ Không có hook | **Phải log thủ công** |
| **Claude.ai** (web) | ❌ Không có hook | **Phải log thủ công** |
| **Perplexity** | ❌ Không có hook | **Phải log thủ công** |

> [!WARNING]
> Nếu bạn dùng ChatGPT/web tools mà **không log thủ công**, những session đó sẽ **không được tính** vào điểm AI Usage. Hãy log ngay sau khi kết thúc session.

---

### 2.2 — Log Tự Động: Antigravity IDE

Khi bạn đang làm việc trong Antigravity IDE (như lúc này), mọi prompt bạn gõ đều được **lưu vào transcript** tại:
```
C:\Users\<tên>\.gemini\antigravity-ide\brain\<conv-id>\.system_generated\logs\transcript.jsonl
```

Khi bạn chạy `git push`, pre-push hook tự động:
1. Đọc transcript 24 giờ gần nhất
2. Lọc ra các `USER_INPUT` và `USER_EXPLICIT` thuộc repo hiện tại
3. Append vào `.ai-log/session.jsonl`
4. Submit lên grading server

**→ Bạn không cần làm gì ngoài việc `git push` như bình thường.**

---

### 2.3 — Log Thủ Công: Web Tools (ChatGPT, Gemini Web, Claude.ai...)

**Khi nào cần log?** Ngay sau khi kết thúc một session với web tool — không để đến hôm sau.

**Cách log (Windows PowerShell):**

```powershell
# Cú pháp chuẩn
scripts\_pyrun.cmd scripts\log_manual.py --tool "<tên tool>" --prompt "<mô tả việc đã làm>"
```

**Ví dụ cụ thể:**

```powershell
# Vừa hỏi ChatGPT về cách thiết kế LangGraph state
scripts\_pyrun.cmd scripts\log_manual.py --tool chatgpt --prompt "Hỏi ChatGPT cách thiết kế LangGraph state schema cho agent phân tích rủi ro tín dụng"

# Vừa dùng Gemini Web để research thuật toán
scripts\_pyrun.cmd scripts\log_manual.py --tool gemini-web --prompt "Research các thuật toán risk scoring: Logistic Regression vs XGBoost vs Neural Network, ưu nhược điểm từng loại"

# Vừa dùng Claude.ai để review code
scripts\_pyrun.cmd scripts\log_manual.py --tool claude-web --prompt "Review và refactor hàm process_document() trong src/agents/nodes/parser.py — nhận feedback về error handling và type hints"

# Vừa dùng Perplexity để tìm tài liệu
scripts\_pyrun.cmd scripts\log_manual.py --tool perplexity --prompt "Tìm kiếm LangSmith documentation về cách setup tracing cho LangGraph agent, tham khảo best practices"
```

**Kết quả mong đợi sau khi chạy:**
```
[log] ✅ Logged: [chatgpt] Hỏi ChatGPT cách thiết kế LangGraph state schema...
[log] 📁 Saved to: .ai-log/session.jsonl
```

---

### 2.4 — Log Thủ Công: Chế Độ Tương Tác (Interactive Mode)

Nếu không nhớ cú pháp `--tool` và `--prompt`, dùng chế độ tương tác:

```powershell
scripts\_pyrun.cmd scripts\log_manual.py
```

Script sẽ hỏi từng thông tin:
```
📝 Manual AI Log Entry
========================================
Tool name (e.g. chatgpt, gemini-web, copilot, other): chatgpt
Model (e.g. gpt-5.4, gemini-3-pro, skip to use tool name): gpt-4o
What did you ask/do? (brief summary): Thiết kế UI flow cho trang verify agent output
Result/outcome (optional, press Enter to skip): Có được wireframe text cho 3 màn hình chính
```

---

### 2.5 — Verify Log Đã Được Ghi

Sau khi log thủ công, luôn kiểm tra để chắc chắn:

```powershell
# Xem dòng log cuối cùng
Get-Content .ai-log/session.jsonl | Select-Object -Last 1 | ConvertFrom-Json | Format-List
```

Output mẫu:
```
ts               : 2026-07-27T13:45:12+07:00
tool             : chatgpt
event            : ManualLog
entry_id         : manual-20260727-134512
model            : chatgpt
repo             : P-093
branch           : main
commit           : a3f9b12
student          : haidang2425@vinuni.edu.vn
prompt           : Hỏi ChatGPT cách thiết kế LangGraph state schema...
response_summary :
```

---

## 📤 Phần 3 — Khi Git Push: Log Được Submit Tự Động

Mỗi lần bạn `git push`, pipeline tự động này chạy:

```
git push
   │
   ├── [pre-push hook] scripts/log_antigravity.py --auto
   │     └── Sweep transcript 24h → append vào .ai-log/session.jsonl
   │
   └── [pre-push hook] scripts/submit_log.py
         └── Đọc .ai-log/session.jsonl → POST lên grading server
```

**Quy tắc push:**
- Push ít nhất **1 lần/ngày** khi có làm việc với AI
- Không để log tích lại nhiều ngày — transcript chỉ được sweep trong **24 giờ gần nhất**

> [!CAUTION]
> Nếu bạn dùng Antigravity IDE nhưng **không push trong 24h**, các prompt trong ngày đó **có thể bị bỏ sót** vì hook chỉ quét transcript 24 giờ gần nhất. Hãy push thường xuyên.

---

## 📝 Phần 4 — Human Log: WORKLOG.md (Hàng Ngày)

### 4.1 — Log Worklog Khi Nào?

**Cuối mỗi ngày làm việc** (hoặc ngay sau khi hoàn thành một task lớn).

### 4.2 — Format và Ví Dụ Cụ Thể

Mở file `WORKLOG.md` và điền theo format:

```markdown
## 2026-07-27

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| Hải Đăng | Thiết kế LangGraph state schema | ✅ Done | `src/agents/state.py` | 2h |
| Hải Đăng | Setup FastAPI skeleton | ✅ Done | `src/api/routes.py` | 1.5h |
| Hải Đăng | Research risk scoring algorithms | 🔄 WIP | Ghi chú trong Notion | 1h |
| An Nhiên | Viết unit test cho parser node | ✅ Done | `tests/test_agents/test_parser.py` | 2h |
| An Nhiên | Fix bug timeout khi gọi OpenAI | ✅ Done | PR #12 merged | 0.5h |

**Tổng kết ngày:** Hoàn thành skeleton backend + state schema. Cần tiếp tục research risk scoring để quyết định thuật toán trước thứ 4.
```

**Status icons:**
- `✅ Done` — Task hoàn thành
- `🔄 WIP` — Đang làm, chưa xong
- `❌ Blocked` — Bị chặn, có lý do

> [!TIP]
> Cột **Output** rất quan trọng — luôn link tới file cụ thể, PR number, hoặc tên document. Đừng để trống hoặc ghi chung chung "đã làm xong".

---

## 📖 Phần 5 — Human Log: JOURNAL.md (Hàng Tuần)

### 5.1 — Log Journal Khi Nào?

**Cuối mỗi tuần** — thường là chiều thứ 6 hoặc tối chủ nhật.

### 5.2 — Format và Ví Dụ Cụ Thể

Mở file `JOURNAL.md` và điền:

```markdown
## Week 3: 2026-07-21 - 2026-07-27

### Mục tiêu tuần này
- [x] Hoàn thành LangGraph agent skeleton với 3 nodes cơ bản
- [x] Setup FastAPI endpoints /chat và /health
- [ ] Viết integration test cho agent-api flow (chuyển sang tuần sau)

### Đã hoàn thành
- LangGraph state schema với 8 fields, đã validate qua pytest
- FastAPI routes với Pydantic validation, swagger docs hoàn chỉnh
- Docker image build thành công, chạy được local

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|---|---|---|
| LangGraph interrupt node gây infinite loop | Đọc docs, thêm max_iterations=10 | ✅ Fixed |
| OpenAI rate limit khi chạy eval | Implement exponential backoff | ✅ Fixed |
| Docker image 2.1GB quá lớn | Dùng multi-stage build, xóa dev deps | 🔄 Giảm còn 850MB |

### Bài học
- Nên đọc LangGraph docs về conditional edges trước khi code, không đoán mò
- Type hints từ đầu tiết kiệm rất nhiều debug time
- Pair programming hiệu quả hơn solo khi gặp architecture decision

### Kế hoạch tuần sau
- [ ] Viết integration tests (coverage ≥ 70%)
- [ ] Deploy lên Render, test end-to-end
- [ ] Bắt đầu RAGAS evaluation với 20 test cases
```

---

## ⚙️ Phần 6 — Workflow Hàng Ngày (Tổng Hợp)

### Morning Checklist (Đầu ngày)

```
✅ Pull code mới nhất: git pull
✅ Kiểm tra WORKLOG.md ngày hôm qua đã điền chưa
✅ Lên plan cho hôm nay (thêm vào WORKLOG.md luôn)
```

### During Work (Trong lúc làm)

```
→ Dùng Antigravity/Claude Code/Cursor/Gemini CLI?
     ✅ Không cần làm gì — hook tự động capture

→ Dùng ChatGPT/Gemini Web/Claude.ai?
     ✅ Log ngay sau khi kết thúc session:
     scripts\_pyrun.cmd scripts\log_manual.py --tool chatgpt --prompt "..."
```

### End of Day Checklist (Cuối ngày)

```
✅ Cập nhật WORKLOG.md với công việc hôm nay
✅ Log thủ công các web tool session (nếu có)
✅ git add . && git commit -m "..." && git push
   (pre-push hook tự động submit AI logs lên server)
```

### End of Week Checklist (Cuối tuần)

```
✅ Cập nhật JOURNAL.md với tổng kết tuần
✅ Review .ai-log/session.jsonl — đủ entries không?
✅ git push để submit tuần này
```

---

## 🚨 Phần 7 — Lỗi Thường Gặp & Cách Xử Lý

### Lỗi 1: Pre-push hook không chạy

**Triệu chứng:** Push thành công nhưng không thấy log nào mới trong `.ai-log/session.jsonl`

**Kiểm tra:**
```powershell
Get-Content .git/hooks/pre-push
```

**Fix:**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1
```

---

### Lỗi 2: Submit log thất bại — "AI_LOG_API_KEY not set"

**Triệu chứng:**
```
[submit] ❌ AI_LOG_API_KEY not configured
```

**Fix:** Cập nhật `.env` với key thật từ BTC:
```bash
AI_LOG_API_KEY=f3p1dEOhD_z8qjjtbeCtb2t9ASMEliz-...   # key thật, không phải placeholder
```

---

### Lỗi 3: `git config user.email` chưa set

**Triệu chứng khi log thủ công:**
```
[log] ⚠️  git email not set! Using fallback: haidang2425
```

**Fix:**
```bash
git config user.email "haidang2425@vinuni.edu.vn"
git config user.name "Hải Đăng"
```

---

### Lỗi 4: WORKLOG.md không có entry cho hôm nay

Đây không phải lỗi kỹ thuật — nhưng sẽ bị trừ điểm nếu có ngày làm việc mà không có entry. Hãy cập nhật ngay.

---

### Lỗi 5: Dùng Antigravity nhưng prompt không được capture

**Nguyên nhân:** Quên push — transcript chỉ được sweep trong 24h.

**Cách phòng tránh:** Push ít nhất 1 lần/ngày, ngay cả khi commit chưa "sạch":
```bash
git add .
git commit -m "wip: [mô tả ngắn]"
git push
```

---

## ❌ Những Điều KHÔNG Làm

> [!CAUTION]
> Những lệnh sau có thể tạo log **giả mạo** hoặc phá vỡ hệ thống log:

```bash
# ❌ KHÔNG gọi log_antigravity.py thủ công với summary
python scripts/log_antigravity.py "TaskComplete" "claude-3"

# ❌ KHÔNG dùng log_manual.py cho Antigravity IDE
# (Antigravity đã auto-log — log thủ công sẽ tạo entry trùng lặp)

# ❌ KHÔNG sửa hoặc xóa file trong .ai-log/
# (file này được quản lý hoàn toàn bởi scripts)

# ❌ KHÔNG git push --no-verify (bypass hook)
# (sẽ không submit log lên server)
```

---

## 📊 Phần 8 — Quick Reference: Log Cái Nào, Ở Đâu

```
Sử dụng AI tool?
├── Antigravity IDE / Claude Code / Cursor / Gemini CLI / Copilot / Codex
│   └── → git push → tự động log ✅
│
├── ChatGPT / Gemini Web / Claude.ai / Perplexity (web tools)
│   └── → Chạy ngay sau session:
│         scripts\_pyrun.cmd scripts\log_manual.py --tool <tool> --prompt "<mô tả>"
│
└── Hoàn thành công việc trong ngày?
    ├── → Cập nhật WORKLOG.md (ai làm gì, kết quả gì)
    └── → Cuối tuần: cập nhật JOURNAL.md (tổng kết, bài học)
```

---

## 📁 Phần 9 — Tất Cả Files & Scripts Liên Quan

| File/Script | Mục đích | Khi nào dùng |
|---|---|---|
| `.ai-log/session.jsonl` | Nơi lưu tất cả AI usage log | Đọc để verify, không sửa tay |
| `scripts/setup_hooks.ps1` | Cài pre-push hook | 1 lần sau khi clone |
| `scripts/log_manual.py` | Log thủ công web tools | Sau mỗi ChatGPT/web session |
| `scripts/log_antigravity.py` | Sweep Antigravity transcript | Tự động chạy khi push |
| `scripts/submit_log.py` | Submit log lên grading server | Tự động chạy khi push |
| `WORKLOG.md` | Log công việc hàng ngày | Cuối mỗi ngày làm việc |
| `JOURNAL.md` | Journal hàng tuần | Cuối mỗi tuần |
| `.env` | API keys cho logging | Setup 1 lần, giữ bí mật |
| `.agents/workflows/log.md` | Workflow log ngắn gọn | Tham khảo nhanh |
| `.agents/rules/ai-log-hook.md` | Rules cho AI agent | AI tự đọc |

---

## ✅ Checklist Cuối — Đảm Bảo Đủ Điểm Deliverables

### Deliverable #4 — AI Logs
- [ ] Hook đã cài: `Test-Path .git/hooks/pre-push` trả về `True`
- [ ] `.env` có `AI_LOG_API_KEY` thật (không phải placeholder)
- [ ] Push code ít nhất 1 lần/ngày khi có làm việc
- [ ] Log thủ công ngay sau mỗi session với web tools
- [ ] Kiểm tra `.ai-log/session.jsonl` có entries đủ không

### Deliverable #8 — Weekly Journal
- [ ] `JOURNAL.md` có entry cho mỗi tuần làm việc
- [ ] Mỗi entry đủ 4 section: Mục tiêu / Đã hoàn thành / Khó khăn / Bài học

### Deliverable #9 — Worklog
- [ ] `WORKLOG.md` có entry cho mỗi ngày làm việc (không bỏ ngày)
- [ ] Mỗi dòng có đủ: Member / Task / Status / Output / Time
- [ ] Cột Output luôn có link/file cụ thể (không để trống)

---

*Hướng dẫn này được tổng hợp từ:*
*`.agents/workflows/log.md`, `.agents/rules/ai-log-hook.md`, `README.md`, và source code trong `scripts/`*
