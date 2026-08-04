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
| `owasp_prompt_injection.v1.jsonl` | Focused attacks and benign controls for four OWASP-aligned prompt-injection families. |
| `wellness_adversarial.v1.jsonl` | 108 human-authored wellness attacks: four classes by nine MECE mechanisms by three alternatives. |
| `wellness_adversarial.v1.manifest.json` | Compact authorship and design contract for the custom suite. |
| `public_security/` | 1,503 pinned public cases from garak, PromptInject, HarmBench, JailbreakBench, and Many-shot Jailbreaking. |
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

## Focused prompt-injection regressions

`owasp_prompt_injection.v1.jsonl` contains 24 authored English cases: four
attacks and two benign controls for each of direct prompt injection, many-shot
jailbreaking, delimiter-break attacks, and DAN-style personas. Attack cases must
stop at the Security LM ingress boundary with no main-pipeline tool or citation
activity. Controls measure false positives.

The prompts paraphrase attack patterns from the
[OWASP LLM Prompt Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)
rather than copying its examples. This is a visible regression set, not a sealed
security benchmark.

## Public hard suite

Run `python scripts/build_public_security_benchmark.py --fetch` after installing
the `evaluation` extra. The builder writes cases and a reproducibility manifest
with pinned source revisions, hashes, methods, and counts. These high-volume
outputs are local generated artifacts and are ignored by Git.

## Custom MECE wellness suite

`wellness_adversarial.v1.jsonl` covers Direct Prompt Injection, Many-Shot
Jailbreaking, Delimiter Break Attack, and DAN-Style Persona. Within each class,
nine variations are non-overlapping by primary attack mechanism. Every class spans
the same nine wellness domains exactly once, with three authored alternatives per
cell. The 108 prompts are unique and schema-valid.

`build_wellness_adversarial_dataset.py` deterministically assembles the reviewed
attack wording stored in `wellness_adversarial.py`; it makes no model call. The
manifest records the human-authored provenance and design dimensions. This
attack-only suite measures ingress block recall, not benign false-positive rate.
