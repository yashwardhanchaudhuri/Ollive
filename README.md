# Ollive — Wellness Assistant

Wellness assistant with one fixed agent architecture, two backends, retrieval over a local knowledge base with strict citations, Streamlit UI, and observability.

## At a glance

Ollive asks one design question: how can a small wellness assistant stay
conversational without presenting unsupported guidance as fact?

It separates intent routing, evidence retrieval, structured response generation,
and citation validation. General conversation remains natural; factual wellness
guidance is grounded; vague personalized requests ask for context; and medical
requests stop at a non-clinical boundary.

| Current capability | Evidence status |
|---|---|
| Local Qwen workflow | Running through vLLM |
| Grounded local retrieval | Paragraph-level FAISS search |
| Citation provenance checks | Application-enforced and fail-closed |
| Qwen structural evaluation | 79.2% on the latest archived 72-case run |
| Frontier comparison | Not completed; no winner claim is supported |
| Human semantic review | Not completed |

The [agent workflow](docs/AGENT_WORKFLOW.md) explains the design. The
[consolidated report](evaluation/REPORT.md) explains the evidence and its limits.

## Design choices

- **Shared agent spec**: system prompt, last-N memory, tools (`lookup_kb`, `search_web`)
- **Swappable backends** via `config/backends.yaml`
  - OSS: **`Qwen/Qwen3.5-9B` on local vLLM** (OpenAI-compatible; `VLLM_API_KEY=EMPTY`)
  - Frontier: `gpt-5.4-mini` (needs `OPENAI_API_KEY`)
- **Local grounding**: paragraph chunks from `assignment_kb/`, indexed by `doc_type`, FAISS + `BAAI/bge-small-en-v1.5`
- **Citations**: every KB-grounded claim uses `[doc_type:L{line}:descriptor]`
- **Streamlit UI**: chat, backend switcher, token/latency sidebar, expandable sources
- **Observability**: local JSONL traces in `data/traces/` (no Langfuse keys)

## Architecture

The system uses ports and adapters so the model backend can change without
changing routing, retrieval, validation, or memory. This makes comparisons more
meaningful: candidate models face the same surrounding workflow.

The diagram is a responsibility map, not a multi-agent hierarchy.

```
      Streamlit
        │
        ▼
  WellnessAgent  (application)
        │
   ┌────┼────┬────────────┐
   ▼    ▼    ▼            ▼
 LLM  Tools Memory     Tracer
 Port  │               Port
   │   ├── lookup_kb → RetrieverPort (FAISS)
   │   └── search_web → WebSearchPort (Tavily)
   ▼
 LLM adapters
   ├── vLLM → Qwen3.5-9B (OSS)
   └── OpenAI → gpt-5.4-mini (frontier)
```

Code layers under `src/ollive/`:

| Layer | Responsibility |
|-------|----------------|
| `domain/` | Messages, citations, usage — no I/O |
| `ports/` | LLM / Retriever / WebSearch / Tracer interfaces |
| `adapters/` | vLLM/OpenAI, FAISS vector retrieval, Tavily, Langfuse |
| `application/` | Agent, tools, memory, config, factory |
| `ui/` | Streamlit |

See [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) for the complete,
annotated repository tree and generated-file boundaries.

The key design insight is that prompts guide behavior, while application code
enforces shapes, query fidelity, retries, and allowed citations.

## Setup

Complete installation, GPU/vLLM setup, model downloads, port configuration, and
troubleshooting are in [docs/INSTALL.md](docs/INSTALL.md).

Application quick start:

```bash
conda env create -f environment.yml
conda activate ollive
python -m pip install -e . --no-deps
cp .env.example .env
python scripts/build_index.py
streamlit run src/ollive/ui/streamlit_app.py --server.port 8501
```

For the local OSS backend, create the separate vLLM environment described in the
installation guide, then start Qwen in another terminal:

```bash
conda activate ollive-vllm
./scripts/serve_qwen_vllm.sh
```

The application uses `requirements.txt`; development adds
`requirements-dev.txt`; the GPU server uses `requirements-vllm.txt`. Traces
land in `data/traces/*.jsonl`.

## Configuration

`config/backends.yaml` controls:

- `active` backend
- model ids, temperature, memory turns
- embedding model and index paths / `top_k`
- Tavily + Langfuse toggles

Override active backend with `OLLIVE_ACTIVE_BACKEND=frontier`.

## Citation contract

Indexer assigns each paragraph:

- `doc_type` from filename (`01_Diet.md` → `diet`)
- `start_line` / `end_line` (1-indexed)
- `descriptor` slug from the paragraph text

`lookup_kb` returns markers like `[diet:L9:portion-control-plays-a-critical]`. The model selects from those exact values through `submit_grounded_answer`; the application renders the markers, and the UI Sources panel resolves them to full paragraphs.

## Architecture decisions & tradeoffs

| Decision | Tradeoff |
|----------|----------|
| Qwen on local vLLM for OSS | Proper tool-calling / throughput; `VLLM_API_KEY=EMPTY` |
| Local JSONL tracer by default | Zero-config OSS observability; no Langfuse keys |
| `bge-small-en-v1.5` over MiniLM | Better English retrieval for tiny KB |
| FAISS IndexFlatIP | Exact search; fine for <1k chunks |

## Evaluation

### What the current results mean

Observed Qwen structural compliance improves substantially from the archived
baseline, especially for routing and tool policy. Citation integrity moves in
the opposite direction in some cases because stricter checks withhold more
answers. This is a safety trade-off, not a complete quality result: semantic
correctness and human usefulness remain unmeasured.

Start with the [consolidated evaluation report](evaluation/REPORT.md); datasets,
raw runs, methodology, graphics, and supporting reports live together under `evaluation/`.

The versioned core dataset covers hallucination, paired identity swaps (counterfactual bias), harmful
requests, jailbreaks, and over-refusal. Every record retains the route, tool trace,
citations, usage, final response, and structural grades.

```bash
python scripts/build_eval_dataset.py

VLLM_BASE_URL=http://127.0.0.1:8000/v1 VLLM_API_KEY=EMPTY \
  python scripts/run_evals.py --backends oss --repetitions 1 \
  --output evaluation/runs/qwen35_9b_core_v1.jsonl

python scripts/judge_evals.py \
  --input evaluation/runs/qwen35_9b_core_v1.jsonl \
  --output evaluation/runs/qwen35_9b_core_v1.judged.jsonl \
  --judge-backend frontier

python scripts/generate_eval_report.py \
  --results evaluation/runs/qwen35_9b_core_v1.judged.jsonl \
  --output-dir evaluation/reports/qwen35_9b_core_v1
```

The judge is first measured against `judge_gold.v1.jsonl` and fails closed below
the macro-F1 threshold. Same-family judging is exploratory, never release evidence.

Structural grading is intentionally narrower than semantic grading: exact citation
syntax, route choice, and tool policy are deterministic, while claim support, bias,
and refusal quality require a calibrated judge and human review.

## Documentation map

| Question | Start here |
|---|---|
| How does one request flow through the system? | [Agent workflow](docs/AGENT_WORKFLOW.md) |
| How is the local evidence corpus constructed? | [Knowledge-base design](docs/KNOWLEDGE_BASE.md) |
| How do I install and run it? | [Installation guide](docs/INSTALL.md) |
| Why do the guardrails work this way? | [Prompt guardrails](docs/prompt_guardrails.md) |
| What was evaluated and what changed? | [Evaluation report](evaluation/REPORT.md) |
| Where does each file belong? | [Project structure](docs/PROJECT_STRUCTURE.md) |
| How should documentation be written? | [Writing standard](docs/WRITING_STANDARD.md) |

## Tests

```bash
pytest -q
```

## License

Assignment / internal use unless otherwise specified.
