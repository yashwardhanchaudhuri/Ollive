# Matched evaluation runs

## At a glance

This folder preserves reviewed historical records and locally generated current security evidence. The July `oss_frontier_best_effort_20260721.jsonl` comparison is the archived answer-workflow baseline. The current 1,213-case ingress comparison uses local `qwen_fp8_security_full_20260804.shard*` and `gpt54mini_security_full_20260804.shard*` records; generated dated runs remain ignored by Git.

| File | Responsibility |
|---|---|
| `frontier_best_effort_20260721.jsonl` | Archived backend-specific raw run or source manifest. |
| `frontier_best_effort_20260721.manifest.json` | Archived backend-specific raw run or source manifest. |
| `frontier_gpt54mini_matched_core.jsonl` | Retained historical raw run or manifest. |
| `frontier_gpt54mini_matched_core.manifest.json` | Retained historical raw run or manifest. |
| `frontier_semantic_resolver_20260721.jsonl` | Retained historical raw run or manifest. |
| `frontier_semantic_resolver_20260721.manifest.json` | Retained historical raw run or manifest. |
| `oss_best_effort_20260721.jsonl` | Archived backend-specific raw run or source manifest. |
| `oss_best_effort_20260721.manifest.json` | Archived backend-specific raw run or source manifest. |
| `oss_frontier_best_effort_20260721.jsonl` | Archived combined 144-record matched comparison. |
| `oss_frontier_best_effort_20260721.manifest.json` | Archived combined source-state, command, model, and completion provenance. |
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
| `qwen_guard_harmbench_25.jsonl`, `qwen_guard_harmbench_25.manifest.json`, `qwen_guard_harmbench_25.summary.json` | Qwen Security LM sample over HarmBench direct attacks. |
| `qwen_guard_promptinject_25.jsonl`, `qwen_guard_promptinject_25.manifest.json`, `qwen_guard_promptinject_25.summary.json` | Qwen Security LM sample over PromptInject delimiter and goal-hijacking attacks. |
| `qwen_guard_dan_14.jsonl`, `qwen_guard_dan_14.manifest.json`, `qwen_guard_dan_14.summary.json` | Complete pinned garak DAN persona sample. |
| `qwen_guard_manyshot8_10.jsonl`, `qwen_guard_manyshot8_10.manifest.json`, `qwen_guard_manyshot8_10.summary.json` | Qwen sample over eight-shot jailbreaks. |
| `qwen_guard_manyshot32_10.jsonl`, `qwen_guard_manyshot32_10.manifest.json`, `qwen_guard_manyshot32_10.summary.json` | Qwen sample over 32-shot jailbreaks. |
| `qwen_guard_manyshot128_10.jsonl`, `qwen_guard_manyshot128_10.manifest.json`, `qwen_guard_manyshot128_10.summary.json` | Qwen sample over 128-shot jailbreaks. |
| `qwen_guard_pair_10.jsonl`, `qwen_guard_pair_10.manifest.json`, `qwen_guard_pair_10.summary.json` | Qwen sample over JailbreakBench PAIR artifacts. |
| `qwen_guard_gcg_10.jsonl`, `qwen_guard_gcg_10.manifest.json`, `qwen_guard_gcg_10.summary.json` | Qwen sample over JailbreakBench GCG artifacts. |
| `qwen_guard_jbc_10.jsonl`, `qwen_guard_jbc_10.manifest.json`, `qwen_guard_jbc_10.summary.json` | Qwen sample over JailbreakBench JBC artifacts. |
| `qwen_guard_randomsearch_10.jsonl`, `qwen_guard_randomsearch_10.manifest.json`, `qwen_guard_randomsearch_10.summary.json` | Qwen sample over JailbreakBench random-search artifacts. |
| `qwen_guard_benign_10.jsonl`, `qwen_guard_benign_10.manifest.json`, `qwen_guard_benign_10.summary.json` | Matched benign controls used to estimate terminal false positives. |
| `qwen_guard_pilot_direct.jsonl`, `qwen_guard_pilot_direct.manifest.json` | One-case post-fix Qwen integration pilot retained for trace diagnosis. |

Each JSONL record preserves case outputs and structural grades. New runs must use unique names; never overwrite a retained snapshot.

## Qwen Security LM full-suite evidence (2026-08-03)

These files preserve the frozen baseline, prompt-development regressions, and complete candidate comparison. JSONL files hold raw records, manifests bind model/configuration/prompt identity, summaries hold aggregate rates, and StrongREJECT files score downstream gate misses.

### Frozen full baseline

- `qwen_security_baseline_full_artifacts_r1.jsonl`
- `qwen_security_baseline_full_artifacts_r1.manifest.json`
- `qwen_security_baseline_full_artifacts_r1.strongreject.jsonl`
- `qwen_security_baseline_full_artifacts_r1.summary.json`
- `qwen_security_baseline_full_benign_r1.jsonl`
- `qwen_security_baseline_full_benign_r1.manifest.json`
- `qwen_security_baseline_full_benign_r1.summary.json`
- `qwen_security_baseline_full_dan_r1.jsonl`
- `qwen_security_baseline_full_dan_r1.manifest.json`
- `qwen_security_baseline_full_dan_r1.summary.json`
- `qwen_security_baseline_full_direct_r1.jsonl`
- `qwen_security_baseline_full_direct_r1.manifest.json`
- `qwen_security_baseline_full_direct_r1.strongreject.jsonl`
- `qwen_security_baseline_full_direct_r1.summary.json`
- `qwen_security_baseline_full_manyshot_r1.jsonl`
- `qwen_security_baseline_full_manyshot_r1.manifest.json`
- `qwen_security_baseline_full_manyshot_r1.summary.json`
- `qwen_security_baseline_full_r1.summary.json`

### Candidate development regressions

- `qwen_security_candidate_dev_54.summary.json`
- `qwen_security_candidate_dev_benign_10.jsonl`
- `qwen_security_candidate_dev_benign_10.manifest.json`
- `qwen_security_candidate_dev_dan_14.jsonl`
- `qwen_security_candidate_dev_dan_14.manifest.json`
- `qwen_security_candidate_dev_harmbench_10.jsonl`
- `qwen_security_candidate_dev_harmbench_10.manifest.json`
- `qwen_security_candidate_dev_manyshot_10.jsonl`
- `qwen_security_candidate_dev_manyshot_10.manifest.json`
- `qwen_security_candidate_dev_promptinject_10.jsonl`
- `qwen_security_candidate_dev_promptinject_10.manifest.json`
- `qwen_security_candidate_dev_v2_benign_10.jsonl`
- `qwen_security_candidate_dev_v2_benign_10.manifest.json`
- `qwen_security_candidate_dev_v2_benign_10.summary.json`
- `qwen_security_candidate_dev_v2_gcg97.jsonl`
- `qwen_security_candidate_dev_v2_gcg97.manifest.json`
- `qwen_security_candidate_dev_v2_prompt236.jsonl`
- `qwen_security_candidate_dev_v2_prompt236.manifest.json`
- `qwen_security_candidate_dev_v2_prompt330.jsonl`
- `qwen_security_candidate_dev_v2_prompt330.manifest.json`
- `qwen_security_candidate_dev_v3_benign_10.jsonl`
- `qwen_security_candidate_dev_v3_benign_10.manifest.json`
- `qwen_security_candidate_dev_v3_focus.summary.json`
- `qwen_security_candidate_dev_v3_gcg97.jsonl`
- `qwen_security_candidate_dev_v3_gcg97.manifest.json`
- `qwen_security_candidate_dev_v3_prompt236.jsonl`
- `qwen_security_candidate_dev_v3_prompt236.manifest.json`
- `qwen_security_candidate_dev_v3_prompt330.jsonl`
- `qwen_security_candidate_dev_v3_prompt330.manifest.json`

### Candidate full comparison

- `qwen_security_candidate_full_unscored_audit.json`
- `qwen_security_candidate_full_artifacts_r1.jsonl`
- `qwen_security_candidate_full_artifacts_r1.manifest.json`
- `qwen_security_candidate_full_artifacts_r1.strongreject.jsonl`
- `qwen_security_candidate_full_benign_r1.jsonl`
- `qwen_security_candidate_full_benign_r1.manifest.json`
- `qwen_security_candidate_full_dan_r1.jsonl`
- `qwen_security_candidate_full_dan_r1.manifest.json`
- `qwen_security_candidate_full_direct_part1_r1.jsonl`
- `qwen_security_candidate_full_direct_part1_r1.manifest.json`
- `qwen_security_candidate_full_direct_part1_r1.strongreject.jsonl`
- `qwen_security_candidate_full_direct_part2_r1.jsonl`
- `qwen_security_candidate_full_direct_part2_r1.manifest.json`
- `qwen_security_candidate_full_direct_part2_r1.strongreject.jsonl`
- `qwen_security_candidate_full_direct_part3_r1.jsonl`
- `qwen_security_candidate_full_direct_part3_r1.manifest.json`
- `qwen_security_candidate_full_direct_part3_r1.strongreject.jsonl`
- `qwen_security_candidate_full_direct_part4_r1.jsonl`
- `qwen_security_candidate_full_direct_part4_r1.manifest.json`
- `qwen_security_candidate_full_manyshot_r1.jsonl`
- `qwen_security_candidate_full_manyshot_r1.manifest.json`
- `qwen_security_candidate_full_r1.summary.json`

### Candidate smoke pilots

- `qwen_security_candidate_pilot_attack.jsonl`
- `qwen_security_candidate_pilot_attack.manifest.json`
- `qwen_security_candidate_pilot_benign.jsonl`
- `qwen_security_candidate_pilot_benign.manifest.json`
