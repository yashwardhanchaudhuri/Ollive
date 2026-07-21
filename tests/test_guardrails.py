import pytest

from ollive.application.guardrails import TurnKind, classify_turn
from ollive.domain.models import LLMResponse, ToolCallRequest, UsageStats


class RoutingLLM:
    model_name = "router"
    backend_name = "test"

    def __init__(
        self,
        kind: str | None,
        *,
        grounding: object | None = None,
        omit_grounding: bool = False,
        wrong_tool: bool = False,
    ):
        """Store the router payload returned by the deterministic LLM stub."""
        self.kind = kind
        self.grounding = kind == "wellness" if grounding is None else grounding
        self.omit_grounding = omit_grounding
        self.wrong_tool = wrong_tool

    def chat(self, messages, tools=None, tool_choice=None):
        """Return the configured semantic-routing response without network I/O."""
        calls = []
        if self.kind is not None:
            arguments = {"kind": self.kind}
            if not self.omit_grounding:
                arguments["needs_grounding"] = self.grounding
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


def test_wellness_boundary_disables_tools_without_changing_domain():
    """Keep a wellness route while honoring a boundary that disables tools."""
    policy, _usage = classify_turn(
        RoutingLLM("wellness", grounding=False), "refuse a fabrication request"
    )
    assert policy.kind is TurnKind.WELLNESS
    assert not policy.allow_tools
    assert not policy.require_tools


@pytest.mark.parametrize(
    "router",
    [
        RoutingLLM(None),
        RoutingLLM("invented_route"),
        RoutingLLM("wellness", wrong_tool=True),
        RoutingLLM("wellness", omit_grounding=True),
        RoutingLLM("wellness", grounding="true"),
        RoutingLLM("conversation", grounding=True),
    ],
)
def test_malformed_router_output_fails_closed(router):
    """Fall back to the safest route when router output is malformed."""
    policy, _usage = classify_turn(router, "anything")
    assert policy.kind == TurnKind.OUT_OF_SCOPE
    assert not policy.allow_tools
