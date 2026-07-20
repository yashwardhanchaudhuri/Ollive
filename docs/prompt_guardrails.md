# Prompt guardrail design

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

The router emits a constrained object with exactly two fields: the domain kind and a
boolean grounding decision. Unknown, missing, extra, incorrectly typed, or contradictory
fields fail to the no-tool out-of-scope policy.

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
- Human review remains required for critical safety behavior, counterfactual fairness,
  and claim-to-source entailment.

## Known architectural boundary

Prompts can strongly influence routing and tool use, but cannot guarantee that generated
prose contains every required citation or that each citation entails its claim. The
application-level citation validator must remain fail-closed, and claim entailment needs
an independently calibrated grader plus human adjudication.
