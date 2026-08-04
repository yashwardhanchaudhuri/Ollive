# Infrastructure adapters

## At a glance

Adapters connect Ollive's stable port interfaces to concrete libraries and
services. Application code selects them through the factory rather than
depending on vendors directly.

| Entry | Responsibility |
|---|---|
| `__init__.py` | Marks the adapter namespace. |
| `llm/` | Implements model inference clients. |
| `rag/` | Implements local indexing and retrieval. |
| `search/` | Implements bounded external web search. |
| `security/` | Converts an independently configured model into constrained, fail-closed security verdicts. |
| `observability/` | Implements local and hosted tracing. |
| `README.md` | Explains the infrastructure boundary. |
New integrations should implement an existing port before factory wiring.

