#!/usr/bin/env python3
"""Build / rebuild the local FAISS KB index."""

from __future__ import annotations

from ollive.application.config import load_config
from ollive.application.factory import build_retriever


def main() -> None:
    """Rebuild the configured KB index and print its available document types."""
    cfg = load_config()
    retriever = build_retriever(cfg, rebuild=True)
    types = retriever.list_doc_types()
    print(f"Indexed doc_types ({len(types)}): {', '.join(types)}")


if __name__ == "__main__":
    main()
