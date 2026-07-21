# Application orchestration

## At a glance

This layer turns model and tool capabilities into Ollive's bounded workflow. It
owns policy, sequencing, memory, grounding, and dependency composition.

| File | Responsibility |
|---|---|
| `agent.py` | Runs classification, model/tool rounds, grounded submission, tracing, and failure rollback. |
| `config.py` | Resolves repository paths, YAML settings, and environment-backed secrets. |
| `factory.py` | Composes configured ports and adapters into a ready `WellnessAgent`. |
| `grounded_answer.py` | Defines and validates the structured answer contract, then renders exact citations. |
| `guardrails.py` | Semantically classifies each turn and supplies its allowed policy. |
| `memory.py` | Keeps a bounded dialogue history without stale tool evidence. |
| `tools.py` | Declares tool schemas, validates bounds and shapes, and dispatches calls. |
| `__init__.py` | Marks the application namespace. |
| `README.md` | Maps orchestration responsibilities. |

The router sets the boundary before the agent acts; grounding then rejects any
factual answer whose submitted claims do not match retrieved evidence.
