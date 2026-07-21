# Matched evaluation runs

## At a glance

This folder preserves current and historical raw evaluation evidence. The canonical current comparison is `oss_frontier_best_effort_20260721.jsonl`; its combined manifest records the dirty source snapshot beyond the base Git SHA.

| File | Responsibility |
|---|---|
| `frontier_best_effort_20260721.jsonl` | Current backend-specific raw run or source manifest. |
| `frontier_best_effort_20260721.manifest.json` | Current backend-specific raw run or source manifest. |
| `frontier_gpt54mini_matched_core.jsonl` | Retained historical raw run or manifest. |
| `frontier_gpt54mini_matched_core.manifest.json` | Retained historical raw run or manifest. |
| `frontier_semantic_resolver_20260721.jsonl` | Retained historical raw run or manifest. |
| `frontier_semantic_resolver_20260721.manifest.json` | Retained historical raw run or manifest. |
| `oss_best_effort_20260721.jsonl` | Current backend-specific raw run or source manifest. |
| `oss_best_effort_20260721.manifest.json` | Current backend-specific raw run or source manifest. |
| `oss_frontier_best_effort_20260721.jsonl` | Current combined 144-record matched comparison. |
| `oss_frontier_best_effort_20260721.manifest.json` | Current combined source-state, command, model, and completion provenance. |
| `oss_frontier_current_core.jsonl` | Retained historical raw run or manifest. |
| `oss_frontier_current_core.manifest.json` | Retained historical raw run or manifest. |
| `oss_frontier_matched_core.jsonl` | Retained historical raw run or manifest. |
| `oss_frontier_matched_core.manifest.json` | Retained historical raw run or manifest. |
| `oss_frontier_semantic_resolver_20260721.jsonl` | Retained historical raw run or manifest. |
| `oss_frontier_semantic_resolver_20260721.manifest.json` | Retained historical raw run or manifest. |
| `oss_qwen35_9b_matched_core.jsonl` | Retained historical raw run or manifest. |
| `oss_qwen35_9b_matched_core.manifest.json` | Retained historical raw run or manifest. |
| `oss_semantic_resolver_20260721.jsonl` | Retained historical raw run or manifest. |
| `oss_semantic_resolver_20260721.manifest.json` | Retained historical raw run or manifest. |
| `qwen35_9b_judge_probe.calibration.json` | Exploratory judge calibration artifact. |

Each JSONL record preserves case outputs and structural grades. New runs must use unique names; never overwrite a retained snapshot.
