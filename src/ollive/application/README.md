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
| `guardrails.py` | Semantically classifies each turn and supplies its allowed route, context scope, and response-depth policy. |
| `memory.py` | Keeps a bounded dialogue history without stale tool evidence. |
| `tools.py` | Declares tool schemas, validates bounds and shapes, and dispatches calls. |
| `__init__.py` | Marks the application namespace. |
| `README.md` | Maps orchestration responsibilities. |

The router sets the boundary and context scope before the agent acts. A topic-reset turn is grounded only against its current user message; a dependent follow-up receives the recent user-authored context needed to resolve it. Grounding then enforces structured items, bounded answer length, and current-turn citation-marker provenance; independent claim-to-source entailment review remains a separate safeguard.
