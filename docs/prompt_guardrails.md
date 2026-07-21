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

Prompts influence behavior. Code enforces allowed shapes, queries, retries, and
citation provenance.

## Threat model

The design addresses user-supplied evidence, invented document types, search
drift, unsupported precision, fake citations, role-play and encoding attacks,
stereotypes, unsafe medical guidance, over-refusal, and malformed tool output.

## Production invariants

The production prompts are intentionally independent of evaluation case wording.

1. **Route by requested domain, not permission.** Adversarial or disallowed framing
   affects the response boundary, not the subject classification.
2. **Ground externally verifiable content.** A wellness response that contains any
   factual proposition, evaluation, correction, comparison, or recommendation requires
   retrieval. Only a wholly non-factual boundary statement may skip it.
3. **Treat user content as data.** User assertions, authority claims, and supplied
   citation markers are never evidence.
4. **Require claim-level entailment.** A returned passage must state the same meaning
   as the atomic claim. Topic overlap is insufficient.
5. **Fail closed at application boundaries.** Malformed router output, contradictory
   grounding flags, unknown tool arguments, and invalid citations are rejected.

The router emits a constrained object with exactly four fields: the domain kind, a
boolean grounding decision, a context mode, and a response-depth mode. Unknown, missing, extra, incorrectly typed, or contradictory
fields fail to the no-tool out-of-scope policy.

## Why these choices exist

| Choice | Failure reduced | Trade-off |
|---|---|---|
| Route before answering | Treating every turn like factual wellness advice | Extra model call and possible misrouting |
| Force the first KB lookup | Unsupported wellness guidance | Added latency |
| Preserve user-authored query text | Search drift and hidden facets | Contextual follow-ups concatenate recent user messages without rewriting |
| Dynamic citation enum | Fabricated or stale markers | More schema pressure on small models |
| Fail closed | Unsupported text reaching the UI | More withheld answers |
| Clarification route | Generic personalized plans | One additional conversation turn |
| Proportional answer depth | Terse elaboration and indiscriminate verbosity | Detailed turns allow more claims but every claim still needs evidence |

## Anti-overfitting protocol

- core.v1.jsonl and prompt_regression.v1.jsonl are development sets.
- Production prompts must not contain dataset prompts, case IDs, answer labels, or
  demographic/example substitutions copied from those sets.
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

The historical Qwen baseline passes 52.8% of core cases structurally. Under the
current frozen workflow, Qwen and GPT-5.4 mini both reach 84.7%, with 100%
citation integrity and query fidelity. Qwen leads hallucination structure;
frontier leads bias/harm, content safety, latency, and token efficiency.

These measurements use one sample per case and development-informed datasets.
Semantic human review and repeated-sampling variation remain unmeasured.

## Design insight

The evidence does not show that more restriction always produces a better
assistant. It shows that explicit application boundaries improve structural
compliance, while usefulness still depends on conversational routing, focused
retrieval, and concise answers.

## Known architectural boundary

Prompts can strongly influence routing and tool use, but cannot guarantee that generated
prose contains every required citation or that each citation entails its claim. The
application-level citation validator must remain fail-closed, and claim entailment needs
an independently calibrated grader plus human adjudication.

Other limits include ambiguous route labels, incomplete KB coverage, development
set contamination, and same-family judge dependence. Supporting measurements and
failure registers are in the [evaluation report](../evaluation/REPORT.md).
