# Runtime configuration

## At a glance

Configuration keeps deployable choices outside application code. The factory
reads this folder to assemble the answer model, independent Security LM, prompt, retriever, search, and tracer. The committed default uses local JSONL observability; Langfuse is an optional runtime provider.

| File | Responsibility |
|---|---|
| `backends.yaml` | Separates answer backends, pipeline bounds, Security LM settings, KB types, trusted domains, and observability. |

Secrets are named here but resolved from environment variables by
`application/config.py`; never write credentials into YAML. A prompt or backend
change can alter behavior without changing Python, so pair it with regression
evaluation.


The `security` section is not an optional observability feature. Production construction
fails when it is disabled or lacks a model. The Security LM uses its own adapter and
may share local weights with the answer model. Credentials and the model identifier
are resolved only from the named environment variables. `max_input_chars` is a
positive adapter-side fallback ceiling; oversized serialized Security LM payloads
fail closed instead of overflowing the model context window.

The `request_limits` section is the earlier runtime admission boundary: a local
per-session sliding request window, current-message cap, and accumulated-context cap.
The committed values are 12 requests per 60 seconds, 20,000 characters per message,
and 48,000 across bounded dialogue. Distributed deployments still need an upstream
identity-aware limiter shared across workers.

The `pipeline` section owns tool-round and one-to-three web-search bounds. Its minimum is validated as at least one, so no configuration path can disable required web evidence.
