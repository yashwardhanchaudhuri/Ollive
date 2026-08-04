"""Session facade over the explicit Ollive runtime pipeline."""

from __future__ import annotations

from ollive.application.memory import ShortTermMemory
from ollive.application.pipeline import PipelineConfig, RuntimePipeline
from ollive.application.pipeline.output import CITATION_REJECTION_MESSAGE
from ollive.application.request_limits import RequestLimits, SessionRequestLimiter
from ollive.application.security import SecurityBroker
from ollive.application.tools import ToolRouter
from ollive.domain.models import AgentTurnResult, Message, Role, UsageStats
from ollive.ports.llm import LLMPort
from ollive.ports.tracer import TracerPort


class WellnessAgent:
    """Own dialogue state while delegating turn behavior to RuntimePipeline."""

    def __init__(
        self,
        llm: LLMPort,
        tools: ToolRouter,
        tracer: TracerPort,
        security: SecurityBroker,
        system_prompt: str,
        memory_turns: int = 8,
        max_tool_rounds: int = 10,
        min_web_searches: int = 1,
        max_web_searches: int = 3,
        session_id: str | None = None,
        request_limits: RequestLimits | None = None,
    ) -> None:
        """Compose the stateless runtime pipeline and bounded session memory."""
        self._llm = llm
        self._memory = ShortTermMemory(max_turns=memory_turns)
        self._pipeline = RuntimePipeline(
            llm=llm,
            tools=tools,
            tracer=tracer,
            security=security,
            config=PipelineConfig(
                system_prompt=system_prompt,
                max_tool_rounds=max_tool_rounds,
                min_web_searches=min_web_searches,
                max_web_searches=max_web_searches,
            ),
            session_id=session_id,
        )
        self._session_usage = UsageStats(
            model=llm.model_name, backend=llm.backend_name
        )
        self._all_citations = []
        self._request_limiter = SessionRequestLimiter(
            request_limits or RequestLimits()
        )

    @property
    def session_usage(self) -> UsageStats:
        """Return cumulative token and latency usage for this session."""
        return self._session_usage

    @property
    def memory(self) -> ShortTermMemory:
        """Expose bounded dialogue memory for UI and evaluation inspection."""
        return self._memory

    def reset(self) -> None:
        """Clear dialogue, citations, and accumulated session usage."""
        self._memory.clear()
        self._session_usage = UsageStats(
            model=self._llm.model_name, backend=self._llm.backend_name
        )
        self._all_citations = []
        self._request_limiter.clear()

    def chat(self, user_text: str) -> AgentTurnResult:
        """Run one turn and commit only finalized dialogue to session memory."""
        checkpoint = self._dialogue_checkpoint()
        self._memory.restore(checkpoint)
        limit_review = self._request_limiter.review(user_text, checkpoint)
        if limit_review is not None:
            return AgentTurnResult(
                assistant_message=(
                    "This request exceeds the session safety budget. Shorten it or "
                    "wait before trying again."
                ),
                security_validation_failed=True,
                security_trace=[SecurityBroker.trace_payload(limit_review)],
                usage=UsageStats(
                    model=self._llm.model_name, backend=self._llm.backend_name
                ),
                backend=self._llm.backend_name,
                model=self._llm.model_name,
                policy_route="security_blocked",
            )
        try:
            result = self._pipeline.run(user_text, checkpoint)
        except Exception:
            self._memory.restore(checkpoint)
            raise

        if result.policy_route != "security_blocked":
            self._memory.restore(checkpoint)
            self._memory.add(Message(role=Role.USER, content=user_text))
            self._memory.add(
                Message(
                    role=Role.ASSISTANT,
                    content=result.assistant_message,
                )
            )
        self._session_usage = self._session_usage.add(result.usage)
        self._all_citations.extend(result.citations)
        return result

    def _dialogue_checkpoint(self) -> list[Message]:
        """Return persistent dialogue with every tool envelope removed."""
        return [
            message
            for message in self._memory.as_list()
            if message.role in {Role.USER, Role.ASSISTANT}
            and not message.tool_calls
        ]
