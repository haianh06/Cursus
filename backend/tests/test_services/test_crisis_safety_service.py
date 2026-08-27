"""Adversarial test suite for crisis_safety_service — a rule-based, NOT
clinically validated, first layer of defense (see the module's own
docstring). This suite exists to catch pattern-list regressions and
document known false-positive/false-negative trade-offs explicitly, not to
certify the detector as sufficient on its own."""

from __future__ import annotations

import pytest

from src.services.core.crisis_safety_service import evaluate

# Real crisis phrasing is intentionally varied: accented, accent-stripped,
# Vietnamese, English, direct statements, and indirect/burden framing.
_POSITIVE_CASES = [
    "Em muốn tự tử",
    "em muon tu tu di",  # accent-stripped
    "Tôi không muốn sống nữa",
    "toi khong muon song nua",
    "Mình chán sống lắm rồi",
    "em muốn biến mất mãi mãi",
    "không còn lý do gì để sống nữa",
    "thà chết còn hơn phải sống thế này",
    "em cắt tay mấy lần rồi",
    "mình là gánh nặng cho gia đình",
    "mọi người sẽ tốt hơn nếu không có em",
    "I want to kill myself",
    "i cant take it anymore, i want to end my life",
    "everyone would be better off dead without me",
    "this is my goodbye",
    "nobody would care if i was gone",
]


@pytest.mark.parametrize("message", _POSITIVE_CASES)
def test_crisis_phrases_trigger(message):
    decision = evaluate(message)
    assert decision.triggered is True
    assert decision.answer is not None
    assert "1800-599-920" in decision.answer


_NEGATIVE_CASES = [
    "Điều kiện qua môn SSA101 là gì?",
    "Em bị trễ deadline bài tập rồi, giờ phải làm sao?",
    "Cách tự học hiệu quả hơn là gì?",
    "I want to kill this bug in my code",
    "Làm sao để tự tin hơn khi thuyết trình?",
    "Bài tập này khó quá, em không làm được",
    "em cảm thấy áp lực với deadline tuần này",  # stress, not crisis — must not over-trigger
    "Kế hoạch tuần của em có ổn không?",
]


@pytest.mark.parametrize("message", _NEGATIVE_CASES)
def test_normal_academic_messages_do_not_trigger(message):
    assert evaluate(message).triggered is False


def test_empty_or_whitespace_message_does_not_trigger():
    assert evaluate("").triggered is False
    assert evaluate("   ").triggered is False
    assert evaluate(None).triggered is False


def test_known_false_positive_self_harm_as_academic_topic():
    """Documented, accepted trade-off: 'self-harm' as a bare academic term
    (e.g. a public-health course discussing self-harm reduction policy)
    trips the EN self-harm pattern. This is intentional given the stated
    "err toward triggering" policy (a false positive only shows one
    supportive message, it never blocks the conversation) — recorded here
    so a future change to this behavior is a deliberate decision, not an
    accidental regression discovered in production."""
    decision = evaluate("What is a self-harm reduction policy in public health?")
    assert decision.triggered is True


def test_answer_never_blocks_further_conversation():
    """The crisis answer must not read as a dead end -- always offers to
    keep talking, mirroring the academic guardrail's "never a dead end"
    principle (guardrail_service.py's own design note)."""
    decision = evaluate("em muốn tự tử")
    assert "quay lại" in decision.answer or "tiếp" in decision.answer
