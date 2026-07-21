# Evaluation library

## At a glance

This package provides reproducible evaluation mechanics. Versioned inputs and
archived outputs live in the repository-level `evaluation/` folder.

| File | Responsibility |
|---|---|
| `models.py` | Defines evaluation cases and output records. |
| `dataset.py` | Strictly loads, validates, and summarizes JSONL cases. |
| `runner.py` | Executes cases across backends and records manifests. |
| `grader.py` | Computes deterministic structural checks from expected behavior. |
| `judge.py` | Applies semantic judging and calculates calibration metrics. |
| `compare.py` | Measures movement between baseline and candidate runs. |
| `report.py` | Generates one-run summaries and SVG charts. |
| `comprehensive_report.py` | Builds cross-artifact analysis for the consolidated report. |
| `__init__.py` | Marks the evaluation namespace. |
| `README.md` | Distinguishes reusable code from evaluation evidence. |

Deterministic checks and model judging answer different questions. Reports must
keep both visible and state when human review has not occurred.
