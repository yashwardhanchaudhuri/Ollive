# Project structure

| Field | Value |
|---|---|
| Objective | Show where responsibilities live and what changes together |
| Audience | Contributors and reviewers |
| Scope | Source-controlled layout plus runtime artifact boundaries |

## How to read the repository

Dependencies point inward. Domain models contain no infrastructure; ports define
capabilities; adapters connect vendors and storage; application code coordinates
the agent; and the UI only presents results.

This arrangement keeps model choice separate from safety and grounding behavior.
The tree below describes the complete source-controlled layout. Generated files
appear only as runtime placeholders. Every project folder also contains a local
`README.md` explaining its role, immediate files, and relationship to this map;
repeated folder guides are omitted from the tree for readability.

```text
Ollive/
├── .env.example                 # Safe environment-variable template
├── .gitignore                   # Secrets and generated local artifacts
├── .streamlit/
│   └── config.toml              # Streamlit theme configuration
├── README.md                    # Project overview and quick start
├── REPORT.pdf                   # One-page two-column evaluation paper
├── run_ollive.sh                # One-command local environment and service launcher
├── environment.yml              # Conda application/development environment
├── pyproject.toml               # Python package metadata
├── requirements.txt             # Unified local runtime, including vLLM
├── requirements.md              # Dependency rationale
│
├── assignment_kb/               # Curated source documents used by local evidence retrieval
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
│   └── backends.yaml            # Agent prompt, backends, retrieval, tools, tracing
│
├── data/                        # Ephemeral runtime output
│   ├── indexes/
│   │   └── .gitkeep             # Generated FAISS index and chunk metadata
│   └── traces/
│       └── .gitkeep             # Generated local JSONL traces
│
├── docs/
│   ├── AGENT_WORKFLOW.md        # End-to-end agent execution and design choices
│   ├── INSTALL.md               # Installation, downloads, ports, troubleshooting
│   ├── KNOWLEDGE_BASE.md        # Corpus scope, retrieval, citations, and limits
│   ├── PROJECT_STRUCTURE.md     # This annotated repository tree
│   ├── WRITING_STANDARD.md      # Narrative and evidence rules for Markdown
│   └── prompt_guardrails.md     # Guardrail threats, choices, results, and limits
│
├── evaluation/                  # Complete, reader-facing evaluation evidence
│   ├── README.md                # Navigation and reproduction guide
│   ├── REPORT.md                # Single authoritative consolidated report
│   ├── report_two_column.css    # Reproducible one-page PDF style
│   ├── datasets/                # Versioned source evaluation datasets
│   │   ├── core.v1.jsonl
│   │   ├── judge_gold.v1.jsonl
│   │   └── prompt_regression.v1.jsonl
│   ├── runs/                    # Archived matched records and manifests
│   │   ├── oss_qwen35_9b_matched_core.jsonl
│   │   ├── frontier_gpt54mini_matched_core.jsonl
│   │   ├── oss_frontier_matched_core.jsonl
│   │   └── qwen35_9b_judge_probe.calibration.json
│   └── reports/                 # Supporting detailed comparison and graphics
│       └── oss_frontier_matched_core/
│
├── scripts/
│   ├── build_eval_dataset.py    # Build the core evaluation dataset
│   ├── build_index.py           # Build/rebuild the local FAISS knowledge index
│   ├── build_prompt_regression_dataset.py
│   ├── combine_eval_runs.py
│   ├── compare_eval_runs.py
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
    ├── test_documentation.py
    ├── test_evaluation.py
    ├── test_grounded_answer.py
    ├── test_guardrails.py
    ├── test_indexer.py
    └── test_memory.py
```

## Design boundaries

| Boundary | Why it exists |
|---|---|
| Unified environment versus separate processes | Simplify installation while isolating model serving from the UI runtime |
| Ports versus adapters | Keep orchestration independent of vendors |
| Dialogue memory versus traces | Prevent stale tool evidence entering later turns |
| Evaluation source versus generated reports | Preserve reproducible inputs and derived evidence |
| Knowledge corpus versus project docs | Avoid indexing operational text as wellness evidence |

## Change-impact guide

| Change | Review together |
|---|---|
| Add a backend | Configuration, adapter, factory, installation docs, evaluation manifest |
| Add a route | Guardrails, agent behavior, datasets, tests, workflow document |
| Change citation shape | Parser, grounding contract, UI, tests, archived evidence |
| Change a KB file | Corpus version, index, citation lines, retrieval tests, evaluation |
| Change report structure | Source Markdown, PDF style/renderer, links, and artifact validation |

The important insight is ownership: behavioral changes rarely belong to one file.
This map keeps prompts, code, tests, and reports from drifting apart.

## Folder-level guides

Use this document to understand the architecture across folders, then use the
nearest `README.md` while working inside a folder. Local guides name every
immediate source file and explain why the folder exists. Documentation tests
enforce guide coverage and file-map synchronization, while the KB indexer
explicitly excludes `assignment_kb/README.md` from retrievable evidence.

## Runtime boundaries

- `src/ollive/`, `scripts/`, `tests/`, `evaluation/datasets/`, and
  `assignment_kb/` are reproducible source inputs.
- `data/indexes/` and `data/traces/` are generated locally and ignored.
- `evaluation/runs/` archives selected raw run evidence and manifests.
- `evaluation/reports/` contains supporting human-readable reports and graphics.
- Model weights live in the Hugging Face cache, not in this repository.
- Local credentials belong only in `.env`, which is excluded from Git.
