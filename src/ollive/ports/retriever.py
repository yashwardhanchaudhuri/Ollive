"""Retriever port for local KB lookup."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ollive.domain.models import Chunk


class RetrieverPort(ABC):
    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 4,
        doc_types: list[str] | None = None,
    ) -> list[Chunk]: ...

    @abstractmethod
    def list_doc_types(self) -> list[str]: ...
