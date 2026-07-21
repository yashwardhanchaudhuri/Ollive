# Generated retrieval index

## At a glance

The Markdown indexer writes its local search cache here. The authoritative
source remains `assignment_kb/`.

| File | Responsibility |
|---|---|
| `faiss.index` | Stores embedding vectors for similarity search. |
| `chunks.pkl` | Maps vectors back to text and citation metadata. |
| `meta.json` | Records the embedder, chunk count, and document types. |
| `.gitkeep` | Preserves the directory in a fresh checkout. |
| `README.md` | Documents this generated-artifact boundary. |

Use `scripts/build_index.py` after corpus or embedding changes. Generated files
can be deleted and rebuilt.
