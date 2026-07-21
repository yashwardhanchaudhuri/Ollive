"""Web search port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class WebSearchPort(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Return external results for a bounded web query."""
        ...
