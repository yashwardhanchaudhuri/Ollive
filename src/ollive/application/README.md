# Application orchestration

## At a glance

This layer turns model and tool capabilities into Ollive's bounded workflow. It
owns policy, sequencing, memory, grounding, and dependency composition.

| File | Responsibility |
|---|---|
| `agent.py` | Runs classification, model/tool rounds, grounded submission, tracing, and failure rollback. |
| `config.py` | Resolves repository paths, YAML settings, and environment-backed secrets. |
| `factory.py` | Composes configured ports and adapters into a ready `WellnessAgent`. |
| `grounded_answer.py` | Defines the structured answer contract, verifies claim-to-source entailment, then renders exact citations. |
| `guardrails.py` | Runs one policy-routing call, then maps medical urgency to application-owned boundary text. |
| `memory.py` | Keeps a bounded dialogue history without stale tool evidence. |
| `tools.py` | Declares tool schemas, validates bounds and shapes, and dispatches calls. |
| `__init__.py` | Marks the application namespace. |
| `README.md` | Maps orchestration responsibilities. |

A focused LLM call first decides whether the current turn depends on prior dialogue; the policy router then selects domain, depth, and explicit web requirements. Grounded turns bind retrieval either to the current user text or to the immediately preceding user turn plus the current text. When continuation is selected, grounded answer generation receives up to the three most recent user turns, while assistant prose and prior tool evidence remain excluded. Grounding then enforces structured items, bounded answer length, current-turn marker provenance, and an isolated claim-to-source entailment check before rendering.
