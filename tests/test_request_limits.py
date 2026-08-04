"""Application-owned request and many-shot context budget tests."""

from __future__ import annotations

from ollive.adapters.observability.langfuse_tracer import NoOpTracer
from ollive.application.agent import WellnessAgent
from ollive.application.request_limits import RequestLimits, SessionRequestLimiter
from ollive.application.security import SecurityBroker
from ollive.domain.models import Message, Role


class Clock:
    def __init__(self) -> None:
        """Initialize the controllable monotonic timestamp."""
        self.now = 0.0

    def __call__(self) -> float:
        """Return the current test timestamp."""
        return self.now


def test_limiter_blocks_long_single_message_before_model_review():
    """Reject a single oversized request without semantic review."""
    limiter = SessionRequestLimiter(
        RequestLimits(
            max_requests=3,
            window_seconds=10,
            max_message_chars=5,
            max_context_chars=10,
        )
    )
    review = limiter.review("123456", [])
    assert review is not None
    assert review.reason_code == "input_size_limit"
    assert review.decision_source == "application_policy"


def test_limiter_blocks_many_shot_context_accumulation():
    """Reject accumulated dialogue plus current input above its context cap."""
    limiter = SessionRequestLimiter(
        RequestLimits(
            max_requests=3,
            window_seconds=10,
            max_message_chars=6,
            max_context_chars=10,
        )
    )
    history = [Message(role=Role.USER, content="12345")]
    review = limiter.review("123456", history)
    assert review is not None
    assert review.reason_code == "context_size_limit"


def test_limiter_enforces_and_resets_sliding_window():
    """Expire old attempts and clear the window when the session resets."""
    clock = Clock()
    limiter = SessionRequestLimiter(
        RequestLimits(
            max_requests=2,
            window_seconds=10,
            max_message_chars=10,
            max_context_chars=10,
        ),
        clock=clock,
    )
    assert limiter.review("one", []) is None
    assert limiter.review("two", []) is None
    assert limiter.review("three", []).reason_code == "session_rate_limit"
    clock.now = 11
    assert limiter.review("later", []) is None
    limiter.clear()
    assert limiter.review("reset", []) is None


class NeverCalledLLM:
    model_name = "never-called"
    backend_name = "test"

    def __init__(self) -> None:
        """Initialize the model-call counter."""
        self.calls = 0

    def chat(self, messages, tools=None, tool_choice=None):
        """Fail if deterministic admission incorrectly calls a model."""
        self.calls += 1
        raise AssertionError("budget-blocked input reached a model")


def test_agent_applies_budget_before_any_model_call():
    """Prove session admission blocks before Security LM or answer-model calls."""
    llm = NeverCalledLLM()
    agent = WellnessAgent(
        llm=llm,
        tools=object(),
        tracer=NoOpTracer(),
        security=SecurityBroker(object()),
        system_prompt="test",
        request_limits=RequestLimits(
            max_requests=2,
            window_seconds=10,
            max_message_chars=5,
            max_context_chars=10,
        ),
    )

    result = agent.chat("123456")

    assert llm.calls == 0
    assert result.policy_route == "security_blocked"
    assert result.security_trace[0]["reason_code"] == "input_size_limit"
    assert agent.memory.as_list() == []
