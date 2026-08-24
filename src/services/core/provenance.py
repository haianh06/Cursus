"""Provenance contract (Data Contract §3).

Every record that is rendered in the UI in a way that could be mistaken for a
fact must carry one of these ``source_type`` values so the UI can label it
correctly:

- ``official_document``  syllabus/CLO/session text — citation opens the source
- ``simulated``          Gate-2 demo fixture (deadline, demo progress)
- ``user_entered``       availability, defer reason
- ``system_derived``     completion %, risk score (formula + evidence shown)
- ``ai_suggested``       task decomposition, duration estimate

Nothing in this module talks to the DB; it only builds the dicts that get
stored in the existing JSON columns (``WeeklyPlan.goals``,
``WeeklyReflection.metrics``, ``RiskSignal.evidence`` ...). Keeping it
schema-free is deliberate: Gate 2 must not require a DB migration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

OFFICIAL_DOCUMENT: Final = "official_document"
SIMULATED: Final = "simulated"
USER_ENTERED: Final = "user_entered"
SYSTEM_DERIVED: Final = "system_derived"
AI_SUGGESTED: Final = "ai_suggested"

SOURCE_TYPES: Final = frozenset(
    {OFFICIAL_DOCUMENT, SIMULATED, USER_ENTERED, SYSTEM_DERIVED, AI_SUGGESTED}
)

# Human-facing labels. The blueprint (§4.3) requires AI estimates to read
# "Ước tính của Curi" and sourced facts to read "theo syllabus".
DISPLAY_LABEL_VI: Final = {
    OFFICIAL_DOCUMENT: "Theo syllabus",
    SIMULATED: "Dữ liệu demo",
    USER_ENTERED: "Do bạn cung cấp",
    SYSTEM_DERIVED: "Hệ thống tính",
    AI_SUGGESTED: "Ước tính của Curi",
}

DISPLAY_LABEL_EN: Final = {
    OFFICIAL_DOCUMENT: "From syllabus",
    SIMULATED: "Demo data",
    USER_ENTERED: "Provided by you",
    SYSTEM_DERIVED: "System calculated",
    AI_SUGGESTED: "Curi estimate",
}

SCHEMA_VERSION: Final = "1.0"
FIXTURE_VERSION: Final = "gate2_demo_v1"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def provenance(
    source_type: str,
    *,
    source_id: str,
    source_version: str = FIXTURE_VERSION,
    confidence: float = 1.0,
    created_at: str | None = None,
) -> dict:
    """Build a provenance record. Raises on an unknown ``source_type`` so a
    typo can never silently downgrade a simulated record into a 'fact'."""
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"Unknown provenance source_type: {source_type!r}")
    return {
        "source_type": source_type,
        "source_id": source_id,
        "source_version": source_version,
        "created_at": created_at or utc_now_iso(),
        "confidence": confidence,
        "label_vi": DISPLAY_LABEL_VI[source_type],
        "label_en": DISPLAY_LABEL_EN[source_type],
    }


def official(source_id: str, *, source_version: str = "2025-11-27") -> dict:
    return provenance(
        OFFICIAL_DOCUMENT, source_id=source_id, source_version=source_version
    )


def simulated(source_id: str = "gate2_demo_fixture") -> dict:
    return provenance(SIMULATED, source_id=source_id)


def ai_suggested(source_id: str = "curi_planner_v1") -> dict:
    return provenance(AI_SUGGESTED, source_id=source_id)


def user_entered(source_id: str = "student_input") -> dict:
    return provenance(USER_ENTERED, source_id=source_id)


def system_derived(source_id: str = "rules_v1") -> dict:
    return provenance(SYSTEM_DERIVED, source_id=source_id)
