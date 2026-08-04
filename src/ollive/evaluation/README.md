# Evaluation library

## At a glance

This package provides reproducible evaluation mechanics. Versioned inputs and
archived outputs live in the repository-level `evaluation/` folder.

| File | Responsibility |
|---|---|
| `artifacts.py` | Provides atomic text/JSON writers, JSONL loading, hashing, and optional language detection. |
| `cases.py` | Constructs consistently shaped authored evaluation cases. |
| `security_corpus.py` | Implements reusable source loading, construction, leakage checks, and splitting for security corpora. |
| `models.py` | Defines evaluation cases and output records. |
| `dataset.py` | Strictly loads, validates, and summarizes JSONL cases. |
| `runner.py` | Executes cases across backends and records manifests. |
| `security_runner.py` | Executes cases through only the application ingress Security LM boundary. |
| `security_summary.py` | Computes ingress-block, bypass, terminal benign false-positive, and trust-score metrics. |
| `wellness_adversarial.py` | Stores the human-authored wellness-native four-by-nine MECE taxonomy, validation, and deterministic v2 builder. |
| `prompt_audit.py` | Inventories prompt surfaces and detects benchmark-specific coupling. |
| `grader.py` | Computes deterministic structural checks from expected behavior. |
| `judge.py` | Applies semantic judging and calculates calibration metrics. |
| `compare.py` | Measures movement between baseline and candidate runs. |
| `report.py` | Generates one-run summaries and SVG charts. |
| `__init__.py` | Marks the evaluation namespace. |
| `README.md` | Distinguishes reusable code from evaluation evidence. |

Deterministic checks and model judging answer different questions. Reports must
keep both visible and state when human review has not occurred.
