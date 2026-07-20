"""Paragraph-level markdown indexer with doc_type metadata."""

from __future__ import annotations

import json
import pickle
import re
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from ollive.domain.citations import slugify_descriptor
from ollive.domain.models import Chunk


def doc_type_from_filename(path: Path) -> str:
    """01_Diet.md -> diet"""
    stem = path.stem
    stem = re.sub(r"^\d+_", "", stem)
    return stem.lower().replace(" ", "_")


def _is_metadata_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if s.startswith("#"):
        return True
    if s.startswith("*") and s.endswith("*") and not s.startswith("* "):
        return True
    return False


def split_paragraphs(text: str) -> list[tuple[int, int, str]]:
    """Return (start_line, end_line, paragraph_text) 1-indexed."""
    lines = text.splitlines()
    paragraphs: list[tuple[int, int, str]] = []
    buf: list[str] = []
    start: int | None = None

    def flush(end_line: int) -> None:
        nonlocal buf, start
        if buf and start is not None:
            para = "\n".join(buf).strip()
            if para:
                paragraphs.append((start, end_line, para))
        buf = []
        start = None

    for i, line in enumerate(lines, start=1):
        if _is_metadata_line(line) and not buf:
            continue
        if line.strip() == "":
            flush(i - 1)
            continue
        if start is None:
            start = i
        buf.append(line)

    flush(len(lines))
    return paragraphs


def extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


class MarkdownParagraphIndexer:
    def __init__(
        self,
        kb_dir: Path,
        index_dir: Path,
        embedder_name: str = "BAAI/bge-small-en-v1.5",
    ) -> None:
        self.kb_dir = kb_dir
        self.index_dir = index_dir
        self.embedder_name = embedder_name
        self._model: SentenceTransformer | None = None
        self.chunks: list[Chunk] = []
        self._index: faiss.IndexFlatIP | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.embedder_name)
        return self._model

    def build(self) -> list[Chunk]:
        md_files = sorted(self.kb_dir.glob("*.md"))
        chunks: list[Chunk] = []
        descriptor_counts: dict[str, int] = {}

        for path in md_files:
            text = path.read_text(encoding="utf-8")
            doc_type = doc_type_from_filename(path)
            title = extract_title(text, path.stem)
            for start, end, para in split_paragraphs(text):
                base = slugify_descriptor(para)
                key = f"{doc_type}:{base}"
                n = descriptor_counts.get(key, 0)
                descriptor_counts[key] = n + 1
                descriptor = base if n == 0 else f"{base}-{n + 1}"
                chunk_id = f"{doc_type}:L{start}:{descriptor}"
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        doc_id=path.name,
                        doc_type=doc_type,
                        title=title,
                        start_line=start,
                        end_line=end,
                        descriptor=descriptor,
                        text=para,
                    )
                )
        self.chunks = chunks
        return chunks

    def _embed(self, texts: list[str]) -> np.ndarray:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return np.asarray(vectors, dtype=np.float32)

    def persist(self) -> None:
        if not self.chunks:
            self.build()
        self.index_dir.mkdir(parents=True, exist_ok=True)
        embeddings = self._embed([c.text for c in self.chunks])
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        faiss.write_index(index, str(self.index_dir / "faiss.index"))
        with (self.index_dir / "chunks.pkl").open("wb") as f:
            pickle.dump(self.chunks, f)
        meta = {
            "embedder": self.embedder_name,
            "n_chunks": len(self.chunks),
            "doc_types": sorted({c.doc_type for c in self.chunks}),
        }
        (self.index_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        self._index = index

    def load(self) -> None:
        index_path = self.index_dir / "faiss.index"
        chunks_path = self.index_dir / "chunks.pkl"
        if not index_path.exists() or not chunks_path.exists():
            self.persist()
            return
        self._index = faiss.read_index(str(index_path))
        with chunks_path.open("rb") as f:
            self.chunks = pickle.load(f)

    def search(
        self,
        query: str,
        top_k: int = 4,
        doc_types: list[str] | None = None,
    ) -> list[Chunk]:
        if self._index is None or not self.chunks:
            self.load()
        assert self._index is not None

        q = self._embed([query])
        # Over-fetch then filter by doc_type for cross-doc control
        fetch_k = min(len(self.chunks), max(top_k * 5, top_k))
        scores, indices = self._index.search(q, fetch_k)
        results: list[Chunk] = []
        allowed = {d.lower() for d in doc_types} if doc_types else None
        for idx in indices[0]:
            if idx < 0:
                continue
            chunk = self.chunks[int(idx)]
            if allowed and chunk.doc_type not in allowed:
                continue
            results.append(chunk)
            if len(results) >= top_k:
                break
        return results

    def list_doc_types(self) -> list[str]:
        if not self.chunks:
            self.load()
        return sorted({c.doc_type for c in self.chunks})
