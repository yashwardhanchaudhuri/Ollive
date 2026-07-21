# Supporting evaluation reports

## At a glance

Each child folder turns one archived run or comparison into readable findings.
The consolidated interpretation remains `evaluation/REPORT.md`.

| Folder | Responsibility |
|---|---|
| `qwen35_9b_core_v1/` | Initial full Qwen core evaluation. |
| `qwen35_9b_final_core/` | Later Qwen core evaluation after prompt changes. |
| `prompt_v2_comparison/` | Before/after structural comparison of prompt iterations. |
| `smoke_qwen/` | Small pipeline-verification run. |
| `README.md` | Explains how supporting reports relate to the consolidated result. |

Reports and SVGs are derived views. Their `summary.json` and corresponding raw
records under `evaluation/runs/` preserve machine-readable evidence.
