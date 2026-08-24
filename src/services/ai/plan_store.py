"""Lưu trữ kế hoạch tuần trong bộ nhớ tiến trình.

Mốc 1 chỉ cần sinh viên sửa/xoá task trước khi chốt kế hoạch (FR-3.2), chưa cần
lưu lịch sử phiên bản. Ghi đè trong RAM là đủ và tránh phải viết migration mới.

Nợ kỹ thuật đã biết: dữ liệu mất khi restart, chưa tách theo người dùng. Mốc 2
chuyển xuống bảng `weekly_plans` / `study_tasks` đã có sẵn trong schema.
"""

from __future__ import annotations

import threading

from src.services.ai.planner import PlanTask


class PlanStore:
    """Kho kế hoạch theo `plan_id`, an toàn khi nhiều request chạy song song."""

    def __init__(self) -> None:
        self._plans: dict[str, list[PlanTask]] = {}
        self._task_index: dict[str, str] = {}
        self._lock = threading.Lock()

    def save(self, plan_id: str, tasks: list[PlanTask]) -> None:
        """Ghi đè toàn bộ task của một kế hoạch."""
        with self._lock:
            self._plans[plan_id] = list(tasks)
            for task in tasks:
                self._task_index[task["task_id"]] = plan_id

    def get_tasks(self, plan_id: str) -> list[PlanTask] | None:
        with self._lock:
            tasks = self._plans.get(plan_id)
            return list(tasks) if tasks is not None else None

    def find_plan_id(self, task_id: str) -> str | None:
        with self._lock:
            return self._task_index.get(task_id)

    def edit_task(self, task_id: str, title: str | None, duration_estimate: str | None) -> list[PlanTask] | None:
        """Sửa tiêu đề và/hoặc thời lượng. Trả danh sách task sau khi sửa, None nếu không tìm thấy."""
        with self._lock:
            plan_id = self._task_index.get(task_id)
            if plan_id is None:
                return None
            for task in self._plans[plan_id]:
                if task["task_id"] == task_id:
                    if title:
                        task["title"] = title
                    if duration_estimate:
                        task["duration_estimate"] = duration_estimate
                    break
            return list(self._plans[plan_id])

    def delete_task(self, task_id: str) -> list[PlanTask] | None:
        """Xoá task. Trả danh sách còn lại, None nếu không tìm thấy."""
        with self._lock:
            plan_id = self._task_index.pop(task_id, None)
            if plan_id is None:
                return None
            self._plans[plan_id] = [t for t in self._plans[plan_id] if t["task_id"] != task_id]
            return list(self._plans[plan_id])

    def clear(self) -> None:
        """Dọn sạch — dùng trong test."""
        with self._lock:
            self._plans.clear()
            self._task_index.clear()


plan_store = PlanStore()
