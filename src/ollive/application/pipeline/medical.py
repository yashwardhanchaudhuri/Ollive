"""Medical-boundary response stage."""

from __future__ import annotations

from ollive.application.guardrails import render_medical_boundary
from ollive.application.pipeline.contracts import TurnState
from ollive.ports.llm import LLMPort
from ollive.ports.tracer import TracerPort


class MedicalStage:
    """Render the constrained medical boundary without evidence tools."""

    def __init__(self, *, llm: LLMPort, tracer: TracerPort) -> None:
        """Bind the urgency classifier and trace sink."""
        self._llm = llm
        self._tracer = tracer

    def run(self, state: TurnState) -> None:
        """Produce the application-owned medical response for one routed turn."""
        text, usage = render_medical_boundary(self._llm, state.user_text)
        state.assistant_text = text
        state.add_usage(usage)
        self._tracer.log_span(
            name="medical_boundary",
            input={"route": state.require_policy().kind.value},
            output=text,
        )
