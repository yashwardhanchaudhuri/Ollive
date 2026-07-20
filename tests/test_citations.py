from ollive.domain.citations import parse_citations, slugify_descriptor, validate_citations
from ollive.domain.models import Citation


def test_slugify_descriptor():
    assert slugify_descriptor("Portion control plays a critical role") == "portion-control-plays-a-critical"


def test_parse_citations():
    text = "Eat mindfully [diet:L9:portion-control-satiety] and move [exercise:L7-L8:cardio-strength]."
    cites = parse_citations(text)
    assert len(cites) == 2
    assert cites[0].doc_type == "diet"
    assert cites[0].line == 9
    assert cites[0].descriptor == "portion-control-satiety"
    assert cites[1].line == 7
    assert cites[1].end_line == 8


def test_validate_citations():
    allowed = [
        Citation(doc_type="diet", line=9, descriptor="portion-control-satiety", text="..."),
    ]
    claimed = parse_citations("See [diet:L9:portion-control-satiety] and [diet:L99:fake-thing].")
    valid, invalid = validate_citations(claimed, allowed)
    assert len(valid) == 1
    assert len(invalid) == 1
