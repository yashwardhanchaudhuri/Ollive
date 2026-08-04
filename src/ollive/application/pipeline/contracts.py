"""Typed state and configuration shared by runtime pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ollive.application.guardrails import TurnPolicy
from ollive.domain.models import AgentTurnResult, Citation, Message, UsageStats
from ollive.domain.security import SecurityReview


@dataclass(frozen=True)
class PipelineConfig:
    """Application-owned execution bounds for one runtime pipeline."""

    system_prompt: str
    max_tool_rounds: int = 10
    min_web_searches: int = 1
    max_web_searches: int = 3

    def __post_init__(self) -> None:
        """Reject invalid bounds before the pipeline can accept traffic."""
        if self.max_tool_rounds < 1:
            raise ValueError("max_tool_rounds must be at least 1")
        if not 1 <= self.min_web_searches <= self.max_web_searches <= 3:
            raise ValueError(
                "Web-search bounds must satisfy 1 <= minimum <= maximum <= 3"
            )


@dataclass
class TurnState:
    """Carry one turn through stages without hidden cross-stage mutation."""

    user_text: str
    history: list[Message]
    model: str
    backend: str
    usage: UsageStats
    security_trace: list[dict[str, Any]] = field(default_factory=list)
    policy: TurnPolicy | None = None
    evidence_query: str = ""
    max_answer_items: int = 3
    messages: list[Message] = field(default_factory=list)
    assistant_text: str = ""
    citations: list[Citation] = field(default_factory=list)
    invalid_citations: list[Citation] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    structured_grounded: bool = False
    structured_error: str | None = None
    citation_validation_failed: bool = False
    security_validation_failed: bool = False

    @classmethod
    def begin(
        cls,
        *,
        user_text: str,
        history: list[Message],
        model: str,
        backend: str,
    ) -> "TurnState":
        """Create an empty, identity-aware state for one user turn."""
        return cls(
            user_text=user_text,
            history=list(history),
            model=model,
            backend=backend,
            usage=UsageStats(model=model, backend=backend),
            evidence_query=user_text,
        )

    def add_usage(self, usage: UsageStats) -> None:
        """Accumulate ordinary stage usage into the turn."""
        self.usage = self.usage.add(usage)

    def record_security(self, review: SecurityReview) -> dict[str, Any]:
        """Accumulate classifier cost and append a trace-safe verdict event."""
        from ollive.application.security import SecurityBroker

        self.usage = self.usage.add(review.usage).model_copy(
            update={"model": self.model, "backend": self.backend}
        )
        event = SecurityBroker.trace_payload(review)
        self.security_trace.append(event)
        return event

    def require_policy(self) -> TurnPolicy:
        """Return the routed policy or fail on an invalid stage transition."""
        if self.policy is None:
            raise RuntimeError("RoutingStage must run before this pipeline stage")
        return self.policy

    def result(self, *, route: str | None = None) -> AgentTurnResult:
        """Build the stable public result from finalized pipeline state."""
        policy_route = route or self.require_policy().kind.value
        unique = list({citation.marker: citation for citation in self.citations}.values())
        return AgentTurnResult(
            assistant_message=self.assistant_text,
            citations=unique,
            invalid_citations=self.invalid_citations,
            citation_validation_failed=self.citation_validation_failed,
            security_validation_failed=self.security_validation_failed,
            security_trace=self.security_trace,
            tool_trace=self.tool_trace,
            usage=self.usage,
            backend=self.backend,
            model=self.model,
            policy_route=policy_route,
        )
