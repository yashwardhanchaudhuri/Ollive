"""Citation validation and final Security LM alignment."""

from __future__ import annotations

from ollive.application.pipeline.contracts import TurnState
from ollive.application.security import SECURITY_REJECTION_MESSAGE, SecurityBroker
from ollive.domain.citations import (
    find_citation_like_tokens,
    parse_citations,
    validate_citations,
)
from ollive.ports.tracer import TracerPort

CITATION_REJECTION_MESSAGE = (
    "I couldn't verify the citations in the generated answer, so I withheld it. "
    "Please try again."
)


class OutputStage:
    """Validate grounded output and enforce the last security boundary."""

    def __init__(
        self, *, security: SecurityBroker, tracer: TracerPort
    ) -> None:
        """Bind final validation and observability dependencies."""
        self._security = security
        self._tracer = tracer

    def run(self, state: TurnState, *, validate_grounding: bool = True) -> None:
        """Validate citations when needed, then require final Security LM approval."""
        if validate_grounding:
            self._validate_citations(state)
        canary_review = self._security.review_canary(state.assistant_text)
        if canary_review is not None:
            event = state.record_security(canary_review)
            self._tracer.log_span(name="security:canary", output=event)
            state.assistant_text = SECURITY_REJECTION_MESSAGE
            state.citations = []
            state.security_validation_failed = True
            return
        review = self._security.review_output(
            user_text=state.user_text,
            route=state.require_policy().kind.value,
            assistant_text=state.assistant_text,
            citations=state.citations,
            tool_trace=state.tool_trace,
        )
        event = state.record_security(review)
        self._tracer.log_span(name="security:output", output=event)
        if not review.allowed:
            state.assistant_text = SECURITY_REJECTION_MESSAGE
            state.citations = []
            state.security_validation_failed = True

    def _validate_citations(self, state: TurnState) -> None:
        """Reject stale, fabricated, malformed, or missing citation markers."""
        claimed = parse_citations(state.assistant_text)
        valid, invalid = validate_citations(claimed, state.citations)
        allowed_markers = {citation.marker for citation in state.citations}
        unexpected = [
            token
            for token in find_citation_like_tokens(state.assistant_text)
            if token not in allowed_markers
        ]
        missing = (
            bool(state.citations)
            and not claimed
            and not state.structured_grounded
        )
        state.invalid_citations = invalid
        state.citation_validation_failed = (
            bool(state.structured_error)
            or bool(invalid)
            or bool(unexpected)
            or missing
        )
        if state.citation_validation_failed:
            self._tracer.log_span(
                name="citation_validation_failed",
                input={"claimed": [citation.marker for citation in claimed]},
                output={
                    "invalid": [citation.marker for citation in invalid],
                    "unexpected_tokens": unexpected,
                    "structured_error": state.structured_error,
                },
            )
            state.assistant_text = CITATION_REJECTION_MESSAGE
            state.citations = []
        else:
            state.citations = valid
