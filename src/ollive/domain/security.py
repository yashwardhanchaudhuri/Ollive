"""Infrastructure-free security review contracts."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ollive.domain.models import UsageStats


AuthorityContentMode = Literal[
    "direct_request",
    "quotation_or_transformation",
    "self_labeled_data",
    "mixed",
    "none",
]
PersonaMode = Literal["none", "ordinary", "authority_seeking"]

AuthorityTarget = Literal[
    "assistant_policy",
    "hidden_instructions",
    "tool_authority",
    "persistent_memory",
    "response_content",
    "subject_matter",
    "none",
    "unclear",
]
AuthorityEffect = Literal[
    "override",
    "disclose",
    "impersonate",
    "persist",
    "unauthorized_action",
    "transform",
    "discuss",
    "normal_request",
    "none",
    "unclear",
]

SecurityDecisionSource = Literal[
    "model",
    "authority_policy",
    "application_policy",
    "fail_closed",
    "canary",
]


class SecurityStage(str, Enum):
    """Identify the trust boundary being reviewed."""

    INPUT = "input"
    CONTEXT = "context"
    EVIDENCE = "evidence"
    COMBINED_EVIDENCE = "combined_evidence"
    OUTPUT = "output"


class SecurityItemVerdict(BaseModel):
    """Return the decision for one identified evidence object."""

    model_config = ConfigDict(extra="forbid", strict=True)

    item_id: str = Field(min_length=1, max_length=240)
    decision: Literal["allow", "exclude"]
    risk_flags: list[str] = Field(default_factory=list, max_length=20)


class SecurityCheckResult(BaseModel):
    """Record one executed single-purpose classifier check."""

    model_config = ConfigDict(extra="forbid", strict=True)

    check: str = Field(min_length=1, max_length=80)
    decision: Literal["allow", "block"]
    reason_code: str = Field(min_length=1, max_length=120)
    risk_flags: list[str] = Field(default_factory=list, max_length=20)
    trust_score: float = Field(ge=0.0, le=1.0)
    items: list[SecurityItemVerdict] = Field(default_factory=list, max_length=50)


class AuthorityAssessment(BaseModel):
    """Describe requested authority effects without making the policy decision."""

    model_config = ConfigDict(extra="forbid", strict=True)

    content_mode: AuthorityContentMode
    persona_mode: PersonaMode
    target: AuthorityTarget
    effect: AuthorityEffect
    execution_requested: bool
    evidence_excerpt: str = Field(default="", max_length=280)


class SecurityReview(BaseModel):
    """Constrained Security LM decision consumed by application code."""

    model_config = ConfigDict(extra="forbid", strict=True)

    stage: SecurityStage
    decision: Literal["allow", "block"]
    reason_code: str = Field(min_length=1, max_length=120)
    risk_flags: list[str] = Field(default_factory=list, max_length=20)
    items: list[SecurityItemVerdict] = Field(default_factory=list, max_length=50)
    checks: list[SecurityCheckResult] = Field(default_factory=list, max_length=12)
    authority: AuthorityAssessment | None = None
    decision_source: SecurityDecisionSource = "model"
    trust_score: float | None = Field(default=None, ge=0.0, le=1.0)
    usage: UsageStats = Field(default_factory=UsageStats)

    @property
    def allowed(self) -> bool:
        """Return whether the application may advance past this gate."""
        return self.decision == "allow"

    @property
    def approved_item_ids(self) -> set[str]:
        """Return evidence identifiers explicitly approved by the gate."""
        if not self.allowed:
            return set()
        return {
            item.item_id for item in self.items if item.decision == "allow"
        }
