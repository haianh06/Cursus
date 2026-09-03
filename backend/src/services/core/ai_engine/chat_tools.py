"""Tool-calling ("function calling") for Cursus Chat's live-data lookups.

Pure LLM-plumbing layer, same as chat_stream.py/structured.py in this same
package -- no DB/model imports here. The actual tool EXECUTION (touching the
database, scoped to the asking student) lives in
src/services/core/chat_tool_service.py; this module only defines the tool
schemas the model is offered and decides WHICH ones (if any) to call.

Runs as a separate, non-streamed, light-model call BEFORE the main
streaming answer (see cursus_chat.py) rather than folding tool-calling into
that streaming call itself -- accumulating tool-call deltas across stream
chunks then following up with a second call is a well-known but fiddly
pattern, and this app's single existing streaming path is worth keeping
untouched. The cost is one extra light-model call per turn (same trade-off
`generate_followup_suggestions` in chat_stream.py already makes).

`OPENAI_BASE_URL` here may point at a third-party OpenAI-compatible gateway
(not confirmed to support tool calling -- see ai_service_client.py's own
docstring about it possibly only implementing the older Chat Completions
surface). `decide_tool_calls()` is therefore FAIL-OPEN by design: any
error, or a response with no tool_calls at all (whether because the model
genuinely didn't need one, or because the gateway silently ignored
`tools=`), just returns an empty list -- Cursus Chat falls back to
today's RAG-only behavior for that turn, never an error shown to the
student.
"""
from __future__ import annotations

import json
import logging
import time

from src.config import Settings
from src.services.core.ai_engine.client import async_openai_client, model_for_route
from src.services.core.ai_engine.routing import ModelRoute
from src.services.core.ai_usage_recorder import record_llm_call
from src.services.core.llm import has_configured_llm

logger = logging.getLogger(__name__)

_MIN_WEEK_OFFSET = -4
_MAX_WEEK_OFFSET = 4

_WEEK_OFFSET_PARAM = {
    "type": "integer",
    "description": (
        "Which week relative to the current one, e.g. 0 = this week, "
        "1 = next week, -1 = last week. Defaults to 0 (this week) when "
        "omitted."
    ),
    "minimum": _MIN_WEEK_OFFSET,
    "maximum": _MAX_WEEK_OFFSET,
}

CHAT_TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_weekly_timetable",
            "description": (
                "Get the student's real class/exam/self-study schedule for "
                "one week -- use this for any question about what sessions, "
                "classes, or exams the student has, and when."
            ),
            "parameters": {
                "type": "object",
                "properties": {"weeks_from_now": _WEEK_OFFSET_PARAM},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_plan_tasks",
            "description": (
                "Get the student's real weekly study plan and its tasks "
                "(title, status, priority) -- use this for any question "
                "about what the student's plan or to-do tasks are for a "
                "week, or what is/isn't done yet."
            ),
            "parameters": {
                "type": "object",
                "properties": {"weeks_from_now": _WEEK_OFFSET_PARAM},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_quiz_results",
            "description": (
                "Get the student's real quizzes with due dates, whether "
                "each is done/pending, and the student's own grade if "
                "graded -- use this for any question about quiz status or "
                "scores."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_risk_signals",
            "description": (
                "Get the student's own real academic-risk signals/warnings "
                "(if any) -- use this for a question about whether the "
                "student is at risk or has any warnings."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_self_study_stats",
            "description": (
                "Get the student's real self-study time tracked per day for "
                "one week -- use this for any question about how much the "
                "student has studied on their own."
            ),
            "parameters": {
                "type": "object",
                "properties": {"weeks_from_now": _WEEK_OFFSET_PARAM},
                "required": [],
            },
        },
    },
]

_TOOL_DECISION_INSTRUCTIONS = (
    "You decide whether answering the student's message needs one of the "
    "supplied tools (their real timetable, plan/tasks, quiz results, risk "
    "signals, or self-study stats). Call a tool ONLY when the message is "
    "genuinely asking about that student's own live data. If the message "
    "is about course content, general chit-chat, or anything a tool "
    "wouldn't help with, call no tool at all."
)


def _clamp_week_offset(value: object) -> int:
    try:
        offset = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
    return max(_MIN_WEEK_OFFSET, min(_MAX_WEEK_OFFSET, offset))


def _parse_tool_call(raw_call) -> dict | None:
    name = getattr(getattr(raw_call, "function", None), "name", None)
    if not name:
        return None
    raw_arguments = getattr(raw_call.function, "arguments", None) or "{}"
    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError:
        arguments = {}
    if not isinstance(arguments, dict):
        arguments = {}
    if "weeks_from_now" in arguments:
        arguments["weeks_from_now"] = _clamp_week_offset(arguments["weeks_from_now"])
    return {"name": name, "arguments": arguments}


async def decide_tool_calls(*, settings: Settings, message: str) -> list[dict]:
    """Returns `[{"name": ..., "arguments": {...}}, ...]`, or `[]` when no
    tool is needed, the LLM isn't configured, or anything goes wrong.
    Never raises -- see module docstring for why this must fail open."""
    if not has_configured_llm():
        return []

    route = ModelRoute("OPENAI_LIGHT_MODEL", "chat-tool-decision")
    model = model_for_route(route, settings)
    client = async_openai_client(settings)
    started = time.perf_counter()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _TOOL_DECISION_INSTRUCTIONS},
                {"role": "user", "content": message},
            ],
            tools=CHAT_TOOL_SPECS,
            tool_choice="auto",
            max_tokens=300,
        )
        record_llm_call(
            feature="chat_tool_decision",
            model=model,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            latency_ms=int((time.perf_counter() - started) * 1000),
            success=True,
        )
        raw_calls = response.choices[0].message.tool_calls or []
        parsed = [_parse_tool_call(call) for call in raw_calls]
        return [call for call in parsed if call is not None]
    except Exception:
        # Fail open: a gateway that doesn't support `tools=` at all, a
        # timeout, or any other failure here must never take down the main
        # chat turn -- it just proceeds as if no tool was needed, exactly
        # like today's tool-less behavior.
        record_llm_call(
            feature="chat_tool_decision",
            model=model,
            input_tokens=0,
            output_tokens=0,
            latency_ms=int((time.perf_counter() - started) * 1000),
            success=False,
        )
        logger.exception("chat_tool_decision_failed")
        return []
