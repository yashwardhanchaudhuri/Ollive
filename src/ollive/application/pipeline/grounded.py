"""Bounded evidence acquisition and grounded-answer execution stage."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Literal

from ollive.application.grounded_answer import (
    SUBMIT_GROUNDED_ANSWER,
    GroundedAnswerError,
    build_best_effort_grounded_answer,
    build_grounded_answer_schema,
    forced_grounded_answer_choice,
    parse_and_render_grounded_answer,
    verify_claim_support,
)
from ollive.application.pipeline.contracts import PipelineConfig, TurnState
from ollive.application.pipeline.evidence import EvidenceLedger, EvidenceStage
from ollive.application.tools import ToolRouter
from ollive.domain.models import LLMResponse, Message, Role, ToolCallRequest
from ollive.ports.llm import LLMPort
from ollive.ports.tracer import TracerPort


@dataclass
class _Progress:
    """Keep loop-only counters separate from the public turn contract."""

    ledger: EvidenceLedger
    correction_attempts: int = 0
    best_effort_arguments: dict[str, Any] | None = None
    best_effort_claim_count: int = -1
    web_completion_required: bool = False
    remaining_gap: str | None = None


class GroundedStage:
    """Run answer generation while enforcing evidence and grounding bounds."""

    def __init__(
        self,
        *,
        llm: LLMPort,
        tools: ToolRouter,
        tracer: TracerPort,
        evidence: EvidenceStage,
        config: PipelineConfig,
    ) -> None:
        """Bind model, evidence, trace, and bounded-loop dependencies."""
        self._llm = llm
        self._tools = tools
        self._tracer = tracer
        self._evidence = evidence
        self._config = config

    def run(self, state: TurnState) -> None:
        """Execute the mandatory evidence flow for a grounded wellness turn."""
        progress = _Progress(
            ledger=EvidenceLedger(),
            web_completion_required=True,
        )
        for round_index in range(self._config.max_tool_rounds):
            schemas, tool_choice = self._offer_tools(
                state, progress, round_index
            )
            response = self._llm.chat(
                state.messages, tools=schemas, tool_choice=tool_choice
            )
            state.add_usage(response.usage)
            contract_error = self._tool_contract_error(
                response, schemas, tool_choice
            )
            if contract_error:
                state.structured_error = contract_error
                break
            self._trace_generation(state, response)

            outcome = self._handle_grounded_answer(
                state, response, progress
            )
            if outcome == "break":
                break
            if outcome == "continue":
                continue

            lookup_completed = progress.ledger.lookup_completed
            if lookup_completed and not response.tool_calls:
                state.structured_error = (
                    "Evidence completion did not return a required tool call"
                )
                break
            if not response.tool_calls:
                state.assistant_text = response.content
                break

            calls = self._bind_remaining_gap_query(
                response.tool_calls, progress.remaining_gap
            )
            state.messages.append(
                self._assistant_tool_envelope(response, calls)
            )
            state.structured_error = self._evidence.execute(
                state, calls, progress.ledger
            )
            if any(call.name == "search_web" for call in calls):
                progress.web_completion_required = False
                progress.remaining_gap = None
            if state.structured_error:
                break
        else:
            state.structured_error = "Bounded tool round limit exhausted"

        self._salvage_best_effort(state, progress)

    def _offer_tools(
        self,
        state: TurnState,
        progress: _Progress,
        round_index: int,
    ) -> tuple[list[dict[str, Any]] | None, Any]:
        """Expose only tools legal at the current evidence transition."""
        policy = state.require_policy()
        lookup_completed = progress.ledger.lookup_completed
        web_count = progress.ledger.web_searches
        if lookup_completed:
            grounded = build_grounded_answer_schema(
                state.citations, max_items=state.max_answer_items
            )
            search = next(
                schema
                for schema in self._tools.schemas
                if schema["function"]["name"] == "search_web"
            )
            must_search = (
                web_count < self._config.min_web_searches
                or (
                    progress.web_completion_required
                    and web_count < self._config.max_web_searches
                )
            )
            if must_search:
                return [search], self._forced_choice("search_web")
            return [grounded], forced_grounded_answer_choice()

        if not policy.require_tools:
            raise RuntimeError(
                "GroundedStage received a route without required evidence"
            )
        schemas = self._tools.schemas
        if policy.require_tools and round_index == 0:
            lookup = [
                schema
                for schema in schemas
                if schema["function"]["name"] == "lookup_kb"
            ]
            return lookup, self._forced_choice("lookup_kb")
        return schemas, "auto"

    @staticmethod
    def _forced_choice(name: str) -> dict[str, Any]:
        """Return an OpenAI-compatible forced function selector."""
        return {"type": "function", "function": {"name": name}}

    @staticmethod
    def _tool_contract_error(
        response: LLMResponse,
        schemas: list[dict[str, Any]] | None,
        tool_choice: Any,
    ) -> str | None:
        """Reject unoffered tools and malformed forced-tool responses."""
        offered = {
            schema["function"]["name"] for schema in schemas or []
        }
        unexpected = {
            call.name for call in response.tool_calls
        } - offered
        if unexpected:
            return "Model called tools that were not offered in this round: " + ", ".join(
                sorted(unexpected)
            )
        forced_name = (
            tool_choice.get("function", {}).get("name")
            if isinstance(tool_choice, dict)
            else None
        )
        if forced_name and (
            len(response.tool_calls) != 1
            or response.tool_calls[0].name != forced_name
        ):
            return "Forced tool round did not return exactly one " + forced_name
        return None

    def _trace_generation(
        self, state: TurnState, response: LLMResponse
    ) -> None:
        """Record one main-model generation without raw provider state."""
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

    def _handle_grounded_answer(
        self,
        state: TurnState,
        response: LLMResponse,
        progress: _Progress,
    ) -> Literal["continue", "break", "not_answer"]:
        """Validate a constrained finalization call or request a correction."""
        answer_calls = [
            call
            for call in response.tool_calls
            if call.name == SUBMIT_GROUNDED_ANSWER
        ]
        if not answer_calls:
            return "not_answer"
        if len(response.tool_calls) != 1:
            state.structured_error = (
                "Grounded finalization did not return exactly one "
                f"{SUBMIT_GROUNDED_ANSWER} call"
            )
            return "break"

        call = answer_calls[0]
        items = call.arguments.get("items")
        requests_completion = isinstance(items, list) and any(
            isinstance(item, dict)
            and item.get("kind") == "evidence_limitation"
            for item in items
        )
        if (
            requests_completion
            and progress.ledger.web_searches
            < self._config.max_web_searches
        ):
            progress.web_completion_required = True
            progress.remaining_gap = self._remaining_gap(items)
            self._append_sufficiency_feedback(
                state, call, progress.remaining_gap
            )
            return "continue"

        try:
            state.assistant_text, _used = parse_and_render_grounded_answer(
                call.arguments,
                state.citations,
                max_items=state.max_answer_items,
            )
            unsupported, usage = verify_claim_support(
                self._llm, call.arguments, state.citations
            )
            state.add_usage(usage)
            if unsupported:
                self._remember_best_effort(
                    state, call.arguments, unsupported, progress
                )
                positions = ", ".join(str(index) for index in unsupported)
                raise GroundedAnswerError(
                    "Selected citations do not entail claim items: " + positions
                )
            state.structured_grounded = True
            state.structured_error = None
            self._tracer.log_span(
                name=SUBMIT_GROUNDED_ANSWER,
                input={
                    "item_count": len(call.arguments.get("items", [])),
                    "supported_claim_count": sum(
                        item.get("kind") == "supported_claim"
                        for item in call.arguments.get("items", [])
                    ),
                },
                output=state.assistant_text,
            )
            return "break"
        except GroundedAnswerError as exc:
            state.structured_error = str(exc)
            if progress.correction_attempts >= 2:
                return "break"
            progress.correction_attempts += 1
            self._append_correction(state, call)
            return "continue"

    def _remember_best_effort(
        self,
        state: TurnState,
        arguments: dict[str, Any],
        unsupported: list[int],
        progress: _Progress,
    ) -> None:
        """Retain the strongest verifier-approved partial answer candidate."""
        candidate = build_best_effort_grounded_answer(
            arguments,
            unsupported,
            state.citations,
            max_items=state.max_answer_items,
        )
        claim_count = sum(
            item.get("kind") == "supported_claim"
            for item in candidate["items"]
        )
        if claim_count > progress.best_effort_claim_count:
            progress.best_effort_arguments = candidate
            progress.best_effort_claim_count = claim_count

    @staticmethod
    def _append_correction(
        state: TurnState, call: ToolCallRequest
    ) -> None:
        """Append a bounded same-evidence correction exchange."""
        state.messages.append(
            Message(
                role=Role.ASSISTANT,
                content="",
                tool_calls=[
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments),
                        },
                    }
                ],
            )
        )
        state.messages.append(
            Message(
                role=Role.TOOL,
                name=SUBMIT_GROUNDED_ANSWER,
                tool_call_id=call.id,
                content=json.dumps(
                    {
                        "error": "invalid_grounded_answer",
                        "details": state.structured_error,
                        "instruction": (
                            "Resubmit a corrected answer using the same retrieved "
                            "evidence."
                        ),
                    }
                ),
            )
        )

    @staticmethod
    def _assistant_tool_envelope(
        response: LLMResponse, calls: list[ToolCallRequest]
    ) -> Message:
        """Convert effective typed calls into a turn-local tool envelope."""
        return Message(
            role=Role.ASSISTANT,
            content=response.content or "",
            tool_calls=[
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments),
                    },
                }
                for call in calls
            ],
        )

    @staticmethod
    def _remaining_gap(items: list[dict[str, Any]]) -> str:
        """Combine structured limitation text into one bounded search target."""
        gaps = [
            str(item.get("text", "")).strip()
            for item in items
            if isinstance(item, dict)
            and item.get("kind") == "evidence_limitation"
            and str(item.get("text", "")).strip()
        ]
        return " ".join(gaps)[:1000] or "remaining evidence gap"

    @staticmethod
    def _append_sufficiency_feedback(
        state: TurnState, call: ToolCallRequest, remaining_gap: str
    ) -> None:
        """Persist the named gap before forcing the next bounded search."""
        state.messages.append(
            Message(
                role=Role.ASSISTANT,
                content="",
                tool_calls=[
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments),
                        },
                    }
                ],
            )
        )
        state.messages.append(
            Message(
                role=Role.TOOL,
                name=SUBMIT_GROUNDED_ANSWER,
                tool_call_id=call.id,
                content=json.dumps(
                    {
                        "status": "more_evidence_required",
                        "remaining_gap": remaining_gap,
                        "instruction": (
                            "The application will bind the next web query to this "
                            "remaining gap."
                        ),
                    }
                ),
            )
        )

    @staticmethod
    def _bind_remaining_gap_query(
        calls: list[ToolCallRequest], remaining_gap: str | None
    ) -> list[ToolCallRequest]:
        """Bind additional web calls to the structured remaining gap."""
        if not remaining_gap:
            return calls
        return [
            call.model_copy(
                update={
                    "arguments": {
                        **call.arguments,
                        "query": remaining_gap,
                    }
                }
            )
            if call.name == "search_web"
            else call
            for call in calls
        ]

    def _salvage_best_effort(
        self, state: TurnState, progress: _Progress
    ) -> None:
        """Render verifier-approved partial evidence after correction exhaustion."""
        if (
            not state.structured_error
            or progress.best_effort_arguments is None
        ):
            return
        state.assistant_text, _used = parse_and_render_grounded_answer(
            progress.best_effort_arguments,
            state.citations,
            max_items=state.max_answer_items,
        )
        state.structured_grounded = True
        state.structured_error = None
        self._tracer.log_span(
            name="best_effort_grounded_answer",
            input={
                "supported_claim_count": progress.best_effort_claim_count
            },
            output=state.assistant_text,
        )
