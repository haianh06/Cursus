from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ModelRoute:
    model_env: str
    reason: str

def select_model(*, intent: str, source_count: int, message: str) -> ModelRoute:
    complex_intents = {"course_complex", "plan_action", "reflection", "practice"}
    if intent in complex_intents or source_count > 2 or len(message) > 700:
        return ModelRoute("OPENAI_STRONG_MODEL", "multi-step or multi-source request")
    return ModelRoute("OPENAI_LIGHT_MODEL", "simple grounded request")
