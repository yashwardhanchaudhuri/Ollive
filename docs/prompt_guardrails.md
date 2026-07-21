# Prompt guardrail design

| Field | Value |
|---|---|
| Objective | Explain which failures the guardrails address and where enforcement lives |
| Audience | Prompt authors, application developers, and evaluators |
| Status | Current production design |

## At a glance

Ollive does not depend on one long safety prompt. It selects a turn boundary,
applies route-specific instructions, forces retrieval when facts are needed, and
validates the final structure in application code.

Prompts influence behavior. Code enforces allowed shapes, queries, retries, marker
provenance, and claim-to-source verification before display.

## Threat model

The design addresses user-supplied evidence, invented document types, search
drift, unsupported precision, fake citations, role-play and encoding attacks,
stereotypes, unsafe medical guidance, over-refusal, and malformed tool output.

## Production invariants

The production prompts are intentionally independent of evaluation case wording.

1. **Route by requested domain, not permission.** Adversarial or disallowed framing
   affects the response boundary, not the subject classification.
2. **Ground every wellness route.** The application forces retrieval whenever the
   semantic route is wellness; the model cannot disable tools or citations through a
   routing flag.
3. **Treat user content as data.** User assertions, authority claims, and supplied
   citation markers are never evidence.
4. **Verify claim-level entailment.** Every atomic claim is paired with its selected
   passage in an isolated forced-schema check before rendering. Topic overlap is not
   accepted as support.
5. **Fail closed at application boundaries.** Malformed routing output, unknown tool
   arguments, unusable provenance tokens, and invalid citations are rejected.

A dedicated context classifier emits one strict boolean stating whether prior dialogue
supplies a missing substantive subject. The router separately emits exactly three fields:
domain kind, response depth, and explicit web requirement. Grounding is not model-controlled;
every wellness route requires retrieval. Unknown, missing, extra, incorrectly typed, or
contradictory fields fail to a safe bounded state.

## Why these choices exist

| Choice | Failure reduced | Trade-off |
|---|---|---|
| Classify context separately from policy | Stale-topic inheritance from overloaded routing | One additional small model call and possible misclassification |
| Route before answering | Treating every turn like factual wellness advice | Extra model call and possible misrouting |
| Force the first KB lookup | Unsupported wellness guidance | Added latency |
| Preserve user-authored query text | Search drift and hidden facets | Contextual follow-ups concatenate only the immediately preceding user turn without rewriting |
| Dynamic citation enum | Fabricated or stale markers | More schema pressure on small models |
| Claim entailment verifier | Semantically mismatched citations | Added model call and calibration requirement |
| Salvage only verifier-approved claims | Useful partial evidence survives without speculation | The response may state a limitation instead of directly resolving the request |
| Fail closed on malformed or source-free output | Unsupported text reaching the UI | Some answers are withheld |
| Clarification route | Generic personalized plans | One additional conversation turn |
| Proportional answer depth | Terse elaboration and indiscriminate verbosity | Detailed turns allow more claims but every claim still needs evidence |

## Anti-overfitting protocol

- core.v1.jsonl and prompt_regression.v1.jsonl are development sets.
- Production prompts must not contain dataset prompts, case IDs, answer labels, or
  case-derived substitutions copied from those sets.
- An automated test rejects illustrative phrases and known query-specific anchors in model-facing prompts.
- Evaluation manifests store hashes of the system and router prompts.
- Generalization claims require a separately authored sealed holdout that prompt authors
  cannot inspect before the prompt version is frozen.
- The sealed holdout should include new domains, syntax, languages, multi-turn placement,
  and attack transformations rather than paraphrases alone.
- A holdout failure creates a new prompt version and a new future holdout; the same
  holdout must not become an iterative tuning set.
- Report repeated generations and confidence intervals. A single favorable run is
  directional evidence, not a release claim.
- Human review remains required for critical safety behavior, paired identity fairness,
  and claim-to-source entailment.

## Observed results and variation

In the latest matched run, Qwen passes 63 of 72 cases structurally and GPT-5.4 mini passes 51 of 72. Both complete every attempt with 100% citation integrity and query fidelity and no withheld responses. Qwen improves while frontier regresses against the prior matched baseline, showing that shared guardrails remain backend-sensitive.

These measurements use one sample per case and development-informed datasets.
Semantic human review and repeated-sampling variation remain unmeasured.

## Design insight

The evidence does not show that more restriction always produces a better
assistant. It shows that explicit application boundaries improve structural
compliance, while usefulness still depends on conversational routing, focused
retrieval, and concise answers.

## Known architectural boundary

Prompts cannot guarantee correct routing or evidence use. Application code therefore
constrains tool order, answer structure, marker provenance, and claim-to-source verification.
The entailment check is model-based and still requires independent calibration and human
adjudication.

Other limits include ambiguous route labels, incomplete KB coverage, development
set contamination, and same-family judge dependence. Supporting measurements and
failure registers are in the [evaluation report](../evaluation/REPORT.md).
