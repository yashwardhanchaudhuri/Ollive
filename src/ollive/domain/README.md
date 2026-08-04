# Domain contracts

## At a glance

The domain is Ollive's infrastructure-free center. Its types and citation rules
can be tested without a model, database, network, or UI.

| File | Responsibility |
|---|---|
| `models.py` | Defines messages, chunks, citations, tool requests/results, usage, and agent-turn results. |
| `security.py` | Defines strict security stages, authority assessments, per-check and per-item results, bounded trust scores, decision sources, and aggregate reviews. |
| `citations.py` | Creates citation descriptors, parses markers, and validates markers against retrieved bounds. |
| `__init__.py` | Marks the domain namespace. |
| `README.md` | Explains the innermost dependency boundary. |

Provider-specific payloads must be converted into these types by adapters rather
