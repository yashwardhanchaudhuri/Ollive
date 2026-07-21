# Ollive evaluation evidence

This directory is the entry point for the current OSS-frontier comparison and its retained historical snapshots.

## At a glance

| Evidence question | Current answer |
|---|---|
| Which candidates have a matched current run? | Qwen 3.5 9B and GPT-5.4 mini |
| Is there a valid comparison? | Yes for structural workflow behavior; semantic review remains pending |
| Are current results human-graded? | No |
| What is measured? | Routing, tools, citations, query fidelity, latency, and token expenditure |
| What should be read first? | [One-page evaluation paper](REPORT.md) |

The canonical paper summarizes the current 144-attempt run. Detailed records and the earlier archived snapshot remain available for audit, not as competing conclusions.

## Layout

- `REPORT.md` - authoritative one-page paper source for the current run
- `REPORT.pdf` - one-page two-column evaluation paper
- `report_two_column.css` - reproducible PDF layout
- `datasets/` - versioned source cases
- `runs/` - raw records, manifests, and calibration output
- `reports/` - current detailed report, graphics, and retained archive

## Evidence map

| Need | Canonical artifact |
|---|---|
| One-page evaluation PDF | [REPORT.pdf](REPORT.pdf) |
| Overall interpretation | [REPORT.md](REPORT.md) |
| Dataset creation and provenance | [REPORT.md - Study and dataset](REPORT.md#study-and-dataset) |
| Core dataset | [datasets/core.v1.jsonl](datasets/core.v1.jsonl) |
| Current combined run | [runs/oss_frontier_current_core.jsonl](runs/oss_frontier_current_core.jsonl) |
| Current run manifest | [runs/oss_frontier_current_core.manifest.json](runs/oss_frontier_current_core.manifest.json) |
| Current detailed report | [reports/oss_frontier_current_core/report.md](reports/oss_frontier_current_core/report.md) |
| Judge calibration dataset | [datasets/judge_gold.v1.jsonl](datasets/judge_gold.v1.jsonl) |
| Earlier archived comparison | [runs/oss_frontier_matched_core.jsonl](runs/oss_frontier_matched_core.jsonl) |

## Reproduce

    python scripts/build_eval_dataset.py
    python scripts/run_evals.py --dataset evaluation/datasets/core.v1.jsonl \
      --backends oss frontier --repetitions 1 \
      --output evaluation/runs/my_run.jsonl
    python scripts/generate_eval_report.py --results evaluation/runs/my_run.jsonl \
      --output-dir evaluation/reports/my_run

Run records retain route, tool trace, citations, usage, response, and structural grades. Manifests retain model configuration, prompt hashes, and source revision.

## Governance

- Preserve failures and include execution errors in denominators.
- Do not tune against a future sealed release holdout.
- Hide model identity during judge or human review where possible.
- Human-review all critical failures and a random sample of passes.
- Version rubric or label changes with their dataset.
- Do not treat same-family self-judging as independent evidence.
