"""Team progress report — đọc docs/planning/v2/progress/*.md, đếm checkbox theo
từng sprint (mỗi khối "## ...") và in bảng % hoàn thành mỗi người / mỗi sprint.

Đây là "tool" thay cho việc hỏi tiến độ bằng lời nói: mỗi thành viên tick [x] vào
đúng file progress của mình khi việc đã test thật (không phải "code xong nhưng
chưa chắc chạy"), commit thường xuyên — nhóm trưởng chạy script này bất kỳ lúc
nào để biết ai đang ở đâu, không cần hỏi.

Cách dùng:
    python scripts/progress_report.py                 # in bảng ra terminal
    python scripts/progress_report.py --out docs/planning/v2/progress/SNAPSHOT.md
                                                        # đồng thời ghi bản snapshot
                                                        # markdown để commit làm bằng
                                                        # chứng lịch sử (git log sẽ
                                                        # cho thấy % thay đổi theo ngày)
    python scripts/progress_report.py --person HAIANH  # chỉ xem 1 người, in chi tiết
                                                        # từng dòng còn thiếu

Không phụ thuộc thư viện ngoài — chỉ dùng stdlib, chạy được bằng python3 trần.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Windows terminals often default to cp1252, which cannot encode Vietnamese
# diacritics — force UTF-8 stdout/stderr so this runs the same on every OS.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

PROGRESS_DIR = Path(__file__).resolve().parent.parent / "docs" / "planning" / "v2" / "progress"

SECTION_RE = re.compile(r"^##\s+(.*)")
CHECKBOX_RE = re.compile(r"^\s*-\s*\[( |x|X)\]\s*(.*)")


@dataclass
class SectionProgress:
    name: str
    items: list[tuple[bool, str]] = field(default_factory=list)

    @property
    def done(self) -> int:
        return sum(1 for checked, _ in self.items if checked)

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def pct(self) -> int | None:
        return None if self.total == 0 else round(100 * self.done / self.total)


def parse_file(path: Path) -> list[SectionProgress]:
    sections: list[SectionProgress] = []
    current: SectionProgress | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = SECTION_RE.match(line)
        if m:
            current = SectionProgress(name=m.group(1).strip())
            sections.append(current)
            continue
        m = CHECKBOX_RE.match(line)
        if m and current is not None:
            checked = m.group(1).lower() == "x"
            current.items.append((checked, m.group(2).strip()))
    return sections


def pct_str(pct: int | None) -> str:
    return "—" if pct is None else f"{pct}%"


def build_table(all_people: dict[str, list[SectionProgress]]) -> str:
    # Union of section names, in first-seen order (files are meant to share the
    # same sprint structure — if one drifts, it still shows up, just misaligned).
    section_names: list[str] = []
    for sections in all_people.values():
        for s in sections:
            if s.name not in section_names:
                section_names.append(s.name)

    header = ["Người"] + section_names + ["**Tổng**"]
    rows = [header, ["---"] * len(header)]

    for person, sections in all_people.items():
        by_name = {s.name: s for s in sections}
        row = [f"**{person}**"]
        total_done = total_all = 0
        for name in section_names:
            s = by_name.get(name)
            if s is None:
                row.append("—")
                continue
            row.append(f"{s.done}/{s.total} ({pct_str(s.pct)})")
            total_done += s.done
            total_all += s.total
        overall = None if total_all == 0 else round(100 * total_done / total_all)
        row.append(f"**{total_done}/{total_all} ({pct_str(overall)})**")
        rows.append(row)

    lines = ["| " + " | ".join(r) for r in rows]
    return "\n".join(line + " |" for line in lines)


def print_person_detail(person: str, sections: list[SectionProgress]) -> None:
    print(f"\n=== {person} — việc còn thiếu ===")
    any_missing = False
    for s in sections:
        remaining = [text for checked, text in s.items if not checked]
        if remaining:
            any_missing = True
            print(f"\n[{s.name}] ({s.done}/{s.total})")
            for text in remaining:
                print(f"  - [ ] {text}")
    if not any_missing:
        print("  Không còn việc nào chưa tick — kiểm tra lại có đúng đã test thật chưa trước khi coi là xong.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, help="Ghi bảng ra file markdown (để commit làm bằng chứng lịch sử)")
    parser.add_argument("--person", type=str, help="Chỉ in chi tiết việc còn thiếu của 1 người (tên file không kèm .md)")
    args = parser.parse_args()

    if not PROGRESS_DIR.exists():
        print(f"Không tìm thấy thư mục {PROGRESS_DIR}")
        raise SystemExit(1)

    skip_stems = {"SNAPSHOT", "README"}
    files = sorted(PROGRESS_DIR.glob("*.md"))
    files = [f for f in files if f.stem.upper() not in skip_stems]
    if not files:
        print(f"Không tìm thấy file progress nào trong {PROGRESS_DIR}")
        raise SystemExit(1)

    all_people = {f.stem: parse_file(f) for f in files}

    if args.person:
        key = args.person.upper()
        if key not in all_people:
            print(f"Không tìm thấy '{args.person}'. Có: {', '.join(all_people)}")
            raise SystemExit(1)
        print_person_detail(key, all_people[key])
        return

    table = build_table(all_people)
    print(table)

    if args.out:
        timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
        content = (
            f"# Progress Snapshot\n\n"
            f"Sinh tự động bởi `python scripts/progress_report.py --out ...` lúc {timestamp}. "
            f"Không sửa tay file này — sửa trực tiếp trong `docs/planning/v2/progress/<TÊN>.md` rồi chạy lại script.\n\n"
            f"{table}\n"
        )
        args.out.write_text(content, encoding="utf-8")
        print(f"\nĐã ghi snapshot vào {args.out}")


if __name__ == "__main__":
    main()
