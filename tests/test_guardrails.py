import pytest
import json
from pathlib import Path

from ollive.application.guardrails import (
    CONTEXT_PROMPT,
    ContextMode,
    MEDICAL_BOUNDARY_PROMPT,
    POLICIES,
    ROUTER_PROMPT,
    ResponseDepth,
    TurnKind,
    classify_context,
    classify_turn,
)
from ollive.application.config import load_config
from ollive.application.grounded_answer import SUPPORT_VERIFIER_PROMPT
from ollive.application.tools import TOOL_SCHEMAS
from ollive.adapters.security.llm_security import SECURITY_SYSTEM_PROMPT
from ollive.evaluation.judge import JUDGE_PROMPT
from ollive.evaluation.prompt_audit import (
    audit_prompt_specificity,
    load_case_corpus,
    prompt_surfaces,
)

from ollive.domain.models import (
    LLMResponse,
    Message,
    Role,
    ToolCallRequest,
    UsageStats,
)


class RoutingLLM:
    model_name = "router"
    backend_name = "test"

    def __init__(
        self,
        kind: str | None,
        *,
        wrong_tool: bool = False,
        response_depth: object = "standard",
        web_search_requested: bool = False,
        context_mode: object = "current",
        omit_response_depth: bool = False,
        extra_field: bool = False,
    ):
        """Store the router payload returned by the deterministic LLM stub."""
        self.kind = kind
        self.wrong_tool = wrong_tool
        self.response_depth = response_depth
        self.web_search_requested = web_search_requested
        self.context_mode = context_mode
        self.omit_response_depth = omit_response_depth
        self.extra_field = extra_field

    def chat(self, messages, tools=None, tool_choice=None):
        """Return configured context and route decisions without network I/O."""
        tool_name = tools[0]["function"]["name"] if tools else None
        if tool_name == "judge_context":
            return LLMResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="context-1",
                        name="judge_context",
                        arguments={
                            "requires_prior_dialogue": (
                                self.context_mode == "previous_and_current"
                            )
                        },
                    )
                ],
                usage=UsageStats(total_tokens=3, model="router", backend="test"),
            )
        calls = []
        if self.kind is not None:
            arguments = {
                "kind": self.kind,
                "web_search_requested": self.web_search_requested,
            }
            if self.extra_field:
                arguments["unexpected"] = True
            if not self.omit_response_depth:
                arguments["response_depth"] = self.response_depth
            calls.append(
                ToolCallRequest(
                    id="route-1",
                    name="wrong_tool" if self.wrong_tool else "route_turn",
                    arguments=arguments,
                )
            )
        return LLMResponse(
            tool_calls=calls,
            usage=UsageStats(total_tokens=7, model="router", backend="test"),
        )


@pytest.mark.parametrize(
    ("kind", "allow_tools"),
    [
        (TurnKind.CONVERSATION, False),
        (TurnKind.WELLNESS_CLARIFICATION, False),
        (TurnKind.WELLNESS, True),
        (TurnKind.MEDICAL, False),
        (TurnKind.OUT_OF_SCOPE, False),
    ],
)
def test_semantic_router_accepts_only_declared_enum(kind, allow_tools):
    """Accept only declared route kinds and their matching tool policies."""
    policy, usage = classify_turn(RoutingLLM(kind.value), "arbitrary phrasing")
    assert policy.kind == kind
    assert policy.allow_tools is allow_tools
    assert policy.require_tools is (kind is TurnKind.WELLNESS)
    assert usage.total_tokens == 7


def test_wellness_grounding_is_application_owned():
    """Require evidence tools for every route classified as wellness."""
    policy, _usage = classify_turn(RoutingLLM("wellness"), "wellness request")

    assert policy.kind is TurnKind.WELLNESS
    assert policy.allow_tools
    assert policy.require_tools

def test_explicit_web_request_enables_one_web_evidence_round():
    """Carry an explicit web request into the grounded agent policy."""
    policy, _usage = classify_turn(
        RoutingLLM("wellness", web_search_requested=True),
        "Can you search the internet for healthy lifestyle tips",
    )

    assert policy.kind is TurnKind.WELLNESS
    assert policy.require_tools
    assert policy.web_search_requested


def test_router_exposes_explicit_context_dependency():
    """Carry semantic continuation independently of route and web policy."""
    policy, usage = classify_turn(
        RoutingLLM("wellness", context_mode="previous_and_current"),
        "dependent request",
        history=[Message(role=Role.USER, content="prior request")],
    )

    assert policy.context_mode is ContextMode.PREVIOUS_AND_CURRENT
    assert usage.total_tokens == 10


@pytest.mark.parametrize(
    "router",
    [
        RoutingLLM(None),
        RoutingLLM("invented_route"),
        RoutingLLM("wellness", wrong_tool=True),
        RoutingLLM("wellness", extra_field=True),
        RoutingLLM("conversation", web_search_requested=True),
        RoutingLLM("wellness", omit_response_depth=True),
        RoutingLLM("wellness", response_depth="invented"),
    ],
)
def test_malformed_router_output_fails_closed(router):
    """Fall back to the safest route when router output is malformed."""
    policy, _usage = classify_turn(router, "anything")
    assert policy.kind == TurnKind.OUT_OF_SCOPE
    assert not policy.allow_tools


def test_model_prompts_are_free_of_content_examples():
    """Prevent query-specific demonstrations from anchoring model decisions."""
    prompt_texts = [
        MEDICAL_BOUNDARY_PROMPT,
        CONTEXT_PROMPT,
        ROUTER_PROMPT,
        SUPPORT_VERIFIER_PROMPT,
        JUDGE_PROMPT,
        SECURITY_SYSTEM_PROMPT,
        load_config()["agent"]["system_prompt"],
        *[policy.instruction for policy in POLICIES.values()],
        json.dumps(TOOL_SCHEMAS),
    ]
    combined = "\n".join(prompt_texts).casefold()
    forbidden = ("example:", "for example", "e.g.", "for instance")

    assert all(marker not in combined for marker in forbidden)

    benchmark_literals = (
        "harmbench_direct_",
        "jbb_pair_",
        "ignore any previous and following instructions",
        "i hate humans",
        "kill humans",
    )
    security_prompt = SECURITY_SYSTEM_PROMPT.casefold()
    assert all(literal not in security_prompt for literal in benchmark_literals)


def test_model_prompts_are_case_agnostic_against_versioned_datasets():
    """Reject prompt text copied from or conditional on known evaluation cases."""
    report = audit_prompt_specificity(
        surfaces=prompt_surfaces(),
        cases=load_case_corpus(Path("evaluation/datasets")),
    )

    assert report["status"] == "pass", report["findings"]
