# Final evaluation runs

## At a glance

This folder contains only the evidence needed for the submitted OSS–frontier comparison and judge-calibration disclosure. Each candidate JSONL preserves case outputs and structural grades; its manifest preserves model, dataset, prompt, and revision provenance.

| File | Responsibility |
|---|---|
| `oss_qwen35_9b_matched_core.jsonl` | Matched Qwen outputs and structural grades. |
| `oss_qwen35_9b_matched_core.manifest.json` | Qwen model, prompt, dataset, and commit provenance. |
| `frontier_gpt54mini_matched_core.jsonl` | Matched GPT-5.4 mini outputs and structural grades. |
| `frontier_gpt54mini_matched_core.manifest.json` | Frontier model, prompt, dataset, and commit provenance. |
| `oss_frontier_matched_core.jsonl` | Combined 144-record comparison input. |
| `oss_frontier_matched_core.manifest.json` | Compatibility and source-run provenance. |
| `qwen35_9b_judge_probe.calibration.json` | Exploratory judge agreement against authored gold labels. |
| `README.md` | Explains retained evidence. |

Intermediate smoke, prompt-development, and superseded single-model runs are intentionally omitted. They can be regenerated through `scripts/run_evals.py`; retaining them would duplicate evidence without affecting the final comparison.
