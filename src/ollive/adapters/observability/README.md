# Observability adapters

## At a glance

This folder records what the agent does without coupling orchestration to one
telemetry product. All implementations satisfy the tracer port.

| File | Responsibility |
|---|---|
| `factory.py` | Selects a tracer from configuration and applies safe fallback behavior. |
| `local_tracer.py` | Appends structured events under `data/traces/`. |
| `langfuse_tracer.py` | Sends spans to Langfuse and supplies a no-op fallback. |
| `__init__.py` | Marks the observability namespace. |
| `README.md` | Maps tracing implementations to the application boundary. |

Traces are diagnostics, not conversation memory or formal evaluation evidence.
Optional telemetry failures must not prevent a user answer.
