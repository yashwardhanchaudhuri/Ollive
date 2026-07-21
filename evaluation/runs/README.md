# Archived evaluation runs

## At a glance

This folder is the case-level audit trail. A run JSONL records outputs and
grades; its manifest records the model, configuration, dataset, prompt hashes,
and execution context needed to interpret it.

| File | Responsibility |
|---|---|
| `smoke_qwen.jsonl` | Small Qwen pipeline-verification records. |
| `smoke_qwen.manifest.json` | Configuration and provenance for that smoke run. |
| `qwen35_9b_core_v1.jsonl` | Initial full Qwen core records. |
| `qwen35_9b_core_v1.manifest.json` | Provenance for the initial core run. |
| `qwen35_9b_core_prompt_v2.jsonl` | Core records produced with prompt v2. |
| `qwen35_9b_core_prompt_v2.manifest.json` | Provenance for the prompt-v2 core run. |
| `qwen35_9b_final_core.jsonl` | Later full Qwen core records. |
| `qwen35_9b_final_core.manifest.json` | Provenance for the later core run. |
| `prompt_v2_smoke.jsonl` | Prompt-v2 smoke records. |
| `prompt_v2_smoke.manifest.json` | Provenance for the prompt-v2 smoke run. |
| `prompt_v2_regression.jsonl` | First focused prompt-regression records. |
| `prompt_v2_regression.manifest.json` | Provenance for that regression run. |
| `prompt_v21_regression.jsonl` | Prompt-v2.1 regression records. |
| `prompt_v21_regression.manifest.json` | Provenance for the v2.1 run. |
| `prompt_v22_regression.jsonl` | Prompt-v2.2 regression records. |
| `prompt_v22_regression.manifest.json` | Provenance for the v2.2 run. |
| `qwen35_9b_judge_probe.calibration.json` | Judge predictions and agreement metrics against gold labels. |
| `README.md` | Explains raw-run and manifest roles. |

