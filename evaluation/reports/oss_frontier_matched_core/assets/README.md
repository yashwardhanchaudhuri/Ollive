# Matched comparison graphics

## At a glance

These SVGs visualize structural and workflow diagnostics for both candidates.
They support the report but do not substitute for raw records or human review.

| File | Responsibility |
|---|---|
| `axis_pass_rates.svg` | Pairs Qwen and GPT-5.4 mini structural pass rates within each axis. |
| `efficiency_comparison.svg` | Compares mean latency and token use; lower is better. |
| `check_pass_rates.svg` | Compares deterministic guardrail diagnostics. |
| `evaluation_pipeline.svg` | Shows the dataset-to-report evidence flow. |
| `README.md` | Explains the visual evidence boundary. |

Exact values are retained in the parent `summary.json`.
