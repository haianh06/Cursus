"""Moved from the standalone ai-service (app/core/routing.py) when that
service was folded into backend as an in-process module -- picks the model
env var to read, not the model name itself, so a route can survive a model
rename by only touching config."""
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
