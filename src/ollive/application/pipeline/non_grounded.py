"""Conversation, clarification, and refusal response stage."""

from __future__ import annotations

from ollive.application.pipeline.contracts import TurnState
from ollive.ports.llm import LLMPort
from ollive.ports.tracer import TracerPort


class NonGroundedStage:
    """Generate a tool-free response for explicitly non-grounded routes."""

    def __init__(self, *, llm: LLMPort, tracer: TracerPort) -> None:
        """Bind the answer model and trace sink without any evidence tools."""
        self._llm = llm
        self._tracer = tracer

    def run(self, state: TurnState) -> None:
        """Run one tool-free generation and reject any attempted tool call."""
        response = self._llm.chat(
            state.messages, tools=None, tool_choice=None
        )
        state.add_usage(response.usage)
        self._tracer.log_generation(
            name="llm_chat",
            model=self._llm.model_name,
            input_messages=[
                {"role": message.role.value, "content": message.content}
                for message in state.messages
            ],
            output=response.content
            or str([call.name for call in response.tool_calls]),
            usage={
                "input": response.usage.prompt_tokens,
                "output": response.usage.completion_tokens,
                "total": response.usage.total_tokens,
                "unit": "TOKENS",
            },
            metadata={"latency_ms": response.usage.latency_ms},
        )
        if response.tool_calls:
            state.structured_error = (
                "Non-grounded route attempted an unavailable tool call"
            )
            return
        state.assistant_text = response.content
