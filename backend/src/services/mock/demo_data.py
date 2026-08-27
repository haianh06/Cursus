"""Đọc dữ liệu mô phỏng dùng cho màn Giảng viên và Admin ở Mốc 1.

Playbook chỉ định các màn F4-F7 đọc thẳng từ file JSON đã sinh sẵn, không tính
toán lại: `seed_students_SSA101.json` (12 SV, 4 tuần, alert đã tính theo công
thức trong PRD) và `courses_BIT_SE_K20D_K21A.json` (48 môn ngành SE).

Nợ kỹ thuật đã biết: Mốc 2 chuyển sang tính từ bảng `study_tasks` / `risk_signals`
thay vì đọc file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = ROOT / "docs" / "planning" / "v2" / "data"
CLASS_SNAPSHOT_FILE = "seed_students_SSA101.json"
CURRICULUM_FILE = "courses_BIT_SE_K20D_K21A.json"


def load_class_snapshot() -> dict[str, Any]:
    """Số liệu lớp SSA101: `class_summary`, `students`, `kpi_comparison`."""
    return _read_json(CLASS_SNAPSHOT_FILE)


def load_curriculum() -> dict[str, Any]:
    """Chương trình đào tạo: `curriculum_meta`, `subjects`, `subject_count`."""
    return _read_json(CURRICULUM_FILE)


def _read_json(filename: str) -> dict[str, Any]:
    path = DATA_DIR / filename
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("demo_data_unreadable", extra={"path": str(path), "error": str(exc)})
        return {}
