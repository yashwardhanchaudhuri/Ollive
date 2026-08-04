"""Deterministic enforcement for persona-mediated authority escalation."""

from __future__ import annotations

from ollive.domain.security import AuthorityAssessment


_PRIVILEGED_TARGETS = frozenset(
    {
        "assistant_policy",
        "hidden_instructions",
        "tool_authority",
        "persistent_memory",
    }
)
_PROHIBITED_EFFECTS = frozenset(
    {
        "override",
        "disclose",
        "impersonate",
        "persist",
        "unauthorized_action",
    }
)


class PersonaGuard:
    """Block a persona only when it requests prohibited authority in execution."""

    def block_reason(self, assessment: AuthorityAssessment) -> str | None:
        """Return the dedicated jailbreak reason for a persona authority attack."""
        if (
            assessment.persona_mode == "authority_seeking"
            and assessment.execution_requested
            and assessment.target in _PRIVILEGED_TARGETS
            and assessment.effect in _PROHIBITED_EFFECTS
        ):
            return "jailbreak"
        return None
