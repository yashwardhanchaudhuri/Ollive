# Versioned evaluation datasets

## At a glance

These JSONL files are reproducible evaluation inputs. Builders under `scripts/`
create them; the evaluation runner consumes them without silent field coercion.

| File | Responsibility |
|---|---|
| `core.v1.jsonl` | Broad cases across hallucination, bias/harm, and content safety. |
| `judge_gold.v1.jsonl` | Gold labels used to measure judge agreement and calibration. |
| `prompt_regression.v1.jsonl` | Focused cases for observed prompt and grounding failures. |
| `README.md` | Explains dataset roles and provenance boundaries. |

Cases are source evidence, not generated results. Changing labels, rubrics, or
