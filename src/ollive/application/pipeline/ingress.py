"""Security checks that run before any answer-model call."""

from __future__ import annotations

from ollive.application.pipeline.contracts import TurnState
from ollive.application.security import SecurityBroker
from ollive.domain.models import Message, Role


class IngressStage:
    """Gate current input and composed dialogue before routing."""

    def __init__(self, security: SecurityBroker) -> None:
        """Bind the application-owned security enforcement broker."""
        self._security = security

    def run(self, state: TurnState) -> bool:
        """Return true only when both input and aggregate context are approved."""
        input_review = self._security.review_input(state.user_text)
        state.record_security(input_review)
        if not input_review.allowed:
            return False

        context_review = self._security.review_context(
            state.user_text,
            [
                *state.history,
                Message(role=Role.USER, content=state.user_text),
            ],
        )
        state.record_security(context_review)
        return context_review.allowed
