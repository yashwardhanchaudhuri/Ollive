"""Top-level runtime pipeline composition and stage ordering."""

from __future__ import annotations

from ollive.application.guardrails import TurnKind
from ollive.application.pipeline.contracts import PipelineConfig, TurnState
from ollive.application.pipeline.evidence import EvidenceStage
from ollive.application.pipeline.grounded import GroundedStage
from ollive.application.pipeline.ingress import IngressStage
from ollive.application.pipeline.medical import MedicalStage
from ollive.application.pipeline.non_grounded import NonGroundedStage
from ollive.application.pipeline.output import OutputStage
from ollive.application.pipeline.routing import RoutingStage
from ollive.application.security import SECURITY_REJECTION_MESSAGE, SecurityBroker
from ollive.application.tools import ToolRouter
from ollive.domain.models import AgentTurnResult, Message
from ollive.ports.llm import LLMPort
from ollive.ports.tracer import TracerPort


class RuntimePipeline:
    """Run explicit, fail-closed stages for one approved English turn."""

    def __init__(
        self,
        *,
        llm: LLMPort,
        tools: ToolRouter,
        tracer: TracerPort,
        security: SecurityBroker,
        config: PipelineConfig,
        session_id: str | None = None,
    ) -> None:
        """Compose stages once while retaining no conversation state."""
        self._llm = llm
        self._tracer = tracer
        self._session_id = session_id
        self._ingress = IngressStage(security)
        self._routing = RoutingStage(llm=llm, tools=tools, config=config)
        self._medical = MedicalStage(llm=llm, tracer=tracer)
        self._non_grounded = NonGroundedStage(llm=llm, tracer=tracer)
        evidence = EvidenceStage(
            tools=tools,
            security=security,
            tracer=tracer,
            config=config,
        )
        self._grounded = GroundedStage(
            llm=llm,
            tools=tools,
            tracer=tracer,
            evidence=evidence,
            config=config,
        )
        self._output = OutputStage(security=security, tracer=tracer)

    def run(
        self, user_text: str, history: list[Message]
    ) -> AgentTurnResult:
        """Execute stages in the only permitted runtime order."""
        state = TurnState.begin(
            user_text=user_text,
            history=history,
            model=self._llm.model_name,
            backend=self._llm.backend_name,
        )
        if not self._ingress.run(state):
            state.assistant_text = SECURITY_REJECTION_MESSAGE
            state.security_validation_failed = True
            self._trace_blocked(state)
            return state.result(route="security_blocked")

        self._routing.run(state)
        with self._tracer.start_trace(
            name="wellness_turn",
            metadata={"backend": state.backend, "model": state.model},
            session_id=self._session_id,
        ):
            self._trace_security_events(state)
            policy = state.require_policy()
            if policy.kind is TurnKind.MEDICAL:
                self._medical.run(state)
                self._output.run(state, validate_grounding=False)
            elif policy.require_tools:
                self._grounded.run(state)
                self._output.run(state, validate_grounding=True)
            else:
                self._non_grounded.run(state)
                self._output.run(state, validate_grounding=True)
            self._tracer.flush()
        return state.result()

    def _trace_blocked(self, state: TurnState) -> None:
        """Record ingress rejection without exposing the blocked input downstream."""
        with self._tracer.start_trace(
            name="security_blocked_turn",
            metadata={"backend": state.backend, "model": state.model},
            session_id=self._session_id,
        ):
            self._trace_security_events(state)
            self._tracer.flush()

    def _trace_security_events(self, state: TurnState) -> None:
        """Record security summaries already accumulated by preceding stages."""
        for event in state.security_trace:
            self._tracer.log_span(
                name=f"security:{event['stage']}", output=event
            )
