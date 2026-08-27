"""Curated FAQ answers for Study Assistant — answered without calling the LLM."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FaqEntry:
    id: str
    subject_code: str
    keywords: tuple[str, ...]
    answer: str
    source_label: str
    # Minimum keyword hits required (after folding).
    min_hits: int = 1
    # mục 16 data contract: True when this entry paraphrases fabricated demo
    # content (student_mock_data_service.COURSE_DOCUMENTS — CEA201/PRF192
    # have no official syllabus behind them), not an official_document.
    # FaqService disclaims these the same way QaAnswerService disclaims
    # retrieval answers grounded in source=mock chunks.
    is_mock: bool = False


# Keywords are matched on accent-folded lowercase text.
FAQ_ENTRIES: tuple[FaqEntry, ...] = (
    # ---- SSA101 ----
    FaqEntry(
        id="ssa101_commitment_map",
        subject_code="SSA101",
        keywords=(
            "weekly commitment map",
            "commitment map",
            "ban do cam ket",
            "bản đồ cam kết",
            "cam ket hoc tap",
        ),
        answer=(
            "Weekly Commitment Map (Bản đồ cam kết học tập tuần) giúp bạn chuyển từ "
            "“đi học theo lịch” sang tự quản việc học: liệt kê mọi cam kết "
            "(lecture/lab/assignment/PE), ước lượng giờ, chọn 3 việc ưu tiên và "
            "1 slot deep-work cố định, rồi review cuối tuần."
        ),
        source_label="SSA101 Buổi 1 — Weekly Commitment Map",
        min_hits=1,
    ),
    FaqEntry(
        id="ssa101_smart",
        subject_code="SSA101",
        keywords=("smart", "muc tieu smart", "goal setting", "pomodoro", "time blocking"),
        answer=(
            "Mục tiêu SMART = Specific, Measurable, Achievable, Relevant, Time-bound. "
            "SSA101 khuyến nghị gắn mục tiêu với Pomodoro/time-blocking và phân biệt "
            "động lực intrinsic vs extrinsic. Ví dụ: hoàn thành Lab trước 21:00 thứ Năm "
            "bằng 3 phiên Pomodoro 25 phút."
        ),
        source_label="SSA101 Buổi 2 — SMART goals",
        min_hits=1,
    ),
    FaqEntry(
        id="ssa101_syllabus_summary",
        subject_code="SSA101",
        keywords=("tom tat syllabus", "summarize syllabus", "syllabus ssa101", "noi dung mon"),
        answer=(
            "SSA101 (Academic Skills) tập trung: văn hóa học thuật, quản lý thời gian/"
            "Weekly Commitment Map, SMART goals, information literacy, critical thinking "
            "và academic integrity. Đánh giá mock gồm Commitment Map, SMART plan, "
            "reflection và capstone."
        ),
        source_label="SSA101 Syllabus — Academic Skills",
        min_hits=1,
    ),
    FaqEntry(
        id="ssa101_integrity",
        subject_code="SSA101",
        keywords=(
            "academic integrity",
            "liem chinh",
            "plagiarism",
            "dao van",
            "trich dan nguon",
        ),
        answer=(
            "Academic integrity yêu cầu dùng nguồn có trách nhiệm: tìm–lọc–đánh giá "
            "nguồn, trích dẫn đúng và không đạo văn. Assistant có thể gợi ý hướng học "
            "nhưng không làm hộ bài tập."
        ),
        source_label="SSA101 Syllabus — Academic integrity",
        min_hits=1,
    ),
    # ---- PRF192 ----
    FaqEntry(
        id="prf192_lab02",
        subject_code="PRF192",
        keywords=("lab 02", "lab02", "loops", "arrays", "mang", "vong lap"),
        answer=(
            "Lab 02 (Loops & Arrays) yêu cầu bằng C11: nhập mảng, tính tổng/max/min, "
            "đảo ngược mảng in-place, và với ma trận in đường chéo chính (nếu vuông). "
            "Nộp file .c + screenshot ít nhất 2 test cases."
        ),
        source_label="PRF192 Lab 02 — Loops & Arrays",
        min_hits=1,
        is_mock=True,
    ),
    FaqEntry(
        id="prf192_c11",
        subject_code="PRF192",
        keywords=("c11", "chuan c", "standard c", "dev-c", "compiler"),
        answer=(
            "PRF192 dùng chuẩn C11; môi trường phổ biến là Dev-C++ hoặc VS Code + GCC. "
            "Nên tránh extension không chuẩn khi luyện PE."
        ),
        source_label="PRF192 Syllabus — Programming Fundamentals with C",
        min_hits=1,
        is_mock=True,
    ),
    FaqEntry(
        id="prf192_pe",
        subject_code="PRF192",
        keywords=("practical exam", "pe ", " thi pe", "diem pe", "assessment"),
        answer=(
            "Theo syllabus mock PRF192: Labs/Workshops ~30%, Progress tests ~20%, "
            "Practical Exam (PE) ~50%. PE thường dùng môi trường máy thi quy định."
        ),
        source_label="PRF192 Syllabus — Assessment",
        min_hits=1,
        is_mock=True,
    ),
    FaqEntry(
        id="prf192_syllabus_summary",
        subject_code="PRF192",
        keywords=("tom tat syllabus", "summarize syllabus", "syllabus prf192", "outline"),
        answer=(
            "PRF192 đi từ intro C, kiểu dữ liệu/toán tử, hệ đếm, if/switch, vòng lặp, "
            "hàm, mảng 1D/2D, string & pointer intro, rồi workshop/PE. Trọng tâm là "
            "viết chương trình C có cấu trúc và debug được."
        ),
        source_label="PRF192 Syllabus — Programming Fundamentals with C",
        min_hits=1,
        is_mock=True,
    ),
    FaqEntry(
        id="prf192_array_function",
        subject_code="PRF192",
        keywords=("pass array", "truyen mang", "pointer", "mang vao ham"),
        answer=(
            "Khi truyền mảng vào hàm trong C, mảng decay thành pointer. Nên truyền "
            "kèm size (ví dụ `void f(int a[], int n)` hoặc `int *a`) và không giả định "
            "hàm biết được độ dài mảng từ kiểu."
        ),
        source_label="PRF192 FAQ",
        min_hits=1,
        is_mock=True,
    ),
    # ---- CEA201 ----
    FaqEntry(
        id="cea201_datapath",
        subject_code="CEA201",
        keywords=("datapath", "cpu", "alu", "register file", "control signal"),
        answer=(
            "CPU datapath gồm register file, ALU, PC/IR, cổng memory và mux chọn nguồn. "
            "Với lệnh R-type: fetch → decode/đọc register → ALU → ghi rd (RegWrite=1). "
            "Worksheet thường yêu cầu điền thêm control signals cho load/store/branch."
        ),
        source_label="CEA201 Lecture — CPU Datapath & Control",
        min_hits=1,
        is_mock=True,
    ),
    FaqEntry(
        id="cea201_cache",
        subject_code="CEA201",
        keywords=("cache", "hit", "miss", "memory hierarchy", "mapping"),
        answer=(
            "Memory hierarchy: Registers → L1/L2 cache → Main memory → Secondary storage. "
            "Direct-mapped: mỗi block memory map vào đúng 1 line cache. "
            "Average access time ≈ hit_time + miss_rate × miss_penalty."
        ),
        source_label="CEA201 Lecture — Cache Memory",
        min_hits=1,
        is_mock=True,
    ),
    FaqEntry(
        id="cea201_syllabus_summary",
        subject_code="CEA201",
        keywords=("tom tat syllabus", "summarize syllabus", "syllabus cea201"),
        answer=(
            "CEA201 (Computer Organization & Architecture) gồm: hiệu năng, bus, "
            "memory/cache, I/O & interrupt, cấu trúc CPU, instruction set/addressing, "
            "pipelining intro và hỗ trợ OS."
        ),
        source_label="CEA201 Syllabus — Computer Organization & Architecture",
        min_hits=1,
        is_mock=True,
    ),
    # ---- CSI106 ----
    FaqEntry(
        id="csi106_data_rep",
        subject_code="CSI106",
        keywords=(
            "data representation",
            "binary",
            "hex",
            "ascii",
            "unicode",
            "2's complement",
            "bieu dien du lieu",
        ),
        answer=(
            "Quiz Data Representation thường gồm: đổi binary↔decimal↔hex, ASCII/"
            "Unicode, số có dấu (2's complement) và số bit cần để biểu diễn một giá trị."
        ),
        source_label="CSI106 FAQ — Quiz & concepts",
        min_hits=1,
    ),
    FaqEntry(
        id="csi106_tcp_udp",
        subject_code="CSI106",
        keywords=(
            "tcp",
            "udp",
            "tcp va udp",
            "tcp and udp",
            "difference between tcp",
            "protocol",
        ),
        answer=(
            "TCP là connection-oriented và hướng tới truyền tin cậy; UDP là "
            "connectionless, nhẹ hơn, phù hợp khi chấp nhận mất gói để giảm độ trễ."
        ),
        source_label="CSI106 FAQ — Quiz & concepts",
        min_hits=1,
    ),
    FaqEntry(
        id="csi106_algorithm",
        subject_code="CSI106",
        keywords=("thuat toan", "algorithm", "pseudocode", "flowchart", "binary search"),
        answer=(
            "Thuật toán là dãy bước hữu hạn, xác định để giải một bài toán. Có thể "
            "biểu diễn bằng pseudocode/flowchart/ngôn ngữ lập trình. Ví dụ intro: "
            "linear search O(n) vs binary search O(log n) trên mảng đã sắp xếp."
        ),
        source_label="CSI106 Lecture — Algorithms intro",
        min_hits=1,
    ),
    FaqEntry(
        id="csi106_syllabus_summary",
        subject_code="CSI106",
        keywords=("tom tat syllabus", "summarize syllabus", "syllabus csi106"),
        answer=(
            "CSI106 nhập môn CS: mô hình von Neumann, biểu diễn dữ liệu, logic Boolean "
            "intro, thuật toán, khái niệm ngôn ngữ lập trình, OS overview, mạng/"
            "TCP-IP và ethics/security cơ bản."
        ),
        source_label="CSI106 Syllabus — Introduction to Computer Science",
        min_hits=1,
    ),
    FaqEntry(
        id="csi106_von_neumann",
        subject_code="CSI106",
        keywords=("von neumann", "harvard", "kien truc may tinh"),
        answer=(
            "Mô hình von Neumann dùng chung bộ nhớ cho instruction và data; "
            "kiến trúc Harvard tách riêng instruction memory và data memory (ở mức khái niệm)."
        ),
        source_label="CSI106 FAQ — Quiz & concepts",
        min_hits=1,
    ),
)
