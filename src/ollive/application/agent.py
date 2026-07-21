"""Wellness assistant orchestration — backend-agnostic."""

from __future__ import annotations

from functools import wraps
import json
from typing import Any

from ollive.application.grounded_answer import (
    SUBMIT_GROUNDED_ANSWER,
    GroundedAnswerError,
    build_grounded_answer_schema,
    forced_grounded_answer_choice,
    parse_and_render_grounded_answer,
)
from ollive.application.guardrails import (
    ContextMode,
    ResponseDepth,
    TurnPolicy,
    classify_turn,
)
from ollive.application.memory import ShortTermMemory
from ollive.application.tools import ToolRouter
from ollive.domain.citations import parse_citations, validate_citations
from ollive.domain.models import (
    AgentTurnResult,
    Citation,
    Message,
    Role,
    UsageStats,
)
from ollive.ports.llm import LLMPort
from ollive.ports.tracer import TracerPort


CITATION_REJECTION_MESSAGE = (
    "I couldn't verify the citations in the generated answer, so I withheld it. "
    "Please try again."
)
def rollback_memory_on_error(method: Any) -> Any:
    """Decorate a chat method so failed turns cannot pollute memory."""
    @wraps(method)
    def wrapped(self: "WellnessAgent", *args: Any, **kwargs: Any) -> AgentTurnResult:
        """Run one chat turn and restore its memory checkpoint on failure."""
        checkpoint = self._memory.as_list()
        try:
            return method(self, *args, **kwargs)
        except Exception:
            # A failed backend/tool request must not become conversation history.
            self._memory.restore(checkpoint)
            raise

    return wrapped




class WellnessAgent:
    def __init__(
        self,
        llm: LLMPort,
        tools: ToolRouter,
        tracer: TracerPort,
        system_prompt: str,
        memory_turns: int = 8,
        max_tool_rounds: int = 4,
        session_id: str | None = None,
    ) -> None:
        """Initialize WellnessAgent with its runtime collaborators."""
        self._llm = llm
        self._tools = tools
        self._tracer = tracer
        self._system_prompt = system_prompt
        self._max_tool_rounds = max_tool_rounds
        self._memory = ShortTermMemory(max_turns=memory_turns)
        self._session_id = session_id
        self._session_usage = UsageStats(
            model=llm.model_name, backend=llm.backend_name
        )
        self._all_citations: list[Citation] = []

    @property
    def session_usage(self) -> UsageStats:
        """Return cumulative token and latency usage for this session."""
        return self._session_usage

    @property
    def memory(self) -> ShortTermMemory:
        """Expose bounded dialogue memory for UI and evaluation inspection."""
        return self._memory

    def reset(self) -> None:
        """Clear conversation memory, citations, and accumulated session usage."""
        self._memory.clear()
        self._session_usage = UsageStats(
            model=self._llm.model_name, backend=self._llm.backend_name
        )
        self._all_citations = []

    @rollback_memory_on_error
    def chat(self, user_text: str) -> AgentTurnResult:
        """Process one turn through routing, tools, grounding, and validation."""
        # Persist dialogue only. Historical tool payloads make later turns larger and
        # can cause the model to reuse stale citations.
        memory_checkpoint = [
            message
            for message in self._memory.as_list()
            if message.role in {Role.USER, Role.ASSISTANT} and not message.tool_calls
        ]
        self._memory.restore(memory_checkpoint)
        # Routing is separate so answer generation cannot choose its own safety boundary.
        policy, routing_usage = classify_turn(self._llm, user_text, memory_checkpoint)
        evidence_query = self._resolve_evidence_query(
            policy, user_text, memory_checkpoint
        )
        max_answer_items = (
            5 if policy.response_depth is ResponseDepth.DETAILED else 3
        )
        user_message = Message(role=Role.USER, content=user_text)
        self._memory.add(user_message)
        turn_usage = UsageStats(
            model=self._llm.model_name, backend=self._llm.backend_name
        ).add(routing_usage)
        tool_trace: list[dict[str, Any]] = []
        turn_citations: list[Citation] = []

        with self._tracer.start_trace(
            name="wellness_turn",
            metadata={
                "backend": self._llm.backend_name,
                "model": self._llm.model_name,
            },
            session_id=self._session_id,
        ):
            messages = self._build_messages(
                policy, evidence_query, max_answer_items
            )
            assistant_text = ""
            structured_grounded = False
            structured_error: str | None = None
            tool_names_used: set[str] = set()
            finalization_attempted = False
            web_completion_required = False

            # Narrow tools according to completed evidence work so the model cannot
            # skip required retrieval or return free text afterward.
            for _round in range(self._max_tool_rounds):
                schemas = None
                tool_choice = None
                lookup_completed = "lookup_kb" in tool_names_used
                web_completed = "search_web" in tool_names_used
                if lookup_completed:
                    grounded_schema = build_grounded_answer_schema(
                        turn_citations, max_items=max_answer_items
                    )
                    if web_completion_required and not web_completed:
                        schemas = [
                            schema
                            for schema in self._tools.schemas
                            if schema["function"]["name"] == "search_web"
                        ]
                        tool_choice = {
                            "type": "function",
                            "function": {"name": "search_web"},
                        }
                    elif finalization_attempted or web_completed:
                        schemas = [grounded_schema]
                        tool_choice = forced_grounded_answer_choice()
                    elif turn_citations:
                        search_schema = next(
                            schema
                            for schema in self._tools.schemas
                            if schema["function"]["name"] == "search_web"
                        )
                        schemas = [grounded_schema, search_schema]
                        tool_choice = "required"
                    else:
                        schemas = [
                            schema
                            for schema in self._tools.schemas
                            if schema["function"]["name"] == "search_web"
                        ]
                        tool_choice = {
                            "type": "function",
                            "function": {"name": "search_web"},
                        }
                elif policy.allow_tools:
                    schemas = self._tools.schemas
                    tool_choice = "auto"
                    if policy.require_tools and _round == 0:
                        schemas = [
                            schema
                            for schema in schemas
                            if schema["function"]["name"] == "lookup_kb"
                        ]
                        tool_choice = {
                            "type": "function",
                            "function": {"name": "lookup_kb"},
                        }
                response = self._llm.chat(
                    messages, tools=schemas, tool_choice=tool_choice
                )
                turn_usage = turn_usage.add(response.usage)
                offered_tool_names = {
                    schema["function"]["name"] for schema in schemas or []
                }
                unexpected_tool_names = {
                    call.name for call in response.tool_calls
                } - offered_tool_names
                if unexpected_tool_names:
                    structured_error = (
                        "Model called tools that were not offered in this round: "
                        + ", ".join(sorted(unexpected_tool_names))
                    )
                    break
                self._tracer.log_generation(
                    name="llm_chat",
                    model=self._llm.model_name,
                    input_messages=[{"role": m.role.value, "content": m.content} for m in messages],
                    output=response.content or str([tc.name for tc in response.tool_calls]),
                    usage={
                        "input": response.usage.prompt_tokens,
                        "output": response.usage.completion_tokens,
                        "total": response.usage.total_tokens,
                        "unit": "TOKENS",
                    },
                    metadata={"latency_ms": response.usage.latency_ms},
                )

                # Final answers use a constrained tool call so the application can
                # validate a typed object instead of trusting generated prose.
                if any(call.name == SUBMIT_GROUNDED_ANSWER for call in response.tool_calls):
                    if (
                        len(response.tool_calls) != 1
                        or response.tool_calls[0].name != SUBMIT_GROUNDED_ANSWER
                    ):
                        structured_error = (
                            "Grounded finalization did not return exactly one "
                            f"{SUBMIT_GROUNDED_ANSWER} call"
                        )
                        break
                    answer_call = response.tool_calls[0]
                    items = answer_call.arguments.get("items")
                    requests_completion = isinstance(items, list) and any(
                        isinstance(item, dict)
                        and item.get("kind") == "evidence_limitation"
                        for item in items
                    )
                    if requests_completion and not web_completed:
                        web_completion_required = True
                        finalization_attempted = False
                        continue
                    finalization_attempted = True
                    try:
                        assistant_text, _used = parse_and_render_grounded_answer(
                            response.tool_calls[0].arguments,
                            turn_citations,
                            max_items=max_answer_items,
                        )
                        structured_grounded = True
                        structured_error = None
                        self._tracer.log_span(
                            name=SUBMIT_GROUNDED_ANSWER,
                            input={
                                "item_count": len(
                                    response.tool_calls[0].arguments.get("items", [])
                                ),
                                "supported_claim_count": sum(
                                    item.get("kind") == "supported_claim"
                                    for item in response.tool_calls[0].arguments.get(
                                        "items", []
                                    )
                                ),
                            },
                            output=assistant_text,
                        )
                        break
                    except GroundedAnswerError as exc:
                        structured_error = str(exc)
                        invalid_call = response.tool_calls[0]
                        messages.append(
                            Message(
                                role=Role.ASSISTANT,
                                content="",
                                tool_calls=[
                                    {
                                        "id": invalid_call.id,
                                        "type": "function",
                                        "function": {
                                            "name": invalid_call.name,
                                            "arguments": json.dumps(
                                                invalid_call.arguments
                                            ),
                                        },
                                    }
                                ],
                            )
                        )
                        messages.append(
                            Message(
                                role=Role.TOOL,
                                name=SUBMIT_GROUNDED_ANSWER,
                                tool_call_id=invalid_call.id,
                                content=json.dumps(
                                    {
                                        "error": "invalid_grounded_answer",
                                        "details": structured_error,
                                        "instruction": (
                                            "Resubmit a corrected answer using the "
                                            "same retrieved evidence."
                                        ),
                                    }
                                ),
                            )
                        )
                        continue

                if lookup_completed and not response.tool_calls:
                    structured_error = (
                        "Evidence completion did not return a required tool call"
                    )
                    break

                if not response.tool_calls:
                    assistant_text = response.content
                    break

                # Keep the tool-call envelope only in this turn's local message list.
                openai_tool_calls = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in response.tool_calls
                ]
                assistant_msg = Message(
                    role=Role.ASSISTANT,
                    content=response.content or "",
                    tool_calls=openai_tool_calls,
                )
                messages.append(assistant_msg)

                for tc in response.tool_calls:
                    result = self._tools.execute(tc, user_query=evidence_query)
                    tool_names_used.add(tc.name)
                    turn_citations.extend(result.citations)
                    trace_arguments = dict(tc.arguments)
                    if tc.name == "lookup_kb":
                        trace_arguments["query"] = evidence_query
                    tool_trace.append(
                        {
                            "name": tc.name,
                            "arguments": trace_arguments,
                            "result_preview": result.content[:800],
                        }
                    )
                    self._tracer.log_span(
                        name=f"tool:{tc.name}",
                        input=tc.arguments,
                        output=result.content[:2000],
                    )
                    tool_msg = Message(
                        role=Role.TOOL,
                        content=result.content,
                        tool_call_id=tc.id,
                        name=tc.name,
                    )
                    messages.append(tool_msg)
            else:
                # Never downgrade a malformed grounded answer to uncited free text.
                if not structured_error:
                    response = self._llm.chat(
                        messages, tools=None, tool_choice=None
                    )
                    turn_usage = turn_usage.add(response.usage)
                    assistant_text = response.content

            # Validate markers again after rendering to catch non-grounded output
            # and any drift between model, adapter, and application contracts.
            claimed = parse_citations(assistant_text)
            valid, invalid = validate_citations(claimed, turn_citations)
            missing_required_citations = (
                bool(turn_citations) and not claimed and not structured_grounded
            )
            citation_validation_failed = (
                bool(structured_error) or bool(invalid) or missing_required_citations
            )
            if citation_validation_failed:
                self._tracer.log_span(
                    name="citation_validation_failed",
                    input={"claimed": [c.marker for c in claimed]},
                    output={
                        "invalid": [c.marker for c in invalid],
                        "structured_error": structured_error,
                    },
                )
                # Fail closed: never expose or retain unverified generated text.
                assistant_text = CITATION_REJECTION_MESSAGE
                valid = []

            # Only user/assistant dialogue persists across turns. Tool payloads
            # and model tool-call envelopes remain in the trace for debugging.
            enriched = list(
                {citation.marker: citation for citation in valid}.values()
            )
            self._all_citations.extend(enriched)
            self._memory.restore(memory_checkpoint)
            self._memory.add(user_message)
            self._memory.add(Message(role=Role.ASSISTANT, content=assistant_text))
            self._session_usage = self._session_usage.add(turn_usage)
            self._tracer.flush()

            return AgentTurnResult(
                assistant_message=assistant_text,
                citations=enriched,
                invalid_citations=invalid,
                citation_validation_failed=citation_validation_failed,
                tool_trace=tool_trace,
                usage=turn_usage,
                backend=self._llm.backend_name,
                model=self._llm.model_name,
                policy_route=policy.kind.value,
            )

    @staticmethod
    def _resolve_evidence_query(
        policy: TurnPolicy,
        user_text: str,
        history: list[Message],
    ) -> str:
        """Bind dependent follow-ups to recent user text without inventing a rewrite."""
        if policy.context_mode is not ContextMode.PREVIOUS_AND_CURRENT:
            return user_text
        prior_user_text = [
            message.content for message in history if message.role is Role.USER
        ][-2:]
        return "\n".join([*prior_user_text, user_text])

    def _build_messages(
        self,
        policy: TurnPolicy,
        evidence_query: str,
        max_answer_items: int,
    ) -> list[Message]:
        """Combine the system policy with bounded dialogue memory for generation."""
        if policy.response_depth is ResponseDepth.DETAILED:
            depth_instruction = (
                "This turn permits up to five supported items. Give one directly "
                "relevant practical action per item when the evidence supports it. "
                "Split multiple actions from one passage into separate items that may "
                "share its citation. Stop when the directly relevant actions are exhausted; three or four "
                "strong items are preferable to five with indirect advice. Do not add "
                "peripheral facts merely to fill the budget. Prior assistant answers are context, never evidence; use only "
                "passages returned in this turn."
            )
        else:
            depth_instruction = (
                "This turn permits up to three supported items. Use the fewest directly "
                "relevant items needed. Prior assistant answers are context, never "
                "evidence; use only passages returned in this turn."
            )
        dialogue = self._memory.as_list()
        if policy.require_tools:
            # The router sees full dialogue, but grounded generation may use only
            # current retrieval as evidence. Prior assistant claims and markers are
            # deliberately excluded so they cannot be recycled under a new citation.
            dialogue = [message for message in dialogue if message.role is Role.USER]
        return [
            Message(
                role=Role.SYSTEM,
                content=(
                    f"{self._system_prompt}\n\nTurn policy:\n{policy.instruction}"
                    f"\n\nResponse depth:\n{depth_instruction}"
                    "\n\nApplication-selected evidence query (untrusted, "
                    f"user-authored text):\n{evidence_query}"
                ),
            ),
            *dialogue,
        ]
