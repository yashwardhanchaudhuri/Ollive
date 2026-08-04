# Runtime pipeline

## At a glance

This package owns the ordered runtime state machine. Each module has one stage-level
responsibility, and only `RuntimePipeline` composes transitions.

| File | Responsibility |
|---|---|
| `contracts.py` | Defines immutable bounds and typed per-turn state. |
| `ingress.py` | Requires typed authority extraction and security approval for current input and composed context before routing. |
| `routing.py` | Selects route, context, evidence query, and answer messages. |
| `evidence.py` | Executes tools, enforces call counts, gates results, and rebuilds safe payloads. |
| `grounded.py` | Executes the bounded KB/web loop, evidence gates, and grounded-answer contract. |
| `medical.py` | Produces the application-owned medical boundary. |
| `non_grounded.py` | Generates tool-free conversation, clarification, and refusal routes. |
| `output.py` | Validates citations and enforces final Security LM alignment. |
| `runtime.py` | Composes stages in the only permitted order. |
| `__init__.py` | Exposes the pipeline facade and contracts. |
| `README.md` | Maps stage ownership and trust boundaries. |

Conversation memory is intentionally outside this package. The public
`WellnessAgent` owns session state and delegates each immutable history snapshot to
`RuntimePipeline`.
