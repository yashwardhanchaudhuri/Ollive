import json

from ollive.adapters.search.tavily_search import TavilyWebSearch
from ollive.application.tools import ToolRouter
from ollive.domain.citations import parse_citations, slugify_descriptor, validate_citations
from ollive.domain.models import Citation, ToolCallRequest


def test_slugify_descriptor():
    """Create stable citation descriptors from evidence text."""
    assert slugify_descriptor("Portion control plays a critical role") == "portion-control-plays-a-critical"


def test_parse_citations():
    """Parse single-line and bounded-line citation markers."""
    text = "Eat mindfully [diet:L9:portion-control-satiety] and move [exercise:L7-L8:cardio-strength]."
    cites = parse_citations(text)
    assert len(cites) == 2
    assert cites[0].doc_type == "diet"
    assert cites[0].line == 9
    assert cites[0].descriptor == "portion-control-satiety"
    assert cites[1].line == 7
    assert cites[1].end_line == 8


def test_validate_citations():
    """Separate retrieved markers from unsupported citation claims."""
    allowed = [
        Citation(doc_type="diet", line=9, descriptor="portion-control-satiety", text="..."),
    ]
    claimed = parse_citations("See [diet:L9:portion-control-satiety] and [diet:L99:fake-thing].")
    valid, invalid = validate_citations(claimed, allowed)
    assert len(valid) == 1
    assert len(invalid) == 1


class FakeTavilyClient:
    def __init__(self):
        """Initialize the fake client with no recorded search call."""
        self.call = None

    def search(self, **kwargs):
        """Record search bounds and return trusted, deceptive, and weak results."""
        self.call = kwargs
        return {
            "results": [
                {
                    "title": "Trusted",
                    "url": "https://www.cdc.gov/sleep/about/index.html",
                    "content": "Adults need regular, sufficient sleep.",
                    "score": 0.9,
                },
                {
                    "title": "Deceptive domain",
                    "url": "https://cdc.gov.example.com/sleep",
                    "content": "Untrusted content",
                    "score": 0.99,
                },
                {
                    "title": "Low relevance",
                    "url": "https://www.cdc.gov/other",
                    "content": "Unrelated content",
                    "score": 0.2,
                },
            ]
        }


class RetrieverStub:
    def list_doc_types(self):
        """Return the single document type exposed by the retriever stub."""
        return ["daily_habits"]


class WebStub:
    def search(self, query, max_results=5):
        """Return one deterministic URL-backed web result."""
        return [
            {
                "title": "CDC sleep guidance",
                "url": "https://www.cdc.gov/sleep/about/index.html",
                "content": "Adults need regular, sufficient sleep.",
                "score": 0.9,
                "domain": "www.cdc.gov",
            }
        ]


def test_tavily_search_enforces_domains_and_relevance_locally():
    """Filter deceptive domains and low-scoring Tavily results locally."""
    client = FakeTavilyClient()
    search = TavilyWebSearch(
        api_key="test",
        trusted_domains=["cdc.gov"],
        min_score=0.5,
        client=client,
    )

    results = search.search("adult sleep duration", max_results=3)

    assert [result["title"] for result in results] == ["Trusted"]
    assert client.call["include_domains"] == ["cdc.gov"]
    assert client.call["search_depth"] == "basic"


def test_web_tool_returns_url_backed_citations():
    """Preserve a trusted web result as a URL-backed citation."""
    router = ToolRouter(
        RetrieverStub(),
        WebStub(),
        allowed_doc_types=["daily_habits"],
    )
    result = router.execute(
        ToolCallRequest(
            id="web",
            name="search_web",
            arguments={"query": "adult sleep duration"},
        )
    )

    assert len(result.citations) == 1
    citation = result.citations[0]
    assert citation.source_type == "web"
    assert citation.url == "https://www.cdc.gov/sleep/about/index.html"
    assert json.loads(result.content)["results"][0]["citation"] == citation.marker
