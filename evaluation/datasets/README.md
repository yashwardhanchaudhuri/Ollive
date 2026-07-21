# Versioned evaluation datasets

## At a glance

These JSONL files are reproducible evaluation inputs. Builders under `scripts/`
create them; the evaluation runner loads them with strict schema validation and
never silently coerces unknown or missing fields.

| File | Responsibility |
|---|---|
| `core.v1.jsonl` | The archived 72-case structural comparison across hallucination, bias/harm, and content safety. |
| `judge_gold.v1.jsonl` | Authored pass/fail examples for exploratory judge calibration. |
| `prompt_regression.v1.jsonl` | Development-only wording and fault-class regressions. |
| `README.md` | Explains dataset provenance and use boundaries. |

## Construction and use

`build_eval_dataset.py` writes the core and judge-calibration files;
`build_prompt_regression_dataset.py` writes the distinct regression set. Each
core case specifies an ID, axis, subtype, severity, prompt, expected route,
tool and citation policy, positive behavior, forbidden behavior, and optional
counterfactual-pair metadata.

The loader rejects duplicate IDs, invalid enums, missing behavioral rubrics, and
undeclared record fields. That protects denominators and prevents a malformed
case from silently changing a comparison.

## Evidence boundary

The core and prompt-regression datasets informed development, so they are
regression inputs rather than sealed generalization tests. `judge_gold.v1.jsonl`
contains deliberately clear examples and measures basic judge discrimination; it
is not multi-annotator human gold or production-grade judge validation.

Any new release claim needs a separately authored sealed holdout, blinded human
review for critical and paired cases, and versioned labels or rubric changes.
