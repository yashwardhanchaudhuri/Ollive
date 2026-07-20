# Ollive evaluation datasets

## core.v1.jsonl

This reviewed seed set contains 72 single-turn cases:

| Axis | Cases | Coverage |
|---|---:|---|
| Hallucination | 26 | Answerable KB questions, unsupported precision, false premises, citation and retrieval injection |
| Bias and harmful outputs | 26 | Ten counterfactual pairs plus direct stereotype challenges |
| Content safety | 20 | Medical boundaries, self-harm, harmful requests, jailbreaks, and over-refusal controls |

Each record declares an expected semantic route, tool and citation policy, severity,
positive behavioral rubric, forbidden behavior, optional counterfactual pair, and tags.

The cases intentionally avoid keyword-based grading. Deterministic graders inspect
structured application state. Semantic behavior is graded separately.

## prompt_regression.v1.jsonl

This 24-case set uses phrasings absent from the core set and is balanced evenly across
hallucination, bias/harm, and content safety. It tests the generalized prompt invariants:
domain routing is separate from permission, factual wellness answers require retrieval,
unsupported precision must not be filled from memory, supplied markers are untrusted,
protected-group refusals need no performative retrieval, and medical boundaries survive
role-play, translation, encoding, mixed turns, and claimed authority.

This is a prompt-development regression set, not a sealed release holdout.

## judge_gold.v1.jsonl

This set contains 28 manually authored pass/fail examples across all three axes.
It is a smoke-calibration set, not a production gold standard. A release-quality
judge needs at least 200 stratified examples, multiple blinded annotators,
adjudication, and inter-annotator agreement.

## Data governance

- Do not tune prompts or guardrails on the sealed holdout later used for release.
- Preserve failures; never delete difficult cases to improve a score.
- Keep model identity hidden from judges and human annotators.
- Review all critical failures and a random sample of passes.
- Version any rubric or label change together with the dataset.
- Do not report same-family self-judging as independent evidence.

## Record schema

Required core fields are: id, axis, subtype, severity, prompt, expected_route,
tool_policy, citation_policy, expected_behavior, and forbidden_behavior. Unknown
fields fail shape validation unless added to the typed schema first.
