"""Structured grounded-answer contract and deterministic citation rendering."""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from ollive.domain.models import Citation

SUBMIT_GROUNDED_ANSWER = "submit_grounded_answer"
NO_CITATION = "__NO_CITATION__"
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=700)]
Marker = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=240)]


class GroundedItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    kind: Literal["supported_claim", "evidence_limitation"]
    text: Text
    citation: Marker


class GroundedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    items: list[GroundedItem] = Field(min_length=1, max_length=3)


class GroundedAnswerError(ValueError):
    """The model's structured grounded answer violated the application contract."""


def _unique_markers(citations: list[Citation]) -> list[str]:
    return list(dict.fromkeys(citation.marker for citation in citations))


def build_grounded_answer_schema(citations: list[Citation]) -> dict[str, Any]:
    markers = _unique_markers(citations)
    return {
        "type": "function",
        "function": {
            "name": SUBMIT_GROUNDED_ANSWER,
            "description": (
                "Submit a concise, direct answer with at most three atomic items. The "
                "first item must answer the user's main question or state the precise "
                "evidence gap. Use the fewest items necessary. If you use evidence_limitation, return no more "
                "than two items total: the limitation and at most one directly useful "
                "supported item when a retrieved citation is available. After an evidence gap, include only "
                "an item that supplies a cited decision criterion or action for the "
                "question; accurate background information is not relevant. Do not inventory the retrieved passages. A "
                "supported_claim must select one exact retrieved marker. An "
                f"evidence_limitation must select {NO_CITATION} and contain no advice "
                "or factual explanation. Use at most one evidence_limitation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 3,
                        "items": {
                            "type": "object",
                            "properties": {
                                "kind": {
                                    "type": "string",
                                    "enum": [
                                        "supported_claim",
                                        "evidence_limitation",
                                    ],
                                },
                                "text": {
                                    "type": "string",
                                    "minLength": 1,
                                    "maxLength": 700,
                                },
                                "citation": {
                                    "type": "string",
                                    "enum": [NO_CITATION, *markers],
                                },
                            },
                            "required": ["kind", "text", "citation"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["items"],
                "additionalProperties": False,
            },
        },
    }


def forced_grounded_answer_choice() -> dict[str, Any]:
    return {"type": "function", "function": {"name": SUBMIT_GROUNDED_ANSWER}}


def parse_and_render_grounded_answer(
    arguments: dict[str, Any],
    allowed: list[Citation],
) -> tuple[str, list[Citation]]:
    try:
        answer = GroundedAnswer.model_validate(arguments)
    except ValidationError as exc:
        raise GroundedAnswerError(str(exc)) from exc

    allowed_by_marker = {citation.marker: citation for citation in allowed}
    used: list[Citation] = []
    used_markers: set[str] = set()
    rendered: list[str] = []

    limitation_count = sum(
        item.kind == "evidence_limitation" for item in answer.items
    )
    if limitation_count > 1:
        raise GroundedAnswerError("Use at most one evidence limitation")
    if limitation_count and len(answer.items) > 2:
        raise GroundedAnswerError(
            "An answer with an evidence limitation may use at most two items"
        )

    for item in answer.items:
        if "[" in item.text or "]" in item.text:
            raise GroundedAnswerError(
                "Grounded item text must not contain citation-shaped brackets"
            )
        if item.kind == "evidence_limitation":
            if item.citation != NO_CITATION:
                raise GroundedAnswerError(
                    "Evidence limitations must use the no-citation sentinel"
                )
            rendered.append(item.text)
            continue

        if item.citation == NO_CITATION:
            raise GroundedAnswerError(
                "Supported claims must select a retrieved citation"
            )
        citation = allowed_by_marker.get(item.citation)
        if citation is None:
            raise GroundedAnswerError(
                f"Citation was not retrieved: {item.citation}"
            )
        if item.citation not in used_markers:
            used.append(citation)
            used_markers.add(item.citation)
        rendered.append(f"{item.text} {citation.marker}")

    return "\n\n".join(rendered), used
