# Ollive — Wellness Assistant

Wellness assistant with one fixed agent architecture, two backends, retrieval over a local knowledge base with strict citations, Streamlit UI, and observability.

![Ollive wellness assistant interface](main_page.png)

## At a glance

Ollive asks one design question: how can a small wellness assistant stay
conversational without presenting unsupported guidance as fact?

It separates intent routing, evidence retrieval, structured response generation,
and citation validation. General conversation remains natural; factual wellness
guidance is grounded; vague personalized requests ask for context; and medical
requests stop at a non-clinical boundary.

| Capability or current evidence | Status |
|---|---|
| Local Qwen workflow | Supported through vLLM |
| Grounded local retrieval | Paragraph-level FAISS search |
| Citation provenance checks | Application-enforced and fail-closed |
| Current Qwen structural evaluation | 53/72 (73.6%) on the matched run |
| Current frontier structural evaluation | 62/72 (86.1%); faster and 13.5% lower token use |
| Human semantic review | Not completed |

The [agent workflow](docs/AGENT_WORKFLOW.md) explains the design. The
[consolidated report](evaluation/REPORT.md) explains the evidence and its limits.

## Design choices

- **Shared agent spec**: system prompt, last-N memory, tools (`lookup_kb`, `search_web`)
- **Semantic context policy**: the router distinguishes an isolated request from a dependent follow-up. An isolated grounded turn receives only its current user message; a follow-up receives the relevant recent user turns for retrieval and answer generation. Earlier assistant prose and tool output never become evidence.
- **Swappable backends** via `config/backends.yaml`
  - OSS: **`Qwen/Qwen3.5-9B` on local vLLM** (OpenAI-compatible; `VLLM_API_KEY=EMPTY`)
  - Frontier: `gpt-5.4-mini` (needs `OPENAI_API_KEY`)
- **Local grounding**: paragraph chunks from `assignment_kb/`, indexed by `doc_type`, FAISS + `BAAI/bge-small-en-v1.5`
- **Citations**: every grounded claim selects an application-returned KB or web marker
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

The recommended local path is one command:

```bash
./run_ollive.sh oss
```

It creates or updates the single `ollive` Conda environment, installs the package,
creates `.env` if needed, builds a missing KB index, starts Qwen through vLLM,
waits for the local API, and serves Streamlit at `http://127.0.0.1:8501`. On
exit it stops only the vLLM process it started. The first run downloads the
embedding model and Qwen.

For the frontier backend, set `OPENAI_API_KEY` in `.env`, change `active: oss` to `active: frontier` in `config/backends.yaml`, then run:

```bash
./run_ollive.sh frontier
```

The launcher verifies that its mode matches YAML and starts Streamlit without vLLM. Restore `active: oss` before the OSS path. See
[installation details](docs/INSTALL.md) for prerequisites, ports, manual control,
and troubleshooting. Traces land in `data/traces/*.jsonl`.

## Configuration

`config/backends.yaml` controls:

- `active` backend
- model ids, temperature, memory turns
- embedding model and index paths / `top_k`
- Tavily and observability settings

Set the active backend only in `config/backends.yaml`; it is the single source of truth. The launcher verifies its mode against this value and does not override it.

## Citation contract

Indexer assigns each paragraph:

- `doc_type` from filename (`01_Diet.md` → `diet`)
- `start_line` / `end_line` (1-indexed)
- `descriptor` slug from the paragraph text

`lookup_kb` returns markers like `[diet:L9:portion-control-plays-a-critical]`.
Accepted web results receive separate markers such as `[web:L1:3f5a8c1d7e20]`
plus their original URLs. The model selects only from markers returned during the
current turn through `submit_grounded_answer`; the application renders them, and
the UI source drawer opens either the KB paragraph or the authoritative external
page.

## Architecture decisions & tradeoffs

| Decision | Tradeoff |
|----------|----------|
| Qwen on local vLLM for OSS | Proper tool-calling / throughput; `VLLM_API_KEY=EMPTY` |
| Local JSONL tracer by default | Zero-config OSS observability; no Langfuse keys |
| `bge-small-en-v1.5` over MiniLM | Better English retrieval for tiny KB |
| FAISS IndexFlatIP | Exact search; fine for <1k chunks |

## Evaluation

### What the current results mean

The current matched comparison favors GPT-5.4 mini: 62/72 (86.1%) versus Qwen 3.5 9B at 53/72 (73.6%). Frontier leads the three structural axes, averages 4.95 s versus 6.66 s per case, and uses 366,364 versus 423,556 total tokens. Both retain 100% KB-query fidelity; semantic human review remains pending.

Start with the [one-page evaluation paper](REPORT.pdf).
Sources, datasets, raw outputs, manifests, graphics, and limitations live under `evaluation/`.

The versioned core dataset covers hallucination, paired identity swaps (counterfactual bias), harmful
requests, jailbreaks, and over-refusal. Every record retains the route, tool trace,
citations, usage, final response, and structural grades.

```bash
python scripts/build_eval_dataset.py

VLLM_BASE_URL=http://127.0.0.1:8000/v1 VLLM_API_KEY=EMPTY \
  python scripts/run_evals.py --backends oss frontier --repetitions 1 \
  --output evaluation/runs/oss_frontier_reproduction.jsonl

python scripts/generate_eval_report.py \
  --results evaluation/runs/oss_frontier_reproduction.jsonl \
  --output-dir evaluation/reports/oss_frontier_reproduction
```

The judge is first measured against `judge_gold.v1.jsonl` and fails closed below
the macro-F1 threshold. Same-family judging is exploratory, never release evidence.

Structural grading is intentionally narrower than semantic grading: exact citation
syntax, route choice, and tool policy are deterministic, while claim support, bias,
and refusal quality require a calibrated judge and human review.

## What we would improve with more time

The next stage should strengthen evidence quality rather than add more prompt rules:

- Complete blinded human semantic review of critical failures, pair quality, and sampled passes.
- Create a separately authored sealed holdout that never informs prompt development.
- Run repeated generations and adversarial mutations to measure variance and worst-case behavior.
- Add claim-to-passage entailment review so valid citation syntax cannot mask overbroad claims.
- Measure hosted Qwen hardware/electricity cost and frontier API spend on the same workload.
- Expand multilingual, cultural, disability, and medical-boundary coverage with independent reviewers.

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
