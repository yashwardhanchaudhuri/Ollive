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
| `wellness_adversarial.v1.jsonl` | Historical 108-case suite that appended wellness requests to mostly domain-neutral attacks. |
| `wellness_adversarial.v1.manifest.json` | Historical v1 authorship and design contract. |
| `wellness_adversarial.v2.jsonl` | 108 wellness-native attacks: four classes by nine MECE cells by three situations. |
| `wellness_adversarial.v2.manifest.json` | Current wellness-native authorship, taxonomy, and design contract. |
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

`wellness_adversarial.v2.jsonl` covers Direct Prompt Injection, Many-Shot
Jailbreaking, Delimiter Break Attack, and DAN-Style Persona. Each class partitions
nine primary mechanisms or framings, and each cell is assigned one of nine wellness
domains. Its three alternatives change the wellness situation while retaining the
cell's attack mechanism. Attacks exploit wellness-native objects and boundaries:
care-role authority, injury and symptom escalation, medication and supplement
limits, crisis handling, wearable records, private journals, habit memory, consent,
and poisoned wellness evidence. They do not append a harmless wellness request to a
generic jailbreak template.

`build_wellness_adversarial_dataset.py` deterministically assembles the reviewed
attack wording stored in `wellness_adversarial.py`; it makes no model call. The
manifest records the human-authored provenance, taxonomy, and design dimensions.
Tests enforce 108 unique cases, balanced cells, explicit wellness-native metadata,
domain language, and absence of the v1 plug-in phrase. This attack-only suite
measures ingress block recall, not benign false-positive rate.
