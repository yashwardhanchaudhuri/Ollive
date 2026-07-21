# Ollive evaluation evidence

This directory is the single entry point for Ollive's evaluation work.

## At a glance

| Evidence question | Current answer |
|---|---|
| Which candidates have matched archived runs? | Qwen 3.5 9B and GPT-5.4 mini |
| Is there a valid comparison? | Yes for structural workflow behavior; semantic review is pending |
| Are archived results semantically human-graded? | No |
| What is measured? | Routing, tool, citation, query, latency, and token behavior |
| What should be read first? | [One-page evaluation paper](REPORT.md) |

The consolidated report connects dataset design, execution, results, variation,
insights, and limitations. Run-specific reports provide supporting detail rather
than competing narratives.

## Layout

- `REPORT.md` — authoritative one-page paper source
- `REPORT.pdf` — one-page two-column evaluation paper
- `report_two_column.css` — reproducible PDF layout
- datasets/ — versioned source cases
- runs/ — raw records, manifests, and calibration output
- reports/ — run-specific reports, summaries, and SVG graphics

## Evidence map

| Need | Canonical artifact |
|---|---|
| One-page evaluation PDF | [REPORT.pdf](REPORT.pdf) |
| Overall interpretation | [REPORT.md](REPORT.md) |
| Dataset creation and provenance | [REPORT.md — Study and dataset](REPORT.md#study-and-dataset) |
| Core dataset | [datasets/core.v1.jsonl](datasets/core.v1.jsonl) |
| Prompt regression | [datasets/prompt_regression.v1.jsonl](datasets/prompt_regression.v1.jsonl) |
| Judge calibration | [datasets/judge_gold.v1.jsonl](datasets/judge_gold.v1.jsonl) |
| Matched Qwen run | [runs/oss_qwen35_9b_matched_core.jsonl](runs/oss_qwen35_9b_matched_core.jsonl) |
| Matched frontier run | [runs/frontier_gpt54mini_matched_core.jsonl](runs/frontier_gpt54mini_matched_core.jsonl) |
| Combined comparison | [runs/oss_frontier_matched_core.jsonl](runs/oss_frontier_matched_core.jsonl) |
| Latest detailed report | [reports/oss_frontier_matched_core/report.md](reports/oss_frontier_matched_core/report.md) |

## Reproduce

    python scripts/build_eval_dataset.py
    python scripts/run_evals.py --dataset evaluation/datasets/core.v1.jsonl \
      --backends oss frontier --repetitions 1 --output evaluation/runs/my_run.jsonl
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
