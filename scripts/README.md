# Command-line workflows

## At a glance

These thin entry scripts expose reusable package behavior to operators. Core
logic stays under `src/ollive/`.

| File | Responsibility |
|---|---|
| `build_index.py` | Builds and persists the local KB index. |
| `serve_qwen_vllm.sh` | Starts Qwen through local vLLM with explicit FP8 quantization by default; `OLLIVE_VLLM_QUANTIZATION` overrides it. |
| `build_eval_dataset.py` | Creates core and judge-calibration datasets. |
| `build_prompt_regression_dataset.py` | Creates prompt fault-class cases. |
| `build_owasp_security_dataset.py` | Creates focused prompt-injection attacks and benign controls. |
| `build_public_security_benchmark.py` | Fetches pinned public sources and builds the 1,503-case hard suite. |
| `build_security_split_suite.py` | Builds the original source-separated security train/dev/test corpus. |
| `build_security_tuning_suite.py` | Builds the authority-aligned security train/dev/test corpus with paired benign controls. |
| `build_wellness_adversarial_dataset.py` | Builds the 108-case human-authored, wellness-native v2 MECE attack suite and design manifest. |
| `run_evals.py` | Executes a dataset through configured backends. |
| `run_security_ingress_evals.py` | Measures the Security LM ingress boundary without invoking routing, evidence, or answer generation. |
| `summarize_security_evals.py` | Reports gate bypass, false-positive, worst-case, confidence-interval, and trust-score metrics. |
| `score_strongreject.py` | Scores downstream leaks with StrongREJECT or HarmBench. |
| `audit_prompt_specificity.py` | Fails on benchmark literals, long case overlap, examples, or content-specific prompt conditions. |
| `build_heldout_security_suite.py` | Builds the frozen English held-out suite from pinned sources without printing case text. |
| `judge_evals.py` | Applies the model judge and records calibration. |
| `combine_eval_runs.py` | Merges compatible raw runs. |
| `compare_eval_runs.py` | Creates a before/after comparison. |
| `generate_eval_report.py` | Generates a report for one run. |
| `README.md` | Explains script ownership and entry points. |

Run scripts from the repository root so relative paths resolve consistently.

For an ingress comparison, `--security-backend frontier` temporarily reuses the
existing configured frontier backend as the Security LM. It does not change the
normal runtime configuration or place an API key on the command line.

## Generated artifacts

Dataset and report commands publish files atomically: a complete temporary file
replaces the destination only after generation succeeds. Existing output remains
untouched if a command fails. Large downloaded corpora, dated run output, and
security reports are intentionally ignored by Git; only reviewed source datasets
and final report PDFs belong in version control.

Install builder-only dependencies without adding them to the application runtime:

```bash
python -m pip install -e '.[evaluation]'
```

The extra provides deterministic language detection and Parquet input support for
the held-out and split builders. `score_strongreject.py` also requires a separately
pinned StrongREJECT installation because it is an external evaluator, not an Ollive
runtime dependency.

The split and tuning builders deliberately use different default cache directories
and manifests. Their reusable source-loading and leakage-check logic lives in
`src/ollive/evaluation/security_corpus.py`; the files here remain thin CLI entry
points.
