"""Tests for deterministic persona and output-canary security controls."""

from __future__ import annotations

from ollive.adapters.observability.langfuse_tracer import NoOpTracer
from ollive.adapters.security.persona import PersonaGuard
from ollive.application.canary import OutputCanary
from ollive.application.guardrails import CONVERSATION_POLICY
from ollive.application.pipeline.contracts import TurnState
from ollive.application.pipeline.output import OutputStage
from ollive.application.security import SECURITY_REJECTION_MESSAGE, SecurityBroker
from ollive.domain.security import AuthorityAssessment


def _assessment(*, persona_mode: str, target: str, effect: str) -> AuthorityAssessment:
    """Build an executed authority assessment for deterministic guard tests."""
    return AuthorityAssessment(
        content_mode="direct_request",
        persona_mode=persona_mode,
        target=target,
        effect=effect,
        execution_requested=True,
        evidence_excerpt="override the application policy",
    )


def test_persona_guard_blocks_only_privileged_authority_escalation():
    """Keep harmless role-play distinct from DAN-style authority escalation."""
    guard = PersonaGuard()

    assert guard.block_reason(
        _assessment(
            persona_mode="authority_seeking",
            target="assistant_policy",
            effect="override",
        )
    ) == "jailbreak"
    assert guard.block_reason(
        _assessment(
            persona_mode="ordinary",
            target="response_content",
            effect="normal_request",
        )
    ) is None


def test_output_canary_blocks_a_formatted_marker_leak():
    """Detect an integrity marker even when output adds presentation separators."""
    token = "f2c9a4b6d8e1f3a5c7b9d2e4f6a8c1b3"
    broker = SecurityBroker(object(), output_canary=OutputCanary(token))
    state = TurnState.begin(
        user_text="hello", history=[], model="test", backend="test"
    )
    state.policy = CONVERSATION_POLICY
    state.assistant_text = "Internal marker: f2c9-a4b6 d8e1f3a5c7b9d2e4f6a8c1b3"

    OutputStage(security=broker, tracer=NoOpTracer()).run(
        state, validate_grounding=False
    )

    assert state.security_trace[-1]["decision_source"] == "canary"
    assert state.assistant_text == SECURITY_REJECTION_MESSAGE
    assert state.security_validation_failed
    assert state.security_trace[-1]["reason_code"] == "canary_leak_detected"


def test_output_canary_does_not_flag_unrelated_response_text():
    """Avoid treating normal assistant output as a canary leak."""
    broker = SecurityBroker(
        object(), output_canary=OutputCanary("f2c9a4b6d8e1f3a5c7b9d2e4f6a8c1b3")
    )

    assert broker.review_canary("A normal wellness response.") is None
