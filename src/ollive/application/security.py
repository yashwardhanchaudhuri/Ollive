"""Application-owned enforcement around Security LM verdicts."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any

from ollive.application.canary import OutputCanary
from ollive.domain.models import Citation, Message, ToolResult
from ollive.domain.security import SecurityReview, SecurityStage
from ollive.ports.security import SecurityGatePort

SECURITY_REJECTION_MESSAGE = (
    "I cannot safely process that request within this wellness assistant. "
    "Please rephrase it as a non-clinical wellness question."
)


class SecurityBroker:
    """Ensure no unapproved external runtime data reaches the main pipeline."""

    def __init__(
        self, gate: SecurityGatePort, *, output_canary: OutputCanary | None = None
    ) -> None:
        """Bind the decision port and optional output-canary enforcement."""
        self._gate = gate
        self._output_canary = output_canary

    @property
    def canary_instruction(self) -> str:
        """Return the protected marker instruction for answer-model context."""
        if self._output_canary is None:
            return ""
        return self._output_canary.system_instruction

    def review_canary(self, assistant_text: str) -> SecurityReview | None:
        """Return a deterministic block when the answer leaks the integrity marker."""
        if self._output_canary is None or not self._output_canary.leaked_in(
            assistant_text
        ):
            return None
        return SecurityReview(
            stage=SecurityStage.OUTPUT,
            decision="block",
            reason_code="canary_leak_detected",
            risk_flags=["canary_leak_detected"],
            trust_score=0.0,
            decision_source="canary",
            items=[],
        )

    def review_input(self, user_text: str) -> SecurityReview:
        """Review the current external user message before any main-model call."""
        return self._gate.review(
            stage=SecurityStage.INPUT,
            payload=self._untrusted_text_payload(user_text, source="current_user"),
        )

    def review_context(
        self, user_text: str, history: list[Message]
    ) -> SecurityReview:
        """Review the assembled conversational context for composed intent."""
        prior_history = history
        if (
            history
            and history[-1].role.value == "user"
            and history[-1].content == user_text
        ):
            prior_history = history[:-1]
        if not prior_history:
            return SecurityReview(
                stage=SecurityStage.CONTEXT,
                decision="allow",
                reason_code="no_prior_context",
                risk_flags=[],
                trust_score=1.0,
                items=[],
                decision_source="application_policy",
            )
        return self._gate.review(
            stage=SecurityStage.CONTEXT,
            payload={
                "current": self._untrusted_text_payload(
                    user_text, source="current_user"
                ),
                "history": [
                    {
                        "role": message.role.value,
                        **self._untrusted_text_payload(
                            message.content,
                            source=(
                                "prior_user"
                                if message.role.value == "user"
                                else "prior_assistant_output"
                            ),
                        ),
                    }
                    for message in prior_history
                ],
            },
        )

    def filter_evidence(
        self,
        *,
        user_text: str,
        tool_name: str,
        citations: list[Citation],
        raw_metadata: str = "",
    ) -> tuple[list[Citation], SecurityReview]:
        """Return only evidence items explicitly approved by the Security LM."""
        item_ids = [citation.marker for citation in citations]
        review = self._gate.review(
            stage=SecurityStage.EVIDENCE,
            item_ids=item_ids,
            payload={
                "user_text": user_text,
                "tool_name": tool_name,
                "items": [self._citation_payload(citation) for citation in citations],
                "metadata": raw_metadata[:2000] if not citations else "",
            },
        )
        approved = review.approved_item_ids
        return [c for c in citations if c.marker in approved], review

    def review_combined_evidence(
        self, user_text: str, citations: list[Citation]
    ) -> SecurityReview:
        """Check cross-source meaning before the main model sees the full set."""
        item_ids = [citation.marker for citation in citations]
        return self._gate.review(
            stage=SecurityStage.COMBINED_EVIDENCE,
            item_ids=item_ids,
            payload={
                "user_text": user_text,
                "items": [self._citation_payload(citation) for citation in citations],
            },
        )

    def review_output(
        self,
        *,
        user_text: str,
        route: str,
        assistant_text: str,
        citations: list[Citation],
        tool_trace: list[dict[str, Any]],
    ) -> SecurityReview:
        """Review the full lineage and proposed response before rendering."""
        return self._gate.review(
            stage=SecurityStage.OUTPUT,
            payload={
                "user_text": user_text,
                "route": route,
                "approved_evidence": [
                    self._citation_payload(citation) for citation in citations
                ],
                "tool_trace": tool_trace,
                "proposed_response": assistant_text,
            },
        )

    def safe_tool_result(
        self, result: ToolResult, citations: list[Citation]
    ) -> ToolResult:
        """Rebuild a tool result from approved typed evidence only."""
        payload = {
            "results": [self._citation_payload(citation) for citation in citations]
        }
        return ToolResult(
            tool_call_id=result.tool_call_id,
            name=result.name,
            content=json.dumps(payload, ensure_ascii=False, indent=2),
            citations=citations,
        )

    @staticmethod
    def trace_payload(review: SecurityReview) -> dict[str, Any]:
        """Return a trace-safe summary without exposing classifier reasoning."""
        return {
            "stage": review.stage.value,
            "decision": review.decision,
            "reason_code": review.reason_code,
            "risk_flags": review.risk_flags,
            "decision_source": review.decision_source,
            "trust_score": review.trust_score,
            "items": [item.model_dump() for item in review.items],
            "checks": [check.model_dump() for check in review.checks],
            "authority": (
                review.authority.model_dump() if review.authority is not None else None
            ),
        }

    @staticmethod
    def _canonical_inspection_text(text: str) -> str:
        """Normalize invisible formatting without deleting semantic punctuation."""
        normalized = unicodedata.normalize("NFKC", text).replace("\r\n", "\n")
        visible = "".join(
            character
            for character in normalized
            if unicodedata.category(character) != "Cf"
        )
        return " ".join(visible.split())

    @classmethod
    def _untrusted_text_payload(cls, text: str, *, source: str) -> dict[str, Any]:
        """Build an application-authored envelope whose provenance text cannot alter."""
        review_text = cls._canonical_inspection_text(text)
        return {
            "provenance": {
                "source": source,
                "authority": "untrusted",
                "content_type": "text",
            },
            "review_text": review_text,
            "original_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "original_length": len(text),
            "normalization_changed": review_text != text,
        }

    @staticmethod
    def _citation_payload(citation: Citation) -> dict[str, Any]:
        """Serialize evidence as data without provider-specific tool envelopes."""
        return {
            "item_id": citation.marker,
            "source_type": citation.source_type,
            "title": citation.title,
            "text": citation.text,
            "url": citation.url,
            "domain": citation.domain,
        }
