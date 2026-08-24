# Hệ thống theo dõi tiến độ team — thay báo cáo miệng bằng file + tool

**Vấn đề đang có (theo nhóm trưởng, 11/08/2026):** phân công việc đang dựa vào lời nói — không có cách nào biết "ai đã làm tới đâu" mà không phải hỏi trực tiếp từng người, và không biết khi nào cả 4 người cùng xong 1 sprint để merge.

**Giải pháp:** mỗi người có 1 file checklist riêng ở đây (`HAIANH.md`, `BINH.md`, `CHUNG.md`, `DANG.md`), tick `[x]` khi việc **đã test thật** — không phải "code xong nhưng chưa chắc chạy". Vì file nằm trong git, nhóm trưởng chỉ cần `git pull` + chạy 1 lệnh là biết ngay ai đang ở đâu, không cần hỏi. Lịch sử commit của các file này chính là "log từng người" — xem `git log --follow docs/archive/planning-v2/progress/HAIANH.md` để biết Hải Anh tick việc gì vào lúc nào.

---

## 1. Quy chuẩn chung — tất cả 4 file dùng cùng 1 cấu trúc

Mỗi file có đúng các mục (section `##`) sau, theo đúng thứ tự thời gian đã chốt ở `03-Cursus-Execution-Plan.md`:

1. `Sprint 0 — 11/08 (T3)`
2. `Sprint 0 — 12/08 (T4)`
3. `🎯 Milestone — 13/08 (T5): "1 flow hoàn chỉnh"`
4. `Sprint 1 — Gate 2 (14/08, T6)`
5. `Sprint 2 — Mốc 3 (15-22/08)`
6. `Final — 23/08`
7. `Definition of Done` (gate chất lượng cuối — không phải việc theo ngày, mà là danh sách bắt buộc đúng trước khi coi role đó "xong")

**Việc trong mỗi mục lấy đúng nguyên văn từ mục 6-7 của file role tương ứng** (`docs/archive/planning-v2/roles/<TÊN>_....md`) — file progress không tự phát sinh thêm việc mới. Nếu scope thực tế đổi, sửa cả 2 file cho khớp, đừng để 2 nơi lệch nhau.

## 2. Quy tắc tick — đọc trước khi tick

- ✅ **Chỉ tick khi đã test thật** (chạy trên máy, thấy dữ liệu đúng, không lỗi console) — không tick vì "chắc là chạy được".
- ❌ **Không tick trước cho oai** — nếu nhóm trưởng kiểm tra thấy tick nhưng không chạy được, đây là vấn đề tin cậy, không phải vấn đề kỹ thuật.
- 📝 **Commit ngay khi tick** — đừng gộp tick 10 việc vào 1 commit cuối tuần, mất hết giá trị "log theo thời gian thực".
- 🔄 Nếu 1 việc đã tick nhưng sau đó phát hiện lỗi (regression) — bỏ tick lại `[ ]`, không giữ tick sai.

## 3. Cách chạy — hướng dẫn từng bước

### 3.0 Yêu cầu trước khi chạy

- Có sẵn Python 3 (bất kỳ bản nào ≥3.9 đều được — script chỉ dùng thư viện chuẩn, không cần `pip install` gì).
- Đứng ở **thư mục gốc repo** (`D:\VINAI_Team_093\P-093` hoặc tương đương trên máy bạn) khi chạy lệnh — script tự tìm `docs/archive/planning-v2/progress/` từ vị trí file script, không phụ thuộc bạn đang ở đâu, nhưng để chắc ăn cứ đứng ở root.
- ⚠️ **`make progress` chỉ chạy được nếu máy đã cài `make`** (có sẵn trên macOS/Linux/Git Bash có MSYS, nhưng **không có sẵn trên PowerShell/CMD thuần của Windows**). Nếu gõ `make progress` mà báo `'make' is not recognized` hoặc `command not found` — dùng thẳng lệnh `python scripts/progress_report.py` bên dưới, tác dụng y hệt, không cần cài thêm gì.

### 3.1 Xem tiến độ TẤT CẢ mọi người (bảng tổng quan)

```bash
python scripts/progress_report.py
```

Chạy được y hệt trên PowerShell, CMD, Git Bash, macOS/Linux Terminal — không cần đổi cú pháp gì.

### 3.2 Xem tiến độ của TỪNG NGƯỜI riêng lẻ

Dùng `--person <TÊN>` (không phân biệt hoa/thường, đúng theo tên file trong `docs/archive/planning-v2/progress/`) để chỉ xem 1 người, kèm chi tiết **còn thiếu đúng những việc gì** (không chỉ số %):

```bash
python scripts/progress_report.py --person DANG      # Trịnh Hải Đăng
python scripts/progress_report.py --person HAIANH    # Nguyễn Hải Anh
python scripts/progress_report.py --person BINH      # Nguyễn Anh Bình
python scripts/progress_report.py --person CHUNG     # Nguyễn Đức Chung
```

**Ví dụ output thật** (chạy `--person HAIANH` khi chưa tick gì):

```
=== HAIANH — việc còn thiếu ===

[Sprint 0 — 11/08 (T3)] (0/4)
  - [ ] Đã đọc `docs/archive/planning-v2/roles/HAIANH_student.md` và `docs/frontend/00_AI_CONTEXT_PACK.md`
  - [ ] Thêm trạng thái Error còn thiếu ở khối Plan (`StudentHome.jsx`)
  - [ ] Kiểm tra lại UI hiện tại theo `docs/frontend/08_SCREEN_CONSISTENCY_CHECKLIST.md`
  - [ ] Xác nhận i18n đủ 2 ngôn ngữ cho mọi chuỗi hiện có
...
```

Khi 1 mục đã tick hết, mục đó biến mất khỏi danh sách "còn thiếu" — output ngắn dần theo thời gian, đúng bằng đúng những việc chưa xong.

### 3.3 Ghi lại thành file để commit (mốc lịch sử)

```bash
python scripts/progress_report.py --out docs/archive/planning-v2/progress/SNAPSHOT.md
git add docs/archive/planning-v2/progress/SNAPSHOT.md
git commit -m "chore: progress snapshot 11/08"
```

Làm việc này cuối mỗi ngày/mỗi sprint — sau này `git log -p docs/archive/planning-v2/progress/SNAPSHOT.md` cho thấy % thay đổi theo từng ngày, dùng thẳng số liệu này khi viết `JOURNAL.md` hoặc báo cáo BTC.

### 3.4 Nếu máy có cài `make` (tuỳ chọn, không bắt buộc)

```bash
make progress             # = python scripts/progress_report.py
make progress-snapshot    # = python scripts/progress_report.py --out docs/archive/planning-v2/progress/SNAPSHOT.md
```

**Đọc bảng thế nào:** mỗi ô là `số việc đã xong/tổng số việc (phần trăm)`. Cột cuối `**Tổng**` là tổng toàn bộ sprint của người đó. Khi cả 4 dòng ở cột `Sprint 1 — Gate 2` đều 100% → biết ngay đã đến lúc merge/freeze cho Gate 2, không cần hỏi vòng quanh.

## 4. Quy trình đề xuất cho nhóm trưởng

1. Đầu ngày: `make progress` — xem tối qua ai đã tick gì, ai đang chậm so với `03-Cursus-Execution-Plan.md`.
2. Trước khi ra quyết định merge/freeze 1 sprint: chạy `make progress`, xác nhận cột sprint đó đủ 4 dòng gần 100% (không nhất thiết 100% tuyệt đối cho mọi mục phụ, nhưng cột 🎯 Milestone và Definition of Done nên gần đủ).
3. Cuối mỗi sprint: `make progress-snapshot` rồi commit — tạo mốc lịch sử để sau này viết `JOURNAL.md`/báo cáo BTC có số liệu thật, không phải nhớ lại.
4. Nếu 1 người liên tục 0% nhiều ngày — đây là tín hiệu khách quan để hỏi trực tiếp, không phải phỏng đoán.

## 5. Giới hạn cần biết (để không quá tin tưởng mù quáng vào công cụ)

- Đây là hệ thống **tự báo cáo (self-reported)** — dựa vào việc mỗi người trung thực khi tick, không tự động verify bằng cách chạy test/CI. Nếu cần độ tin cậy cao hơn, có thể nâng cấp sau: viết CI job chạy `pytest`/`npm run build` và chỉ cho phép tick nếu pipeline xanh (không làm ở Gate 2 vì tốn thời gian setup không cần thiết cho quy mô 4 người).
- Không thay thế `WORKLOG.md` (nhật ký công việc theo ngày, có mô tả, dùng cho deliverable BTC) — 2 hệ thống bổ sung nhau: `WORKLOG.md` trả lời "hôm nay làm gì", file progress trả lời "tổng thể còn thiếu gì so với chuẩn đã định".
