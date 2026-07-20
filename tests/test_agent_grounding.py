from ollive.adapters.observability.langfuse_tracer import NoOpTracer
from ollive.application.agent import CITATION_REJECTION_MESSAGE, WellnessAgent
from ollive.application.grounded_answer import SUBMIT_GROUNDED_ANSWER
from ollive.domain.models import (
    Citation,
    LLMResponse,
    Role,
    ToolCallRequest,
    ToolResult,
    UsageStats,
)


class StructuredSleepLLM:
    model_name = "structured-test"
    backend_name = "test"

    def __init__(self, malformed_final=False, recover_after_error=False):
        self.malformed_final = malformed_final
        self.recover_after_error = recover_after_error
        self.answer_calls = 0

    def chat(self, messages, tools=None, tool_choice=None):
        tool_name = tools[0]["function"]["name"] if tools else None
        if tool_name == "route_turn":
            return LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="route",
                        name="route_turn",
                        arguments={"kind": "wellness", "needs_grounding": True},
                    )
                ],
                usage=UsageStats(total_tokens=1),
            )

        self.answer_calls += 1
        if self.answer_calls == 1:
            assert tool_name == "lookup_kb"
            assert tool_choice == {
                "type": "function",
                "function": {"name": "lookup_kb"},
            }
            return LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="lookup",
                        name="lookup_kb",
                        arguments={"doc_types": ["daily_habits"], "top_k": 5},
                    )
                ],
                usage=UsageStats(total_tokens=2),
            )

        assert tool_name == SUBMIT_GROUNDED_ANSWER
        marker_enum = tools[0]["function"]["parameters"]["properties"]["items"][
            "items"
        ]["properties"]["citation"]["enum"]
        marker = marker_enum[1]
        arguments = (
            {"items": []}
            if self.malformed_final and not (
                self.recover_after_error and self.answer_calls > 2
            )
            else {
                "items": [
                    {
                        "kind": "supported_claim",
                        "text": "Maintain a regular sleep schedule.",
                        "citation": marker,
                    }
                ]
            }
        )
        return LLMResponse(
            tool_calls=[
                ToolCallRequest(
                    id="submit",
                    name=SUBMIT_GROUNDED_ANSWER,
                    arguments=arguments,
                )
            ],
            usage=UsageStats(total_tokens=3),
        )


class SleepTools:
    citation = Citation(
        doc_type="daily_habits",
        line=11,
        descriptor="sleep-hygiene-is-among-the",
        text="Maintaining a regular sleep schedule supports restorative rest.",
    )

    @property
    def schemas(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "lookup_kb",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    def execute(self, call, *, user_query=None):
        assert call.name == "lookup_kb"
        assert user_query == "I want sleep tips"
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content=(
                '{"results":[{"citation":"'
                + self.citation.marker
                + '","text":"Maintaining a regular sleep schedule."}]}'
            ),
            citations=[self.citation],
        )


def build_agent(llm):
    return WellnessAgent(
        llm=llm,
        tools=SleepTools(),
        tracer=NoOpTracer(),
        system_prompt="Use grounded wellness evidence.",
    )


def test_agent_forces_lookup_and_renders_structured_citations():
    agent = build_agent(StructuredSleepLLM())
    result = agent.chat("I want sleep tips")

    assert result.assistant_message == (
        "Maintain a regular sleep schedule. "
        "[daily_habits:L11:sleep-hygiene-is-among-the]"
    )
    assert [citation.marker for citation in result.citations] == [
        SleepTools.citation.marker
    ]
    assert not result.citation_validation_failed
    assert [message.role for message in agent.memory.as_list()] == [
        Role.USER,
        Role.ASSISTANT,
    ]
    assert all(not message.tool_calls for message in agent.memory.as_list())


def test_structured_answer_recovers_after_validation_feedback():
    llm = StructuredSleepLLM(malformed_final=True, recover_after_error=True)
    result = build_agent(llm).chat("I want sleep tips")

    assert result.assistant_message.startswith("Maintain a regular sleep schedule.")
    assert not result.citation_validation_failed
    assert llm.answer_calls == 3


def test_malformed_structured_answer_fails_closed_and_memory_stays_clean():
    agent = build_agent(StructuredSleepLLM(malformed_final=True))
    result = agent.chat("I want sleep tips")

    assert result.assistant_message == CITATION_REJECTION_MESSAGE
    assert result.citation_validation_failed
    assert [message.role for message in agent.memory.as_list()] == [
        Role.USER,
        Role.ASSISTANT,
    ]
    assert all(message.role != Role.TOOL for message in agent.memory.as_list())
