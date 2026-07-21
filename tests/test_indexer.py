from pathlib import Path

from ollive.adapters.rag.markdown_indexer import (
    MarkdownParagraphIndexer,
    doc_type_from_filename,
    split_paragraphs,
)


ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "assignment_kb"


def test_doc_type_from_filename():
    """Derive normalized document types from numbered KB filenames."""
    assert doc_type_from_filename(Path("01_Diet.md")) == "diet"
    assert doc_type_from_filename(Path("08_Natural_Supplements.md")) == "natural_supplements"


def test_split_paragraphs_diet():
    """Split evidence paragraphs while preserving their source line bounds."""
    text = (KB / "01_Diet.md").read_text(encoding="utf-8")
    paras = split_paragraphs(text)
    assert len(paras) >= 5
    start, end, body = paras[0]
    assert start >= 5  # after title/subtitle
    assert "Diet forms the cornerstone" in body


def test_build_chunks_without_embeddings(tmp_path):
    """Build unique citation-aware chunks without loading an embedding model."""
    indexer = MarkdownParagraphIndexer(KB, tmp_path, embedder_name="unused")
    chunks = indexer.build()
    assert len(chunks) > 20
    types = {c.doc_type for c in chunks}
    assert "diet" in types
    assert "exercise" in types
    # Descriptors unique per doc_type+descriptor
    keys = [(c.doc_type, c.descriptor) for c in chunks]
    assert len(keys) == len(set(keys))
    assert "readme" not in types
