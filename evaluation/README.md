# Ollive evaluation evidence

This directory maps the archived answer-workflow comparison and locally generated
current security regressions. The archived comparison predates the Security LM and mandatory-web pipeline.

## At a glance

| Evidence question | Current answer |
|---|---|
| Candidates | Qwen 3.5 9B and GPT-5.4 mini |
| Archived structural result | Qwen 63/72 (87.5%); frontier 51/72 (70.8%) |
| Matched Qwen (quantization unrecorded) result | 415/575 attacks blocked; 83/638 benign controls blocked; 970/1,213 correct (80.0%) |
| Matched GPT-5.4 mini result | 490/575 attacks blocked; 103/638 benign controls blocked; 1,025/1,213 correct (84.5%) |
| Current security attempts | 2,426/2,426 completed across both backends; zero execution errors |
| Full-suite construction | Deepset Prompt Injections, JailbreakHub, and XSTest |
| Historical custom wellness v1 | Qwen (quantization unrecorded) blocked 86/108 (79.6%): direct 23/27, many-shot 26/27, delimiter 12/27, DAN 25/27 |
| Wellness-native custom v2 | Qwen 3.5 9B FP8 blocked 108/108 at ingress: 107 model blocks, one fail-closed block, zero errors; no benign controls |
| Updated delimiter subset | Explicit FP8: 16/27 (59.3%); historical/default BF16: 22/27 (81.5%); zero errors |
| Citation/query integrity | 100% for both; zero withheld responses |
| Human semantic review | Completed qualitatively during development; no blinded numeric score is claimed |
| Archived answer evaluation | [One-page PDF](../REPORT.pdf) and [detailed report](reports/oss_frontier_best_effort_20260721/report.md) |

The complete suite uses Deepset Prompt Injections for 79 direct, 78 fixed
delimiter-wrapped, and 198 benign cases; hash-disjoint JailbreakHub rows for 200
DAN/persona, 30 many-shot, and 200 regular-prompt controls; and XSTest for 188
unsafe contrasts and 240 safe controls.

The archived revision improves Qwen but regresses frontier relative to its prior matched run. Do not reduce that backend divergence to the combined average, and do not use these numbers to estimate Security LM attack blocking.

## Local files

| File | Responsibility |
|---|---|
| `REPORT.md` | Archived one-page workflow report source with a current security notice. |
| `report_two_column.css` | Reproducible A4 two-column PDF styling. |
| `README.md` | Evidence map and governance. |

## Evidence map

| Need | Canonical artifact |
|---|---|
| Archived one-page workflow evaluation | [REPORT.pdf](../REPORT.pdf) |
| One-page source | [REPORT.md](REPORT.md) |
| Archived workflow diagnostics | [detailed report](reports/oss_frontier_best_effort_20260721/report.md) |
| Evaluated implementation | [change ledger](reports/oss_frontier_best_effort_20260721/CHANGE_LEDGER.md) |
| Raw 144 records | [combined run](runs/oss_frontier_best_effort_20260721.jsonl) |
| Reproducibility identity | [combined manifest](runs/oss_frontier_best_effort_20260721.manifest.json) |
| Dataset | [core.v1.jsonl](datasets/core.v1.jsonl) |
| Focused prompt-injection regressions | Generated locally as `datasets/owasp_prompt_injection.v1.jsonl` and ignored by Git. |
| Public hard security suite | Generated locally under `datasets/public_security/` and ignored by Git. |
| Custom wellness suite | Current [`wellness_adversarial.v2.jsonl`](datasets/wellness_adversarial.v2.jsonl) and manifest; historical v1 retained; ignored Qwen summary at `../data/evals/qwen_wellness_native_v2_20260804.json` |
| Current security regression | Qwen shards under `runs/qwen_fp8_security_full_20260804.shard*`; GPT shards under `runs/gpt54mini_security_full_20260804.shard*`; generated run files are ignored by Git. |
| Focused Qwen/GPT comparison | Raw focused-development shards use the `qwen_security_weak_subsets_*` and `gpt54mini_security_weak_subsets_*` prefixes; generated summaries remain local. |
| Sequential GPT comparison | Raw shards under `runs/gpt54mini_security_sequential_20260804.*`; summary at `reports/gpt54mini_security_sequential_20260804.json`; all ignored by Git. |
| Class-specific GPT comparison | Raw shards under `runs/gpt54mini_security_class_guards_20260804.*`; summary at `reports/gpt54mini_security_class_guards_20260804.json`; all ignored by Git. |
| Focused fix check | Raw run under `runs/qwen_security_owasp_fixcheck_20260804.*`; summary under `../data/evals/`; all ignored by Git. |
| Before/after | [per-backend comparison](reports/oss_frontier_best_effort_20260721/baseline_comparison/report.md) |

## Reproduce

    python scripts/build_eval_dataset.py
    python scripts/build_owasp_security_dataset.py
    python scripts/build_wellness_adversarial_dataset.py
    python scripts/run_evals.py --dataset evaluation/datasets/core.v1.jsonl \
      --backends oss frontier --repetitions 1 --output evaluation/runs/my_run.jsonl
    python scripts/generate_eval_report.py --results evaluation/runs/my_run.jsonl \
      --output-dir evaluation/reports/my_run

New run records preserve outputs, routes, tool traces, Security LM traces, citations, usage, and structural grades. The current combined manifest supplements the default run manifests with dirty-patch, file, prompt, dataset, config, command, hardware, and completion identity.

Install the `evaluation` extra, then build the pinned 1,503-case public security
suite with `python scripts/build_public_security_benchmark.py --fetch`. The
builder records source revisions, hashes, methods, and counts in its generated
manifest. High-volume corpora and dated reports stay local instead of bloating
the repository.

Run the focused Security LM regression separately, with multiple repetitions:

    python scripts/run_security_ingress_evals.py \
      --dataset evaluation/datasets/owasp_prompt_injection.v1.jsonl \
      --repetitions 5 \
      --output evaluation/runs/owasp_prompt_injection.jsonl

## Governance

- Preserve failures and execution errors in denominators.
- Freeze visible development cases; do not tune against a future sealed holdout.
- Human-review critical failures, identity pairs, fallbacks, and sampled passes.
- Treat one generation and model-based entailment as directional evidence only.
