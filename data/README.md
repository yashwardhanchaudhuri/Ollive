# Local runtime data

## At a glance

This folder separates generated runtime state from reproducible source inputs.
The index is rebuildable; traces support local debugging.

| Child folder | Responsibility |
|---|---|
| `indexes/` | Generated FAISS vectors and chunk metadata for local retrieval. |
| `traces/` | Generated JSONL records from agent execution. |
| `vllm.log` | Ignored server log written by the repository-root `run_ollive.sh` launcher when it starts local Qwen. |

Generated contents are ignored by Git. Reviewable evaluation evidence belongs
under `evaluation/`, not here.
