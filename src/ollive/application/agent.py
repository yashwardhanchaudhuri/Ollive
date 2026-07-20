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
from ollive.application.guardrails import TurnPolicy, classify_turn
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
    @wraps(method)
    def wrapped(self: "WellnessAgent", *args: Any, **kwargs: Any) -> AgentTurnResult:
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
        return self._session_usage

    @property
    def memory(self) -> ShortTermMemory:
        return self._memory

    def reset(self) -> None:
        self._memory.clear()
        self._session_usage = UsageStats(
            model=self._llm.model_name, backend=self._llm.backend_name
        )
        self._all_citations = []

    @rollback_memory_on_error
    def chat(self, user_text: str) -> AgentTurnResult:
        # Persist dialogue only. Historical tool payloads make later turns larger and
        # can cause the model to reuse stale citations.
        memory_checkpoint = [
            message
            for message in self._memory.as_list()
            if message.role in {Role.USER, Role.ASSISTANT} and not message.tool_calls
        ]
        self._memory.restore(memory_checkpoint)
        policy, routing_usage = classify_turn(self._llm, user_text, memory_checkpoint)
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
            messages = self._build_messages(policy)
            assistant_text = ""
            structured_grounded = False
            structured_error: str | None = None

            for _round in range(self._max_tool_rounds):
                schemas = None
                tool_choice = None
                if turn_citations:
                    schemas = [build_grounded_answer_schema(turn_citations)]
                    tool_choice = forced_grounded_answer_choice()
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

                if turn_citations:
                    if (
                        len(response.tool_calls) != 1
                        or response.tool_calls[0].name != SUBMIT_GROUNDED_ANSWER
                    ):
                        structured_error = (
                            "Grounded finalization did not return exactly one "
                            f"{SUBMIT_GROUNDED_ANSWER} call"
                        )
                        break
                    try:
                        assistant_text, _used = parse_and_render_grounded_answer(
                            response.tool_calls[0].arguments,
                            turn_citations,
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
                    result = self._tools.execute(tc, user_query=user_text)
                    turn_citations.extend(result.citations)
                    trace_arguments = dict(tc.arguments)
                    if tc.name == "lookup_kb":
                        trace_arguments["query"] = user_text
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
                if not (turn_citations and structured_error):
                    response = self._llm.chat(
                        messages, tools=None, tool_choice=None
                    )
                    turn_usage = turn_usage.add(response.usage)
                    assistant_text = response.content

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

    def _build_messages(self, policy: TurnPolicy) -> list[Message]:
        return [
            Message(
                role=Role.SYSTEM,
                content=f"{self._system_prompt}\n\nTurn policy:\n{policy.instruction}",
            ),
            *self._memory.as_list(),
        ]
