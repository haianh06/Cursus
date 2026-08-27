"""Sinh kế hoạch tuần từ mục tiêu của sinh viên (FR-3.1).

Luồng: mục tiêu → retrieve top-k chunk syllabus → LLM chia thành 3-7 task, mỗi
task bắt buộc gắn `source_label` lấy nguyên văn từ chunk đã dùng.

Khi chưa cấu hình API key thật, module rơi về bản dựng task tất định từ chính
các chunk lấy được. Task khi đó ít tinh tế hơn nhưng **vẫn trích nguồn thật**,
nên luồng end-to-end và UI vẫn kiểm chứng được mà không tốn tiền gọi LLM.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TypedDict

from src.config import Settings, get_settings
from src.services.core.llm import get_llm
from src.services.rag import rag

logger = logging.getLogger(__name__)

MIN_TASKS = 3
MAX_TASKS = 7
RETRIEVAL_TOP_K = 5

NO_SOURCE_WARNING = "Không tìm thấy dữ liệu môn cụ thể, đề xuất mang tính tham khảo."

SYSTEM_PROMPT = """Bạn là trợ giảng học thuật, giúp sinh viên chia mục tiêu tuần thành các việc nhỏ khả thi.

QUY TẮC BẮT BUỘC:
1. Chỉ dùng thông tin trong phần TÀI LIỆU MÔN HỌC được cung cấp. Không suy diễn ngoài tài liệu.
2. Mỗi task phải có "source_label" sao chép NGUYÊN VĂN từ nhãn nguồn của đoạn tài liệu bạn đã dựa vào.
3. Sinh từ 3 đến 7 task, sắp xếp theo thứ tự nên làm trước - sau.
4. "duration_estimate" viết dạng ngắn gọn: "30m", "1.5h", "2h".
5. Tiêu đề task phải cụ thể, hành động được ngay, viết bằng tiếng Việt.
6. Chỉ trả về JSON hợp lệ theo đúng schema, không thêm lời dẫn hay markdown.

SCHEMA:
{"tasks": [{"title": "...", "duration_estimate": "...", "source_label": "..."}]}"""


class PlanTask(TypedDict):
    task_id: str
    title: str
    duration_estimate: str
    source_label: str


class PlanResult(TypedDict):
    tasks: list[PlanTask]
    warning: str | None


def make_plan(goal_text: str, subject_code: str) -> PlanResult:
    """Chia mục tiêu tuần thành 3-7 task có trích nguồn syllabus.

    `warning` khác None nghĩa là không tìm được nội dung môn tương ứng — UI phải
    hiển thị cảnh báo đó thay vì trình bày kế hoạch như thể đã có căn cứ.
    """
    chunks = rag.retrieve(goal_text, subject_code, k=RETRIEVAL_TOP_K)
    if not chunks:
        return {"tasks": _fallback_tasks(goal_text, chunks=[]), "warning": NO_SOURCE_WARNING}

    settings = get_settings()
    if not _has_real_api_key(settings):
        logger.info("planner_using_deterministic_fallback")
        return {"tasks": _fallback_tasks(goal_text, chunks), "warning": None}

    try:
        tasks = _generate_with_llm(goal_text, chunks)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning("planner_llm_output_invalid", extra={"error": str(exc)})
        return {"tasks": _fallback_tasks(goal_text, chunks), "warning": None}
    except Exception as exc:  # noqa: BLE001 - lỗi mạng/SDK không được làm hỏng demo
        logger.error("planner_llm_call_failed", extra={"error": str(exc)})
        return {"tasks": _fallback_tasks(goal_text, chunks), "warning": None}

    return {"tasks": tasks, "warning": None}


def _generate_with_llm(goal_text: str, chunks: list[rag.Chunk]) -> list[PlanTask]:
    """Gọi LLM và ép kết quả về đúng schema đã cam kết với frontend."""
    response = get_llm().invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("human", _build_user_prompt(goal_text, chunks)),
        ]
    )
    payload = _parse_json_object(str(response.content))
    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise ValueError("LLM không trả về danh sách task")

    allowed_labels = {chunk["source_label"] for chunk in chunks}
    default_label = chunks[0]["source_label"]
    tasks = [
        _normalize_task(item, index, allowed_labels, default_label)
        for index, item in enumerate(raw_tasks[:MAX_TASKS], start=1)
        if isinstance(item, dict) and str(item.get("title", "")).strip()
    ]
    if len(tasks) < MIN_TASKS:
        raise ValueError(f"LLM chỉ trả {len(tasks)} task, tối thiểu cần {MIN_TASKS}")
    return tasks


def _normalize_task(
    item: dict,
    index: int,
    allowed_labels: set[str],
    default_label: str,
) -> PlanTask:
    """Chuẩn hoá 1 task và chặn nhãn nguồn bịa.

    LLM đôi khi tự chế `source_label`; chỉ chấp nhận nhãn thuộc đúng các chunk đã
    truy xuất, sai thì thay bằng nhãn của chunk liên quan nhất.
    """
    label = str(item.get("source_label", "")).strip()
    if label not in allowed_labels:
        logger.info("planner_source_label_rejected", extra={"label": label})
        label = default_label
    return {
        "task_id": f"t{index}",
        "title": str(item["title"]).strip(),
        "duration_estimate": str(item.get("duration_estimate", "1h")).strip() or "1h",
        "source_label": label,
    }


def _build_user_prompt(goal_text: str, chunks: list[rag.Chunk]) -> str:
    excerpts = "\n\n".join(f"[Nguồn: {chunk['source_label']}]\n{chunk['text']}" for chunk in chunks)
    return f"MỤC TIÊU TUẦN CỦA SINH VIÊN:\n{goal_text}\n\nTÀI LIỆU MÔN HỌC:\n{excerpts}"


def _parse_json_object(content: str) -> dict:
    """Bóc JSON khỏi output LLM, chịu được trường hợp bị bọc trong ```json."""
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise ValueError("Không tìm thấy JSON trong output của LLM")
    return json.loads(match.group(0))


def _fallback_tasks(goal_text: str, chunks: list[rag.Chunk]) -> list[PlanTask]:
    """Kế hoạch tất định khi không gọi được LLM.

    Vẫn bám vào chunk thật nên `source_label` là nguồn có thật, không phải nhãn
    trang trí.
    """
    goal = goal_text.strip() or "mục tiêu tuần"
    if not chunks:
        return [
            {"task_id": "t1", "title": f"Xác định phạm vi: {goal}", "duration_estimate": "30m", "source_label": ""},
            {"task_id": "t2", "title": "Lập dàn ý các bước thực hiện", "duration_estimate": "1h", "source_label": ""},
            {"task_id": "t3", "title": "Rà soát lại và chốt kết quả", "duration_estimate": "45m", "source_label": ""},
        ]

    templates = [
        ("Đọc và tóm tắt nội dung: {section}", "45m"),
        ("Đối chiếu {section} với yêu cầu của mục tiêu tuần", "1h"),
        ("Thực hành phần trọng tâm của {section}", "1.5h"),
        ("Ghi chú điểm chưa hiểu ở {section} để hỏi giảng viên", "30m"),
        ("Tự kiểm tra lại kiến thức {section}", "45m"),
    ]
    return [
        {
            "task_id": f"t{index}",
            "title": template.format(section=chunk["section"] or chunk["subject_code"]),
            "duration_estimate": duration,
            "source_label": chunk["source_label"],
        }
        for index, (chunk, (template, duration)) in enumerate(zip(chunks, templates, strict=False), start=1)
    ]


def _has_real_api_key(settings: Settings) -> bool:
    key = settings.openai_api_key or ""
    return bool(key) and not key.startswith("sk-your")
