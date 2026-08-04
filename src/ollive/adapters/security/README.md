# Security adapter

## At a glance

This adapter uses an independently configured language model only for constrained
runtime security work. Input and context first receive a typed authority extraction;
application code maps anchored privileged targets and effects to their owning guard.
At input, the original application-owned envelope passes through five specialist
checks in order: direct injection, delimiter/role confusion, Persona/DAN permission,
harmful capability, and individualized medical risk. Each specialist receives one
concise risk definition and its nearest allowed boundary, returns one strict decision
and trust score, and stops the sequence on an owned block. No fused ingress or
semantic-canary turn runs after the medical guard.

The delimiter specialist explicitly covers nine syntax families: XML, JSON,
Markdown, YAML/front matter, fake chat headers, serialized role labels, claimed
begin/end markers, nested or mismatched boundaries, and Unicode/invisible
separators. These are structural categories rather than copied benchmark cases;
the decision still turns on whether nested text is being made executable or falsely
authoritative. Ordinary structured wellness data and explicit transformation remain
inside the allowed boundary.

For an allowed sequence, the final trust score is the lowest score from the completed
checks. A score cannot grant authority or cancel a block. Malformed, contradictory,
or unavailable contracts fail closed.

| File | Responsibility |
|---|---|
| `checks.py` | Defines the ordered stage-specific specialist checks and focused prompts. |
| `llm_security.py` | Runs authority extraction and focused checks, validates contracts, and stops on the first block. |
| `persona.py` | Deterministically blocks persona-mediated attempts to obtain privileged authority. |
| `policy_catalog.py` | Stores reusable semantic authority families, nearest benign boundaries, and classifier weaknesses. |
| `__init__.py` | Marks the security adapter namespace. |
| `README.md` | Explains the independent security-model boundary. |

The separate random output canary in `application/canary.py` remains. It detects a
secret marker leaking from answer generation and is unrelated to the rejected fused
ingress experiment.
