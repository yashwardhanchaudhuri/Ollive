# Ollive evaluation evidence

This directory is the canonical entry point for the current matched comparison and retained historical snapshots.

## At a glance

| Evidence question | Current answer |
|---|---|
| Candidates | Qwen 3.5 9B and GPT-5.4 mini |
| Current structural result | Qwen 63/72 (87.5%); frontier 51/72 (70.8%) |
| Attempts and errors | 144/144 completed; zero execution errors |
| Citation/query integrity | 100% for both; zero withheld responses |
| Human semantic review | Completed qualitatively during development; no blinded numeric score is claimed |
| Read first | [One-page PDF](../REPORT.pdf) and [current detailed report](reports/oss_frontier_best_effort_20260721/report.md) |

The revision improves Qwen but regresses frontier relative to the prior matched run. Do not reduce that backend divergence to the combined average.

## Local files

| File | Responsibility |
|---|---|
| `REPORT.md` | Current one-page report source. |
| `report_two_column.css` | Reproducible A4 two-column PDF styling. |
| `README.md` | Evidence map and governance. |

## Evidence map

| Need | Canonical artifact |
|---|---|
| One-page evaluation | [REPORT.pdf](../REPORT.pdf) |
| One-page source | [REPORT.md](REPORT.md) |
| Detailed diagnostics | [current report](reports/oss_frontier_best_effort_20260721/report.md) |
| Evaluated implementation | [change ledger](reports/oss_frontier_best_effort_20260721/CHANGE_LEDGER.md) |
| Raw 144 records | [combined run](runs/oss_frontier_best_effort_20260721.jsonl) |
| Reproducibility identity | [combined manifest](runs/oss_frontier_best_effort_20260721.manifest.json) |
| Dataset | [core.v1.jsonl](datasets/core.v1.jsonl) |
| Before/after | [per-backend comparison](reports/oss_frontier_best_effort_20260721/baseline_comparison/report.md) |

## Reproduce

    python scripts/build_eval_dataset.py
    python scripts/run_evals.py --dataset evaluation/datasets/core.v1.jsonl \
      --backends oss frontier --repetitions 1 --output evaluation/runs/my_run.jsonl
    python scripts/generate_eval_report.py --results evaluation/runs/my_run.jsonl \
      --output-dir evaluation/reports/my_run

Run records preserve outputs, routes, tool traces, citations, usage, and structural grades. The current combined manifest supplements the default run manifests with dirty-patch, file, prompt, dataset, config, command, hardware, and completion identity.

## Governance

- Preserve failures and execution errors in denominators.
- Freeze visible development cases; do not tune against a future sealed holdout.
- Human-review critical failures, identity pairs, fallbacks, and sampled passes.
- Treat one generation and model-based entailment as directional evidence only.
