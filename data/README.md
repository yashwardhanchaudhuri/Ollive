# Local runtime data

## At a glance

This folder separates generated runtime state from reproducible source inputs.
The index is rebuildable; traces support local debugging.

| Child folder | Responsibility |
|---|---|
| `indexes/` | Generated FAISS vectors and chunk metadata for local retrieval. |
| `traces/` | Generated JSONL records from agent execution. |

Generated contents are ignored by Git. Reviewable evaluation evidence belongs
under `evaluation/`, not here.
