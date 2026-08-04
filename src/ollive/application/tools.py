"""Tool schemas and executors for lookup_kb / search_web."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints, ValidationError

from ollive.domain.models import Citation, ToolCallRequest, ToolResult
from ollive.ports.retriever import RetrieverPort
from ollive.ports.web_search import WebSearchPort

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "lookup_kb",
            "description": (
                "Search the local wellness knowledge base using the application-selected "
                "user-authored evidence query. The application controls the query. You may only "
                "select optional doc_types and top_k."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 20,
                        "description": (
                            "Optional doc_type filters selected only from the provided enum"
                        ),
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of passages to return (default 4)",
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Search configured authoritative domains for wellness evidence. One search "
                "is required after KB lookup; at most two additional searches may target a "
                "remaining material gap."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Web search query",
                        "minLength": 1,
                        "maxLength": 1000,
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max results (default 5)",
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": ["query"],
            },
        },
    },
]


Query = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
DocType = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=100),
]


class LookupKBArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query: Query
    doc_types: list[DocType] | None = Field(default=None, min_length=1, max_length=20)
    top_k: StrictInt | None = Field(default=None, ge=1, le=20)


class SearchWebArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query: Query
    max_results: StrictInt | None = Field(default=None, ge=1, le=10)


class ToolRouter:
    def __init__(
        self,
        retriever: RetrieverPort,
        web_search: WebSearchPort,
        default_top_k: int = 4,
        allowed_doc_types: list[str] | None = None,
    ) -> None:
        """Initialize ToolRouter with its runtime collaborators."""
        self._retriever = retriever
        self._web_search = web_search
        self._default_top_k = default_top_k
        self._allowed_doc_types = allowed_doc_types or retriever.list_doc_types()

    @property
    def schemas(self) -> list[dict[str, Any]]:
        """Return tool schemas constrained by the live document-type enum."""
        # Copy because this enum belongs to one retriever instance; mutating the
        # module template would leak one agent's corpus into another session.
        schemas = deepcopy(TOOL_SCHEMAS)
        doc_types = schemas[0]["function"]["parameters"]["properties"]["doc_types"]
        doc_types["items"]["enum"] = self._allowed_doc_types
        doc_types["description"] = (
            "Optional filters. Select only from this enum; never construct a value. "
            "Omit doc_types to search all documents."
        )
        schemas[0]["function"]["parameters"]["additionalProperties"] = False
        schemas[1]["function"]["parameters"]["additionalProperties"] = False
        return schemas

    def resolve_evidence_query(
        self, current: str, prior_user_text: list[str]
    ) -> tuple[str, bool]:
        """Attach one bounded prior user turn after the LLM selects continuation."""
        if not prior_user_text:
            return current, False
        return "\n".join([prior_user_text[-1], current]), True

    def execute(
        self, call: ToolCallRequest, *, user_query: str | None = None
    ) -> ToolResult:
        """Validate and dispatch one model-requested tool call."""
        try:
            if call.name == "lookup_kb":
                arguments = dict(call.arguments)
                # Bind retrieval to the application-selected evidence query; fallback_query exists
                # only for direct callers that omit user_query.
                fallback_query = arguments.pop("query", None)
                arguments["query"] = user_query or fallback_query
                return self._lookup_kb(
                    call, LookupKBArguments.model_validate(arguments)
                )
            if call.name == "search_web":
                return self._search_web(call, SearchWebArguments.model_validate(call.arguments))
        except ValidationError as exc:
            return self._error(call, "invalid_arguments", exc.errors(include_url=False))
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content=json.dumps({"error": f"Unknown tool: {call.name}"}),
        )

    def _error(self, call: ToolCallRequest, code: str, details: Any) -> ToolResult:
        """Return a stable JSON tool error without raising into the agent loop."""
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content=json.dumps({"error": code, "details": details}, default=str),
        )

    def _lookup_kb(self, call: ToolCallRequest, args: LookupKBArguments) -> ToolResult:
        """Search allowed knowledge documents and return citation-bearing passages."""
        available = set(self._retriever.list_doc_types())
        unknown = sorted(set(args.doc_types or []) - available)
        # Returning the live enum lets the next model round recover without
        # inventing another category or calling a discovery tool.
        if unknown:
            return self._error(
                call,
                "unknown_doc_types",
                {"unknown": unknown, "available": sorted(available)},
            )
        chunks = self._retriever.search(
            args.query, top_k=args.top_k or self._default_top_k, doc_types=args.doc_types
        )
        citations = [c.to_citation() for c in chunks]
        payload = {
            "results": [
                {
                    "citation": cit.marker,
                    "doc_type": cit.doc_type,
                    "title": cit.title,
                    "start_line": cit.line,
                    "end_line": cit.end_line,
                    "descriptor": cit.descriptor,
                    "text": cit.text,
                }
                for cit in citations
            ],
            "available_doc_types": self._retriever.list_doc_types(),
        }
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content=json.dumps(payload, ensure_ascii=False, indent=2),
            citations=citations,
        )

    def _search_web(self, call: ToolCallRequest, args: SearchWebArguments) -> ToolResult:
        """Convert accepted authoritative web results into URL-backed citations."""
        results = self._web_search.search(args.query, max_results=args.max_results or 5)
        # URL hashes provide stable local markers while the original URL remains
        # attached for provenance and UI navigation.
        citations = [
            Citation(
                doc_type="web",
                line=rank,
                descriptor=hashlib.sha256(result["url"].encode("utf-8")).hexdigest()[:12],
                title=result.get("title") or result.get("domain") or "Web source",
                text=result.get("content", ""),
                source_type="web",
                url=result["url"],
                domain=result.get("domain"),
            )
            for rank, result in enumerate(results, start=1)
            if result.get("url") and result.get("content")
        ]
        markers_by_url = {citation.url: citation.marker for citation in citations}
        payload_results = [
            {**result, "citation": markers_by_url.get(result.get("url"))}
            for result in results
        ]
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content=json.dumps({"results": payload_results}, ensure_ascii=False, indent=2),
            citations=citations,
        )
