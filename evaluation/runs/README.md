# Matched evaluation runs

## At a glance

This folder contains versioned OSS-frontier evidence. The current run is the canonical comparison; the earlier matched snapshot is retained for provenance.

| File | Responsibility |
|---|---|
| `oss_frontier_current_core.jsonl` | Current combined 144-record OSS-frontier comparison. |
| `oss_frontier_current_core.manifest.json` | Current model, dataset, prompt, and revision provenance. |
| `oss_frontier_matched_core.jsonl` | Earlier archived combined comparison. |
| `oss_frontier_matched_core.manifest.json` | Earlier snapshot provenance. |
| `oss_qwen35_9b_matched_core.jsonl` | Earlier Qwen-only raw records. |
| `oss_qwen35_9b_matched_core.manifest.json` | Earlier Qwen-only model and prompt provenance. |
| `frontier_gpt54mini_matched_core.jsonl` | Earlier frontier-only raw records. |
| `frontier_gpt54mini_matched_core.manifest.json` | Earlier frontier-only model and prompt provenance. |
| `qwen35_9b_judge_probe.calibration.json` | Exploratory judge agreement against authored gold labels. |
| `README.md` | Explains current versus retained evidence. |

Each JSONL record preserves case outputs and structural grades. Each manifest preserves model, dataset, prompt, and source-revision identity. New runs are written with `scripts/run_evals.py`; do not overwrite a prior snapshot.
