# Command-line workflows

## At a glance

These thin entry scripts expose reusable package behavior to operators. Core
logic stays under `src/ollive/`.

| File | Responsibility |
|---|---|
| `build_index.py` | Builds and persists the local KB index. |
| `serve_qwen_vllm.sh` | Starts Qwen through the local vLLM service. |
| `build_eval_dataset.py` | Creates core and judge-calibration datasets. |
| `build_prompt_regression_dataset.py` | Creates prompt fault-class cases. |
| `run_evals.py` | Executes a dataset through configured backends. |
| `judge_evals.py` | Applies the model judge and records calibration. |
| `combine_eval_runs.py` | Merges compatible raw runs. |
| `compare_eval_runs.py` | Creates a before/after comparison. |
| `generate_eval_report.py` | Generates a report for one run. |
| `README.md` | Explains script ownership and entry points. |

Run scripts from the repository root so relative paths resolve consistently.
