# Application orchestration

## At a glance

This layer turns model and tool capabilities into Ollive's bounded workflow. It
owns policy, sequencing, memory, grounding, and dependency composition.

| File | Responsibility |
|---|---|
| `agent.py` | Owns session memory and delegates immutable turn snapshots to `RuntimePipeline`. |
| `canary.py` | Creates and detects an opaque output marker that signals prompt-context disclosure. |
| `config.py` | Resolves repository paths, YAML settings, and environment-backed secrets. |
| `factory.py` | Composes configured ports and adapters into a ready `WellnessAgent`. |
| `grounded_answer.py` | Defines the structured answer contract, verifies claim-to-source entailment, then renders exact citations. |
| `guardrails.py` | Runs one policy-routing call, then maps medical urgency to application-owned boundary text. |
| `memory.py` | Keeps a bounded dialogue history without stale tool evidence. |
| `request_limits.py` | Enforces per-session request frequency, current-message size, and accumulated-context budgets before model calls. |
| `pipeline/` | Contains explicit ingress, routing, evidence, grounded, medical, non-grounded, and output stages. |
| `security.py` | Creates immutable untrusted-text envelopes, shortcuts empty history, labels decision sources, enforces Security LM results, and rebuilds approved evidence payloads. |
| `tools.py` | Declares tool schemas, validates bounds and shapes, and dispatches calls. |
| `__init__.py` | Marks the application namespace. |
| `README.md` | Maps orchestration responsibilities. |

`WellnessAgent` owns only bounded session state, including the local sliding request window. It applies request and context admission before delegating accepted traffic.

`WellnessAgent` contains no routing, tool, or validation logic. A separate Security LM
extracts authority semantics, then runs the ordered checks declared for the current
stage. Application code stops on the first block and uses the weakest per-check trust
score when all checks allow. Application-authored provenance—not delimiters inside
content—defines whether text came from the user, history, or another source.

Every grounded wellness turn then performs KB lookup and at least one web search; each
source result and their combined evidence set are approved before entering answer-model
context. Grounding enforces structured items, current-turn marker provenance, and isolated
claim entailment. Final output integrity, harm, and medical checks run before rendering.
Application code—not either model—enforces every transition and the three-search cap.
