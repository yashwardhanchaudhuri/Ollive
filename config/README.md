# Runtime configuration

## At a glance

Configuration keeps deployable choices outside application code. The factory
reads this folder to assemble the model, prompt, retriever, search, and tracer.

| File | Responsibility |
|---|---|
| `backends.yaml` | Defines backend parameters, the system prompt, KB document types, trusted web domains, and observability. |

Secrets are named here but resolved from environment variables by
`application/config.py`; never write credentials into YAML. A prompt or backend
change can alter behavior without changing Python, so pair it with regression
evaluation.
