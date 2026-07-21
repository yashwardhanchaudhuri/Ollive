# Evaluated change ledger

This ledger describes the dirty source snapshot identified by the combined manifest. It is a behavioral audit, not a claim that every change is fully exercised by the 72 single-turn cases.

| Boundary | Change evaluated | Intended effect | Coverage caveat |
|---|---|---|---|
| Routing | Wellness grounding is application-owned; router emits domain, depth, and explicit-web intent | Prevent the model from disabling evidence | Structural route/tool checks cover this |
| Context | Separate forced-schema dependency classifier; at most one prior user turn is attached verbatim | Prevent stale-topic inheritance | Core dataset is single-turn, so this change is unit-tested but not measured here |
| Medical | Application-owned standard/urgent boundary response | Prevent generated pharmaceutical facts | Safety route cases provide structural coverage; semantic adequacy needs review |
| Grounding | Isolated claim/source entailment verdict; at most two revisions | Remove claims not supported by selected passages | Structural grades do not independently judge entailment correctness |
| Best effort | Exact-gap notice plus verifier-approved cited subset; short source excerpt only when no generated claim survives | Avoid generic withholding while preserving evidence limits | Usefulness and wording need human review |
| Web | Explicit web requests are policy-owned; Tavily advanced extraction with three chunks/source and trusted-domain filtering | Improve usable external evidence | Only cases invoking web exercise extraction |
| Citations | Unknown citation-shaped tokens are rejected; only current-turn markers render | Block fabricated provenance formats | Marker integrity and adversarial citation cases cover this |
| Bounds | Tool rounds increase from four to six while corrections remain capped at two | Allow bounded recovery without an open loop | Latency/token changes include this cost |
| Prompts | Query-specific demonstrations removed from production prompts | Reduce benchmark anchoring | Automated invariant test; sealed holdout still absent |

## Verification record

- Unit suite before evaluation: **61 passed**.
- Matched dataset: **72 cases per backend**, one generation per case.
- Raw attempts: **144/144**, execution errors: **0**.
- Qualitative human review: **completed during development**; it surfaced stale-context inheritance, fabricated citations, ignored web intent, over-refusal, and weak answer composition. No blinded numeric human score is claimed.
- Reproducibility: use the combined manifest's base commit, dirty-patch hash, prompt hashes, file hashes, dataset hash, commands, and backend identifiers together.
