"""Deterministic per-session request and context budgets."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import monotonic
from typing import Callable

from ollive.domain.models import Message
from ollive.domain.security import SecurityReview, SecurityStage


@dataclass(frozen=True)
class RequestLimits:
    """Application-owned bounds applied before any model call."""

    max_requests: int = 12
    window_seconds: float = 60.0
    max_message_chars: int = 20_000
    max_context_chars: int = 48_000

    def __post_init__(self) -> None:
        """Reject non-positive or internally inconsistent limits."""
        if self.max_requests < 1 or self.window_seconds <= 0:
            raise ValueError("request rate limits must be positive")
        if self.max_message_chars < 1:
            raise ValueError("max_message_chars must be positive")
        if self.max_context_chars < self.max_message_chars:
            raise ValueError("max_context_chars must cover one maximum-size message")


class SessionRequestLimiter:
    """Bound request bursts and many-shot loading within one agent session."""

    def __init__(
        self,
        limits: RequestLimits,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        """Initialize a session-local sliding window with deterministic bounds."""
        self._limits = limits
        self._clock = clock
        self._requests: deque[float] = deque()

    def review(
        self, user_text: str, history: list[Message]
    ) -> SecurityReview | None:
        """Return an application block when any configured budget is exceeded."""
        now = self._clock()
        cutoff = now - self._limits.window_seconds
        while self._requests and self._requests[0] <= cutoff:
            self._requests.popleft()
        self._requests.append(now)

        if len(user_text) > self._limits.max_message_chars:
            return self._block("input_size_limit")
        context_chars = len(user_text) + sum(len(message.content) for message in history)
        if context_chars > self._limits.max_context_chars:
            return self._block("context_size_limit")
        if len(self._requests) > self._limits.max_requests:
            return self._block("session_rate_limit")
        return None

    def clear(self) -> None:
        """Reset the sliding window with the rest of the session."""
        self._requests.clear()

    @staticmethod
    def _block(reason_code: str) -> SecurityReview:
        """Build a trace-compatible application-policy block."""
        return SecurityReview(
            stage=SecurityStage.INPUT,
            decision="block",
            reason_code=reason_code,
            risk_flags=[reason_code],
            trust_score=0.0,
            decision_source="application_policy",
            items=[],
        )
