# `data/` — Kho học liệu thật (FPT FLM) dùng cho RAG

File này **được track trong git** (ngoại lệ trong `.gitignore`) dù toàn bộ `data/`
không được commit — mục đích là giữ lại tài liệu cấu trúc/quy ước đặt tên ngay cả
khi máy khác clone về chưa có dữ liệu thật.

## Vì sao `data/` bị gitignore

Đây là học liệu thật (syllabus, slide) lấy từ hệ thống FLM của FPT University,
cấp cho chương trình **BIT_SE_K20D_K21A**. Không commit vì (1) dung lượng lớn,
(2) không phải sở hữu của team để public trong repo. Chỉ tồn tại trên máy dev nào
đã tải về.

## Cấu trúc

```
data/
├── raw/                        # Nguyên bản export trực tiếp từ FLM, KHÔNG sửa
│   ├── curriculum_plo_map.docx     # Bảng map môn học -> Program Learning Outcomes
│   └── courses/<SUBJECT_CODE>.docx # 1 file / môn, tên = đúng Subject Code trên FLM
│
├── clean/                      # Bản đã format lại bảng (table-preserved), sẵn sàng
│   │                            # làm input cho docs/planning/v2/scripts/flm_parser.py
│   ├── curriculum_plo_map.docx
│   ├── curriculum_overview.docx    # Curriculum Details tổng quan (chỉ có ở clean/,
│   │                                # raw/ chưa có bản gốc tương ứng — xem "Gaps")
│   └── courses/
│       ├── <SUBJECT_CODE>.docx     # Đa số môn: 1 file phẳng
│       └── CSI106/                 # Môn duy nhất có thêm slide bài giảng
│           ├── CSI106.docx
│           └── slides/CSI_01.pptx … CSI_12.pptx
│
├── uploads/          # Runtime — bài nộp của SV, KHÔNG đụng vào (đọc code bên dưới)
├── admin_uploads/    # Runtime — tài liệu GV/admin ingest qua UI, KHÔNG đụng vào
└── app.db            # Runtime — SQLite fallback khi không dùng Postgres
```

## Quy ước đặt tên file môn học

Tên file = **đúng Subject Code trên FLM**, viết hoa, nối bằng `_`, không dấu
cách/dấu ngoặc/ký tự đặc biệt — kể cả với các "slot" tổ hợp/tự chọn không phải
1 môn cố định (ví dụ `SE_COM_1`, `PHE_COM_2`, `SE_GRA_ELE`, `TMI_ELE` — đây là mã
combo/elective thật do FLM đặt, không phải lỗi đặt tên, xem field `Subject Code`
trong chính nội dung docx để đối chiếu).

`flm_parser.py` đọc **Subject Code từ nội dung file docx** (bảng `Field/Value`),
không parse từ tên file — nên đổi tên file trong `data/` không ảnh hưởng gì tới
script, chỉ ảnh hưởng khả năng đọc/tra cứu bằng mắt của người.

## Gaps đã biết (chưa xử lý, cần format trước khi ingest)

- `raw/courses/EXE101.docx` và `raw/courses/SWT301.docx` **chưa có bản `clean/`
  tương ứng** — 2 môn này chưa qua bước "table-preserved formatting".
- `clean/curriculum_overview.docx` (Curriculum Details tổng quan, tiếng Việt)
  **chưa có bản `raw/` tương ứng** — có thể do lúc export quên lưu bản gốc.

## KHÔNG nhầm với `docs/planning/v2/data/`

Đây là **hai thư mục "data" khác mục đích hoàn toàn**:

| | `data/` (file này) | `docs/planning/v2/data/` |
|---|---|---|
| Nội dung | `.docx`/`.pptx` thô, học liệu gốc | `.json` đã chunk sẵn (output của `flm_parser.py`) |
| Ai đọc lúc runtime | Không ai — chưa nối vào pipeline | `src/services/rag/rag.py` (`DATA_DIR`), `src/services/mock/demo_data.py` — **đọc thật khi chạy app** |
| Có nên di chuyển? | Có, tự do (không ai reference path) | **Không** — di chuyển sẽ break RAG runtime trừ khi sửa code kèm theo |

Việc convert `data/clean/courses/*.docx` → `docs/planning/v2/data/chunks_*.json`
qua `flm_parser.py` hiện **mới làm cho SSA101**, 46 môn còn lại trong `clean/`
chưa được ingest — đây là backlog RAG coverage, không phải lỗi tổ chức file.
