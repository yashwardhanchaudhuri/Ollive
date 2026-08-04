"""Tavily web search adapter."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from ollive.ports.web_search import WebSearchPort


class TavilyWebSearch(WebSearchPort):
    def __init__(
        self,
        api_key: str,
        max_results: int = 5,
        trusted_domains: list[str] | None = None,
        min_score: float = 0.5,
        client: Any | None = None,
    ) -> None:
        """Initialize TavilyWebSearch with its runtime collaborators."""
        if not api_key:
            raise ValueError("TAVILY_API_KEY is required for search_web")
        if not trusted_domains:
            raise ValueError("trusted_domains is required for search_web")
        if client is None:
            from tavily import TavilyClient

            client = TavilyClient(api_key=api_key)
        self._client = client
        self._max_results = max_results
        self._trusted_domains = [domain.lower().lstrip(".") for domain in trusted_domains]
        self._min_score = min_score

    def _is_trusted_url(self, url: str) -> bool:
        """Verify URL scheme and hostname against the domain allowlist."""
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        return parsed.scheme in {"http", "https"} and any(
            host == domain or host.endswith(f".{domain}")
            for domain in self._trusted_domains
        )

    def search(self, query: str, max_results: int | None = None) -> list[dict[str, Any]]:
        """Search allowlisted domains and discard off-domain or weak results."""
        n = min(max_results or self._max_results, self._max_results)
        resp = self._client.search(
            query=query,
            max_results=n,
            include_domains=self._trusted_domains,
            search_depth="advanced",
            chunks_per_source=3,
        )
        results = []
        for item in resp.get("results", []):
        # Recheck provider output locally: include_domains is a request hint, not a
        # sufficient defense against deceptive subdomains or malformed URLs.
            url = item.get("url", "")
            score = item.get("score")
            if not self._is_trusted_url(url):
                continue
            if score is not None and float(score) < self._min_score:
                continue
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": url,
                    "content": item.get("content", ""),
                    "score": score,
                    "domain": (urlparse(url).hostname or "").lower(),
                }
            )
        return results
