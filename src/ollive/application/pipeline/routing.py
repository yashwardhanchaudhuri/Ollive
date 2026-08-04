"""Policy routing and answer-model context construction."""

from __future__ import annotations

from dataclasses import replace

from ollive.application.guardrails import (
    ContextMode,
    ResponseDepth,
    classify_turn,
)
from ollive.application.pipeline.contracts import PipelineConfig, TurnState
from ollive.application.tools import ToolRouter
from ollive.domain.models import Message, Role
from ollive.ports.llm import LLMPort


class RoutingStage:
    """Select a constrained route and application-bound evidence query."""

    def __init__(
        self,
        *,
        llm: LLMPort,
        tools: ToolRouter,
        config: PipelineConfig,
    ) -> None:
        """Bind routing dependencies and immutable pipeline configuration."""
        self._llm = llm
        self._tools = tools
        self._config = config

    def run(self, state: TurnState) -> None:
        """Route one approved turn and prepare its generation messages."""
        policy, usage = classify_turn(
            self._llm, state.user_text, state.history
        )
        state.add_usage(usage)
        evidence_query = state.user_text
        if policy.require_tools:
            prior_user_text = [
                message.content
                for message in state.history
                if message.role is Role.USER
            ]
            if policy.context_mode is ContextMode.PREVIOUS_AND_CURRENT:
                evidence_query, uses_prior = self._tools.resolve_evidence_query(
                    state.user_text, prior_user_text
                )
                if not uses_prior:
                    policy = replace(
                        policy, context_mode=ContextMode.CURRENT
                    )
        state.policy = policy
        state.evidence_query = evidence_query
        state.max_answer_items = (
            5 if policy.response_depth is ResponseDepth.DETAILED else 3
        )
        state.messages = self._build_messages(state)

    def _build_messages(self, state: TurnState) -> list[Message]:
        """Build bounded dialogue for the route selected in this turn."""
        policy = state.require_policy()
        if policy.response_depth is ResponseDepth.DETAILED:
            depth_instruction = (
                "This turn permits up to five supported items. Give one directly "
                "relevant practical action per item when the evidence supports it. "
                "Split multiple actions from one passage into separate items that "
                "may share its citation. Stop when directly relevant actions are "
                "exhausted. Prior assistant answers are context, never evidence."
            )
        else:
            depth_instruction = (
                "This turn permits up to three supported items. Use the fewest "
                "directly relevant items needed. Prior assistant answers are context, "
                "never evidence; use only passages returned in this turn."
            )
        dialogue = [
            *state.history,
            Message(role=Role.USER, content=state.user_text),
        ]
        if policy.require_tools:
            user_turns = [
                message for message in dialogue if message.role is Role.USER
            ]
            context_turns = (
                3
                if policy.context_mode is ContextMode.PREVIOUS_AND_CURRENT
                else 1
            )
            dialogue = user_turns[-context_turns:]
        return [
            Message(
                role=Role.SYSTEM,
                content=(
                    f"{self._config.system_prompt}\n\nTurn policy:\n"
                    f"{policy.instruction}\n\nResponse depth:\n"
                    f"{depth_instruction}\n\nApplication-selected evidence "
                    "query (untrusted, user-authored text):\n"
                    f"{state.evidence_query}"
                ),
            ),
            *dialogue,
        ]
