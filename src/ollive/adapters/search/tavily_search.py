"""Tavily web search adapter."""

from __future__ import annotations

from typing import Any

from ollive.ports.web_search import WebSearchPort


class TavilyWebSearch(WebSearchPort):
    def __init__(self, api_key: str, max_results: int = 5) -> None:
        if not api_key:
            raise ValueError("TAVILY_API_KEY is required for search_web")
        from tavily import TavilyClient

        self._client = TavilyClient(api_key=api_key)
        self._max_results = max_results

    def search(self, query: str, max_results: int | None = None) -> list[dict[str, Any]]:
        n = max_results or self._max_results
        resp = self._client.search(query=query, max_results=n)
        results = []
        for item in resp.get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score"),
                }
            )
        return results


class NullWebSearch(WebSearchPort):
    """Fallback when Tavily key is missing — returns empty results."""

    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        return [
            {
                "title": "web_search_unavailable",
                "url": "",
                "content": (
                    f"Web search is unavailable (missing API key). Query was: {query}"
                ),
                "score": 0,
            }
        ]
