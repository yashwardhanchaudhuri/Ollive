import pytest

from ollive.application.grounded_answer import (
    GroundedAnswerError,
    NO_CITATION,
    build_grounded_answer_schema,
    parse_and_render_grounded_answer,
)
from ollive.domain.models import Citation


@pytest.fixture
def citations():
    return [
        Citation(
            doc_type="daily_habits",
            line=11,
            descriptor="sleep-hygiene-is-among-the",
            text="Maintain a regular sleep schedule.",
        ),
        Citation(
            doc_type="daily_habits",
            line=9,
            descriptor="a-healthy-morning-routine-sets",
            text="Wake at a consistent time.",
        ),
    ]


def test_schema_constrains_citations_to_retrieved_markers(citations):
    schema = build_grounded_answer_schema(citations)
    marker_enum = schema["function"]["parameters"]["properties"]["items"]["items"][
        "properties"
    ]["citation"]["enum"]
    assert marker_enum == [NO_CITATION, *[citation.marker for citation in citations]]
    assert schema["function"]["parameters"]["additionalProperties"] is False
    assert schema["function"]["parameters"]["properties"]["items"]["maxItems"] == 3


def test_renderer_adds_exact_markers(citations):
    text, used = parse_and_render_grounded_answer(
        {
            "items": [
                {
                    "kind": "supported_claim",
                    "text": "Maintain a regular sleep schedule.",
                    "citation": citations[0].marker,
                },
                {
                    "kind": "supported_claim",
                    "text": "Wake at a consistent time.",
                    "citation": citations[1].marker,
                },
            ]
        },
        citations,
    )
    assert text == (
        f"Maintain a regular sleep schedule. {citations[0].marker}\n\n"
        f"Wake at a consistent time. {citations[1].marker}"
    )
    assert used == citations


def test_limitations_only_are_allowed_without_fabricated_citations(citations):
    text, used = parse_and_render_grounded_answer(
        {
            "items": [
                {
                    "kind": "evidence_limitation",
                    "text": (
                        "The retrieved knowledge base does not establish one "
                        "universal value."
                    ),
                    "citation": NO_CITATION,
                }
            ]
        },
        citations,
    )
    assert text.startswith("The retrieved knowledge base")
    assert used == []


@pytest.mark.parametrize(
    "arguments",
    [
        {"items": []},
        {
            "items": [
                {
                    "kind": "supported_claim",
                    "text": "Claim",
                    "citation": "[daily_habits:L999:fake]",
                }
            ]
        },
        {
            "items": [
                {
                    "kind": "supported_claim",
                    "text": (
                        "Typed marker "
                        "[daily_habits:L11:sleep-hygiene-is-among-the]"
                    ),
                    "citation": "[daily_habits:L11:sleep-hygiene-is-among-the]",
                }
            ]
        },
        {
            "items": [
                {
                    "kind": "evidence_limitation",
                    "text": "Not established.",
                    "citation": "[daily_habits:L11:sleep-hygiene-is-among-the]",
                }
            ]
        },
        {
            "items": [
                {
                    "kind": "supported_claim",
                    "text": "Claim",
                    "citation": NO_CITATION,
                }
            ]
        },
        {"items": [], "unexpected": True},
    ],
)
def test_renderer_rejects_invalid_shapes_and_markers(citations, arguments):
    with pytest.raises(GroundedAnswerError):
        parse_and_render_grounded_answer(arguments, citations)


def test_schema_allows_limitation_when_no_source_is_found():
    schema = build_grounded_answer_schema([])
    marker_enum = schema["function"]["parameters"]["properties"]["items"][
        "items"
    ]["properties"]["citation"]["enum"]
    assert marker_enum == [NO_CITATION]

    text, used = parse_and_render_grounded_answer(
        {
            "items": [
                {
                    "kind": "evidence_limitation",
                    "text": "The available sources do not establish this detail.",
                    "citation": NO_CITATION,
                }
            ]
        },
        [],
    )
    assert text == "The available sources do not establish this detail."
    assert used == []
