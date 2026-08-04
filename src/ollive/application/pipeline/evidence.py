"""Segregated tool execution and Security LM evidence approval."""

from __future__ import annotations

from dataclasses import dataclass, field

from ollive.application.pipeline.contracts import PipelineConfig, TurnState
from ollive.application.security import SecurityBroker
from ollive.application.tools import ToolRouter
from ollive.domain.models import Citation, Message, Role, ToolCallRequest
from ollive.ports.tracer import TracerPort


@dataclass
class EvidenceLedger:
    """Track application-owned evidence call counts for one turn."""

    counts: dict[str, int] = field(
        default_factory=lambda: {"lookup_kb": 0, "search_web": 0}
    )

    @property
    def lookup_completed(self) -> bool:
        """Return whether the required local lookup has executed."""
        return self.counts["lookup_kb"] > 0

    @property
    def web_searches(self) -> int:
        """Return the number of web calls executed in this turn."""
        return self.counts["search_web"]


class EvidenceStage:
    """Execute tools, gate raw results, and expose only rebuilt safe payloads."""

    def __init__(
        self,
        *,
        tools: ToolRouter,
        security: SecurityBroker,
        tracer: TracerPort,
        config: PipelineConfig,
    ) -> None:
        """Bind adapters behind the application-owned evidence boundary."""
        self._tools = tools
        self._security = security
        self._tracer = tracer
        self._config = config

    def execute(
        self,
        state: TurnState,
        calls: list[ToolCallRequest],
        ledger: EvidenceLedger,
    ) -> str | None:
        """Execute typed calls and append only Security-LM-approved results."""
        for call in calls:
            if call.name in ledger.counts:
                ledger.counts[call.name] += 1
            if ledger.web_searches > self._config.max_web_searches:
                return "Web-search call limit exceeded"

            raw = self._tools.execute(
                call, user_query=state.evidence_query
            )
            approved, review = self._security.filter_evidence(
                user_text=state.user_text,
                tool_name=call.name,
                citations=raw.citations,
                raw_metadata=raw.content,
            )
            event = state.record_security(review)
            self._tracer.log_span(name="security:evidence", output=event)

            if call.name == "search_web":
                approved = self._review_combined(state, approved)

            safe = self._security.safe_tool_result(raw, approved)
            state.citations.extend(approved)
            trace_arguments = dict(call.arguments)
            if call.name == "lookup_kb":
                trace_arguments["query"] = state.evidence_query
            state.tool_trace.append(
                {
                    "name": call.name,
                    "arguments": trace_arguments,
                    "result_preview": safe.content[:800],
                    "security_decision": review.decision,
                }
            )
            self._tracer.log_span(
                name=f"tool:{call.name}",
                input=call.arguments,
                output=safe.content[:2000],
            )
            state.messages.append(
                Message(
                    role=Role.TOOL,
                    content=safe.content,
                    tool_call_id=call.id,
                    name=call.name,
                )
            )
        return None

    def _review_combined(
        self, state: TurnState, newly_approved: list[Citation]
    ) -> list[Citation]:
        """Allow new evidence only when the aggregate evidence set is safe."""
        candidates = [*state.citations, *newly_approved]
        review = self._security.review_combined_evidence(
            state.user_text, candidates
        )
        event = state.record_security(review)
        self._tracer.log_span(
            name="security:combined_evidence", output=event
        )
        approved_ids = review.approved_item_ids
        existing_ids = {citation.marker for citation in state.citations}
        if not review.allowed or not existing_ids.issubset(approved_ids):
            return []
        return [
            citation
            for citation in newly_approved
            if citation.marker in approved_ids
        ]
