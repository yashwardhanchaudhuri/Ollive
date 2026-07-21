# Local execution traces

## At a glance

The local tracer appends structured agent events here for debugging without an
external observability service.

| File | Responsibility |
|---|---|
| `traces_YYYYMMDD.jsonl` | Daily records of model calls, tools, usage, and outcomes. |
| `.gitkeep` | Preserves the directory before a trace exists. |
| `README.md` | Explains why these artifacts remain local. |

Traces may contain user text and are ignored by Git. They are not the curated,
versioned evidence stored in `evaluation/runs/`.
