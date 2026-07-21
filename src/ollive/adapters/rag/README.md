# Local retrieval adapters

## At a glance

This folder turns curated Markdown into searchable paragraph evidence and
exposes that search through the retriever port.

| File | Responsibility |
|---|---|
| `markdown_indexer.py` | Parses KB files, creates citation-aware chunks, embeds them, and persists FAISS artifacts. |
| `local_retriever.py` | Wraps index search behind the application-facing retriever interface. |
| `__init__.py` | Marks the retrieval-adapter namespace. |
| `README.md` | Explains the path from corpus to evidence. |

The indexer excludes the corpus `README.md`, ensuring operational descriptions
cannot appear as wellness evidence. Citation validation remains in the domain
and application layers.
