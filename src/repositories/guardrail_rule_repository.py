from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.db.models import GuardrailPolicyVersion, GuardrailRule
from src.services.core.guardrail_rules import RULE_GROUPS

_KNOWN_CODES = frozenset(group.code for group in RULE_GROUPS)
_ORDER = {group.code: index for index, group in enumerate(RULE_GROUPS)}

# Anti prompt-injection / data-leak protection -- can't be disabled through
# the Admin UI even by an ADMIN, so a compromised or careless Admin account
# can't turn off the system's own guardrails.
_CORE_LOCKED_CODES = frozenset({"PROMPT_INJECTION"})


class CoreGuardrailLockedError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Guardrail rule {code} is core-locked and cannot be disabled")


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class GuardrailRuleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def ensure_seeded(self) -> None:
        existing = {code for (code,) in self._db.query(GuardrailRule.code).all()}
        for group in RULE_GROUPS:
            if group.code not in existing:
                self._db.add(
                    GuardrailRule(
                        code=group.code,
                        enabled=True,
                        core_locked=group.code in _CORE_LOCKED_CODES,
                        updated_at=_now(),
                    )
                )
        self._db.flush()

    def list_rules(self) -> list[GuardrailRule]:
        self.ensure_seeded()
        rules = self._db.query(GuardrailRule).all()
        return sorted(
            (rule for rule in rules if rule.code in _KNOWN_CODES),
            key=lambda rule: _ORDER[rule.code],
        )

    def enabled_codes(self) -> frozenset[str]:
        return frozenset(rule.code for rule in self.list_rules() if rule.enabled)

    def _publish_version(
        self, rules: list[GuardrailRule], *, change_reason: str | None, actor_user_id: str | None
    ) -> GuardrailPolicyVersion:
        previous = (
            self._db.query(GuardrailPolicyVersion)
            .filter_by(is_active=True)
            .order_by(GuardrailPolicyVersion.created_at.desc())
            .first()
        )
        if previous is not None:
            previous.is_active = False
        version = GuardrailPolicyVersion(
            version=f"gpv_{uuid.uuid4().hex[:12]}",
            rules_snapshot={rule.code: rule.enabled for rule in rules},
            source_version=previous.version if previous else None,
            change_reason=change_reason,
            is_active=True,
            created_by=actor_user_id,
            created_at=_now(),
        )
        self._db.add(version)
        self._db.flush()
        for rule in rules:
            rule.current_version = version.version
        return version

    def set_enabled(
        self,
        code: str,
        *,
        enabled: bool,
        actor_user_id: str | None,
        reason: str | None = None,
    ) -> GuardrailRule:
        if code not in _KNOWN_CODES:
            raise LookupError(f"Unknown guardrail rule: {code}")
        self.ensure_seeded()
        rule = self._db.query(GuardrailRule).filter_by(code=code).one()
        if rule.core_locked and not enabled:
            raise CoreGuardrailLockedError(code)
        rule.enabled = enabled
        rule.change_reason = reason
        rule.updated_at = _now()
        rule.updated_by = actor_user_id
        self._db.flush()
        self._publish_version(self.list_rules(), change_reason=reason, actor_user_id=actor_user_id)
        return rule

    def restore_defaults(self, actor_user_id: str | None) -> list[GuardrailRule]:
        rules = self.list_rules()
        updated_at = _now()
        for rule in rules:
            rule.enabled = True
            rule.change_reason = "Restore defaults"
            rule.updated_at = updated_at
            rule.updated_by = actor_user_id
        self._db.flush()
        self._publish_version(rules, change_reason="Restore defaults", actor_user_id=actor_user_id)
        return rules

    def list_policy_history(self) -> list[GuardrailPolicyVersion]:
        return (
            self._db.query(GuardrailPolicyVersion)
            .order_by(GuardrailPolicyVersion.created_at.desc())
            .all()
        )
