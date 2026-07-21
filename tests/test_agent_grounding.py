from ollive.adapters.observability.langfuse_tracer import NoOpTracer
from ollive.application.agent import CITATION_REJECTION_MESSAGE, WellnessAgent
from ollive.application.grounded_answer import SUBMIT_GROUNDED_ANSWER
from ollive.domain.models import (
    Citation,
    LLMResponse,
    Message,
    Role,
    ToolCallRequest,
    ToolResult,
    UsageStats,
)


class StructuredSleepLLM:
    model_name = "structured-test"
    backend_name = "test"

    def __init__(self, malformed_final=False, recover_after_error=False):
        """Configure whether the deterministic final submission is malformed."""
        self.malformed_final = malformed_final
        self.recover_after_error = recover_after_error
        self.answer_calls = 0

    def chat(self, messages, tools=None, tool_choice=None):
        """Simulate routing, required KB lookup, and structured answer submission."""
        tool_name = tools[0]["function"]["name"] if tools else None
        if tool_name == "route_turn":
            return LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="route",
                        name="route_turn",
                        arguments={
                            "kind": "wellness",
                            "needs_grounding": True,
                            "context_mode": "current",
                            "response_depth": "standard",
                        },
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
        """Expose deterministic KB and web-search tool schemas."""
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
        """Return sleep evidence while asserting exact user-query fidelity."""
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
    """Build a test agent with deterministic tools and no-op tracing."""
    return WellnessAgent(
        llm=llm,
        tools=SleepTools(),
        tracer=NoOpTracer(),
        system_prompt="Use grounded wellness evidence.",
    )


def test_agent_forces_lookup_and_renders_structured_citations():
    """Force retrieval before rendering a validated structured citation."""
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
    """Retry a malformed submission and recover after validation feedback."""
    llm = StructuredSleepLLM(malformed_final=True, recover_after_error=True)
    result = build_agent(llm).chat("I want sleep tips")

    assert result.assistant_message.startswith("Maintain a regular sleep schedule.")
    assert not result.citation_validation_failed
    assert llm.answer_calls == 3


def test_malformed_structured_answer_fails_closed_and_memory_stays_clean():
    """Withhold an invalid answer without retaining internal tool messages."""
    agent = build_agent(StructuredSleepLLM(malformed_final=True))
    result = agent.chat("I want sleep tips")

    assert result.assistant_message == CITATION_REJECTION_MESSAGE
    assert result.citation_validation_failed
    assert [message.role for message in agent.memory.as_list()] == [
        Role.USER,
        Role.ASSISTANT,
    ]
    assert all(message.role != Role.TOOL for message in agent.memory.as_list())


class DetailedFollowupLLM:
    model_name = "detailed-followup-test"
    backend_name = "test"

    def __init__(self):
        """Count answer-stage calls for the contextual follow-up scenario."""
        self.answer_calls = 0

    def chat(self, messages, tools=None, tool_choice=None):
        """Simulate contextual routing, KB retrieval, and a four-item answer."""
        tool_names = [tool["function"]["name"] for tool in tools or []]
        if tool_names == ["route_turn"]:
            return LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="route",
                        name="route_turn",
                        arguments={
                            "kind": "wellness",
                            "needs_grounding": True,
                            "context_mode": "previous_and_current",
                            "response_depth": "detailed",
                        },
                    )
                ]
            )

        self.answer_calls += 1
        if self.answer_calls == 1:
            assert tool_names == ["lookup_kb"]
            assert all(message.role is not Role.ASSISTANT for message in messages)
            return LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="lookup",
                        name="lookup_kb",
                        arguments={"doc_types": ["daily_habits"]},
                    )
                ]
            )

        assert tool_names == [SUBMIT_GROUNDED_ANSWER, "search_web"]
        item_schema = tools[0]["function"]["parameters"]["properties"]["items"]
        assert item_schema["maxItems"] == 5
        marker = item_schema["items"]["properties"]["citation"]["enum"][1]
        actions = [
            "Keep a regular sleep schedule.",
            "Make the sleeping environment dark.",
            "Keep the sleeping environment quiet.",
            "Limit caffeine and screen time before bed.",
        ]
        return LLMResponse(
            tool_calls=[
                ToolCallRequest(
                    id="submit",
                    name=SUBMIT_GROUNDED_ANSWER,
                    arguments={
                        "items": [
                            {
                                "kind": "supported_claim",
                                "text": action,
                                "citation": marker,
                            }
                            for action in actions
                        ]
                    },
                )
            ]
        )


class DetailedFollowupTools(SleepTools):
    def execute(self, call, *, user_query=None):
        """Require the original sleep request to remain attached to elaboration."""
        assert call.name == "lookup_kb"
        assert user_query == "How can I sleep on time?\nElaborate on it?"
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content="{\"results\": [{\"text\": \"sleep actions\"}]}",
            citations=[self.citation],
        )


def test_elaboration_keeps_prior_topic_and_allows_more_supported_actions():
    """Answer an elliptical follow-up from KB evidence without unnecessary web search."""
    agent = WellnessAgent(
        llm=DetailedFollowupLLM(),
        tools=DetailedFollowupTools(),
        tracer=NoOpTracer(),
        system_prompt="Use grounded wellness evidence.",
    )
    agent.memory.add(Message(role=Role.USER, content="How can I sleep on time?"))
    agent.memory.add(
        Message(role=Role.ASSISTANT, content="Keep a regular sleep schedule.")
    )

    result = agent.chat("Elaborate on it?")

    assert [step["name"] for step in result.tool_trace] == ["lookup_kb"]
    assert result.tool_trace[0]["arguments"]["query"] == (
        "How can I sleep on time?\nElaborate on it?"
    )
    assert result.assistant_message.count(DetailedFollowupTools.citation.marker) == 4
    assert not result.citation_validation_failed


class PartialEvidenceLLM:
    model_name = "partial-evidence-test"
    backend_name = "test"

    def __init__(self):
        """Initialize the partial-evidence model-call counter."""
        self.answer_calls = 0

    def chat(self, messages, tools=None, tool_choice=None):
        """Simulate a KB gap followed by web completion and grounded submission."""
        tool_names = [tool["function"]["name"] for tool in tools or []]
        if tool_names == ["route_turn"]:
            return LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="route",
                        name="route_turn",
                        arguments={
                            "kind": "wellness",
                            "needs_grounding": True,
                            "context_mode": "current",
                            "response_depth": "standard",
                        },
                    )
                ]
            )

        self.answer_calls += 1
        if self.answer_calls == 1:
            assert tool_names == ["lookup_kb"]
            return LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="lookup",
                        name="lookup_kb",
                        arguments={"doc_types": ["daily_habits"]},
                    )
                ]
            )
        if self.answer_calls == 2:
            assert tool_names == [SUBMIT_GROUNDED_ANSWER, "search_web"]
            assert tool_choice == "required"
            return LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="gap",
                        name=SUBMIT_GROUNDED_ANSWER,
                        arguments={
                            "items": [
                                {
                                    "kind": "evidence_limitation",
                                    "text": "The KB does not establish adult sleep duration.",
                                    "citation": "__NO_CITATION__",
                                }
                            ]
                        },
                    )
                ]
            )
        if self.answer_calls == 3:
            assert tool_names == ["search_web"]
            assert tool_choice == {
                "type": "function",
                "function": {"name": "search_web"},
            }
            return LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="web",
                        name="search_web",
                        arguments={"query": "recommended sleep duration for adults"},
                    )
                ]
            )

        assert tool_names == [SUBMIT_GROUNDED_ANSWER]
        markers = tools[0]["function"]["parameters"]["properties"]["items"][
            "items"
        ]["properties"]["citation"]["enum"]
        return LLMResponse(
            tool_calls=[
                ToolCallRequest(
                    id="submit",
                    name=SUBMIT_GROUNDED_ANSWER,
                    arguments={
                        "items": [
                            {
                                "kind": "supported_claim",
                                "text": "Keep a regular sleep schedule.",
                                "citation": markers[1],
                            },
                            {
                                "kind": "supported_claim",
                                "text": "Most adults need at least seven hours of sleep.",
                                "citation": markers[2],
                            },
                        ]
                    },
                )
            ]
        )


class PartialEvidenceTools(SleepTools):
    web_citation = Citation(
        doc_type="web",
        line=1,
        descriptor="abc123",
        title="CDC sleep guidance",
        text="Most adults need at least seven hours of sleep.",
        source_type="web",
        url="https://www.cdc.gov/sleep/about/index.html",
        domain="www.cdc.gov",
    )

    def execute(self, call, *, user_query=None):
        """Return distinct KB or web citations for partial-evidence tests."""
        if call.name == "search_web":
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content="{\"results\": []}",
                citations=[self.web_citation],
            )
        assert call.name == "lookup_kb"
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content="{\"results\": []}",
            citations=[self.citation],
        )


def test_agent_completes_partial_kb_evidence_with_cited_web_source():
    """Complete a material KB gap with an explicitly cited web source."""
    agent = WellnessAgent(
        llm=PartialEvidenceLLM(),
        tools=PartialEvidenceTools(),
        tracer=NoOpTracer(),
        system_prompt="Use grounded wellness evidence.",
    )
    result = agent.chat("What time should I sleep and how many hours do I need?")

    assert [step["name"] for step in result.tool_trace] == ["lookup_kb", "search_web"]
    assert {citation.source_type for citation in result.citations} == {
        "knowledge_base",
        "web",
    }
    assert PartialEvidenceTools.web_citation.marker in result.assistant_message
    assert not result.citation_validation_failed


class NoEvidenceLLM:
    model_name = "no-evidence-test"
    backend_name = "test"

    def __init__(self):
        """Initialize the no-evidence model-call counter."""
        self.answer_calls = 0

    def chat(self, messages, tools=None, tool_choice=None):
        """Simulate empty KB and web searches followed by a limitation."""
        tool_names = [tool["function"]["name"] for tool in tools or []]
        if tool_names == ["route_turn"]:
            return LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="route",
                        name="route_turn",
                        arguments={
                            "kind": "wellness",
                            "needs_grounding": True,
                            "context_mode": "current",
                            "response_depth": "standard",
                        },
                    )
                ]
            )

        self.answer_calls += 1
        if self.answer_calls == 1:
            assert tool_names == ["lookup_kb"]
            selected = "lookup_kb"
        elif self.answer_calls == 2:
            assert tool_names == ["search_web"]
            selected = "search_web"
        else:
            assert tool_names == [SUBMIT_GROUNDED_ANSWER]
            markers = tools[0]["function"]["parameters"]["properties"]["items"][
                "items"
            ]["properties"]["citation"]["enum"]
            assert markers == ["__NO_CITATION__"]
            return LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="submit",
                        name=SUBMIT_GROUNDED_ANSWER,
                        arguments={
                            "items": [
                                {
                                    "kind": "evidence_limitation",
                                    "text": "The available sources do not establish this detail.",
                                    "citation": "__NO_CITATION__",
                                }
                            ]
                        },
                    )
                ]
            )

        return LLMResponse(
            tool_calls=[
                ToolCallRequest(
                    id=selected,
                    name=selected,
                    arguments={} if selected == "lookup_kb" else {"query": "missing detail"},
                )
            ]
        )


class NoEvidenceTools(SleepTools):
    def execute(self, call, *, user_query=None):
        """Return an empty result for every evidence tool call."""
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content="{\"results\": []}",
            citations=[],
        )


def test_agent_returns_a_structured_limitation_when_all_sources_are_empty():
    """Return a citation-free limitation when every source is empty."""
    agent = WellnessAgent(
        llm=NoEvidenceLLM(),
        tools=NoEvidenceTools(),
        tracer=NoOpTracer(),
        system_prompt="Use grounded wellness evidence.",
    )

    result = agent.chat("Give me an unsupported wellness detail")

    assert result.assistant_message == "The available sources do not establish this detail."
    assert [step["name"] for step in result.tool_trace] == ["lookup_kb", "search_web"]
    assert result.citations == []
    assert not result.citation_validation_failed
