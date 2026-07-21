"""RetrieverPort adapter over MarkdownParagraphIndexer."""

from __future__ import annotations

from pathlib import Path

from ollive.adapters.rag.markdown_indexer import MarkdownParagraphIndexer
from ollive.domain.models import Chunk
from ollive.ports.retriever import RetrieverPort


class LocalRetriever(RetrieverPort):
    def __init__(self, indexer: MarkdownParagraphIndexer) -> None:
        """Initialize LocalRetriever with its runtime collaborators."""
        self._indexer = indexer
        self._indexer.load()

    @classmethod
    def from_paths(
        cls,
        kb_dir: Path,
        index_dir: Path,
        embedder: str,
        rebuild: bool = False,
    ) -> "LocalRetriever":
        """Load the index, rebuilding it only when explicitly requested."""
        indexer = MarkdownParagraphIndexer(kb_dir, index_dir, embedder)
        # Index files are derived caches. Rebuild only on explicit request or first
        # use so ordinary agent construction does not repeatedly embed the corpus.
        if rebuild or not (index_dir / "faiss.index").exists():
            indexer.persist()
        else:
            indexer.load()
        return cls(indexer)

    def search(
        self,
        query: str,
        top_k: int = 4,
        doc_types: list[str] | None = None,
    ) -> list[Chunk]:
        """Delegate a bounded semantic search to the Markdown index."""
        return self._indexer.search(query, top_k=top_k, doc_types=doc_types)

    def list_doc_types(self) -> list[str]:
        """Return the exact document-type enum present in the index."""
        return self._indexer.list_doc_types()
