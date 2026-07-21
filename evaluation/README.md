# Ollive evaluation evidence

This directory is the single entry point for Ollive's evaluation work.

## At a glance

| Evidence question | Current answer |
|---|---|
| What candidate has a complete archived run? | Qwen/Qwen3.5-9B |
| Is there a valid frontier comparison? | No |
| Are latest results semantically human-graded? | No |
| What is measured? | Routing, tool, citation, query, latency, and token behavior |
| What should be read first? | [Consolidated report](REPORT.md) |

The consolidated report connects dataset design, execution, results, variation,
insights, and limitations. Run-specific reports provide supporting detail rather
than competing narratives.

## Layout

- `REPORT.md` — authoritative overall report
- datasets/ — versioned source cases
- runs/ — raw records, manifests, and calibration output
- reports/ — run-specific reports, summaries, and SVG graphics

## Evidence map

| Need | Canonical artifact |
|---|---|
| Overall interpretation | [REPORT.md](REPORT.md) |
| Dataset creation and provenance | [REPORT.md — Dataset creation](REPORT.md#dataset-creation) |
| Core dataset | [datasets/core.v1.jsonl](datasets/core.v1.jsonl) |
| Prompt regression | [datasets/prompt_regression.v1.jsonl](datasets/prompt_regression.v1.jsonl) |
| Judge calibration | [datasets/judge_gold.v1.jsonl](datasets/judge_gold.v1.jsonl) |
| Latest raw Qwen run | [runs/qwen35_9b_final_core.jsonl](runs/qwen35_9b_final_core.jsonl) |
| Latest detailed report | [reports/qwen35_9b_final_core/report.md](reports/qwen35_9b_final_core/report.md) |
| Before/after report | [reports/prompt_v2_comparison/report.md](reports/prompt_v2_comparison/report.md) |

## Reproduce

    python scripts/build_eval_dataset.py
    python scripts/run_evals.py --dataset evaluation/datasets/core.v1.jsonl \
      --backends oss --repetitions 1 --output evaluation/runs/my_run.jsonl
    python scripts/generate_eval_report.py --results evaluation/runs/my_run.jsonl \
      --output-dir evaluation/reports/my_run

Run records retain route, tool trace, citations, usage, response, and structural
grades. Manifests retain model configuration and prompt hashes.

## Governance

- Preserve failures and include execution errors in denominators.
- Do not tune against a future sealed release holdout.
- Hide model identity during judge or human review where possible.
- Human-review all critical failures and a random sample of passes.
- Version rubric or label changes with their dataset.
- Do not treat same-family self-judging as independent evidence.
