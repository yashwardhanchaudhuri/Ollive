# Project structure

The tree below describes the complete source-controlled layout. Generated files
are shown where they are created at runtime, but are excluded from Git.

```text
Ollive/
├── .env.example                 # Safe environment-variable template
├── .gitignore                   # Secrets, caches, models, indexes, and run outputs
├── .streamlit/
│   └── config.toml              # Streamlit theme configuration
├── README.md                    # Project overview and quick start
├── environment.yml              # Conda application/development environment
├── pyproject.toml               # Python package metadata
├── requirements.txt             # Application dependencies
├── requirements-dev.txt         # Application plus test dependencies
├── requirements-vllm.txt        # Separate GPU model-server dependencies
├── requirements.md              # Dependency rationale
│
├── assignment_kb/               # Curated source documents used by local RAG
│   ├── 01_Diet.md
│   ├── 02_Exercise.md
│   ├── 03_Wellness_Retreats.md
│   ├── 04_Meditation_Reflection.md
│   ├── 05_Reading_Socializing.md
│   ├── 06_Daily_Habits.md
│   ├── 07_Natural_Organic_Eating.md
│   ├── 08_Natural_Supplements.md
│   └── 09_Nature_General_Welfare.md
│
├── config/
│   └── backends.yaml            # Agent prompt, backends, RAG, tools, tracing
│
├── data/                        # Ephemeral runtime output
│   ├── indexes/
│   │   └── .gitkeep             # Generated FAISS index and chunk metadata
│   └── traces/
│       └── .gitkeep             # Generated local JSONL traces
│
├── docs/
│   ├── INSTALL.md               # Installation, downloads, ports, troubleshooting
│   ├── PROJECT_STRUCTURE.md     # This annotated repository tree
│   └── prompt_guardrails.md     # Guardrail design and prompt rationale
│
├── evaluation/                  # Complete, reader-facing evaluation evidence
│   ├── README.md                # Navigation and reproduction guide
│   ├── REPORT.md                # Single authoritative consolidated report
│   ├── datasets/                # Versioned source evaluation datasets
│   │   ├── core.v1.jsonl
│   │   ├── judge_gold.v1.jsonl
│   │   └── prompt_regression.v1.jsonl
│   ├── runs/                    # Archived raw records and manifests
│   └── reports/                 # Supporting run reports and SVG graphics
│       ├── prompt_v2_comparison/
│       ├── qwen35_9b_core_v1/
│       ├── qwen35_9b_final_core/
│       └── smoke_qwen/
│
├── scripts/
│   ├── build_eval_dataset.py    # Build the core evaluation dataset
│   ├── build_index.py           # Build/rebuild the local FAISS knowledge index
│   ├── build_prompt_regression_dataset.py
│   ├── combine_eval_runs.py
│   ├── compare_eval_runs.py
│   ├── generate_comprehensive_eval_report.py
│   ├── generate_eval_report.py
│   ├── judge_evals.py           # Run calibrated model judging
│   ├── run_evals.py             # Execute evaluation cases
│   └── serve_qwen_vllm.sh       # Start Qwen through the vLLM server
│
├── src/
│   └── ollive/
│       ├── __init__.py
│       ├── application/         # Agent orchestration and use cases
│       │   ├── agent.py         # Main bounded agent/tool loop
│       │   ├── config.py        # YAML and environment loading
│       │   ├── factory.py       # Composition root
│       │   ├── grounded_answer.py # Strict grounded-answer contract
│       │   ├── guardrails.py    # Semantic routing and turn policies
│       │   ├── memory.py        # Bounded dialogue-only memory
│       │   └── tools.py         # Tool schemas, validation, dispatch
│       ├── domain/              # Infrastructure-free domain types
│       │   ├── citations.py
│       │   └── models.py
│       ├── ports/               # Adapter interfaces
│       │   ├── llm.py
│       │   ├── retriever.py
│       │   ├── tracer.py
│       │   └── web_search.py
│       ├── adapters/            # Concrete infrastructure integrations
│       │   ├── llm/
│       │   │   ├── local_transformers.py
│       │   │   └── openai_compatible.py
│       │   ├── observability/
│       │   │   ├── factory.py
│       │   │   ├── langfuse_tracer.py
│       │   │   └── local_tracer.py
│       │   ├── rag/
│       │   │   ├── local_retriever.py
│       │   │   └── markdown_indexer.py
│       │   └── search/
│       │       └── tavily_search.py
│       ├── evaluation/          # Dataset, grading, judging, comparison, reports
│       │   ├── compare.py
│       │   ├── comprehensive_report.py
│       │   ├── dataset.py
│       │   ├── grader.py
│       │   ├── judge.py
│       │   ├── models.py
│       │   ├── report.py
│       │   └── runner.py
│       └── ui/
│           ├── streamlit_app.py # Streamlit entry point
│           └── styles.css       # UI styling kept outside Python
│
└── tests/
    ├── test_agent_grounding.py
    ├── test_citations.py
    ├── test_evaluation.py
    ├── test_grounded_answer.py
    ├── test_guardrails.py
    ├── test_indexer.py
    └── test_memory.py
```

## Runtime boundaries

- `src/ollive/`, `scripts/`, `tests/`, `evaluation/datasets/`, and
  `assignment_kb/` are reproducible source inputs.
- `data/indexes/` and `data/traces/` are generated locally and ignored.
- `evaluation/runs/` archives selected raw run evidence and manifests.
- `evaluation/reports/` contains supporting human-readable reports and graphics.
- Model weights live in the Hugging Face cache, not in this repository.
- Local credentials belong only in `.env`, which is excluded from Git.
