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
| Latest Qwen structural evaluation | 63/72 (87.5%) on the current matched run |
| Latest frontier structural evaluation | 51/72 (70.8%) on the current matched run |
| Human semantic review | Not completed |

The [agent workflow](docs/AGENT_WORKFLOW.md) explains the design. The
[consolidated report](evaluation/REPORT.md) explains the evidence and its limits.
## Quick start

From the repository root, use the single launcher:

```bash
./run_ollive.sh oss
```

This creates or updates the unified Conda environment, installs dependencies, builds a missing KB index, starts local Qwen/vLLM, and serves Streamlit at `http://127.0.0.1:8501`. For the frontier backend, put `OPENAI_API_KEY` in `.env`, change `active: oss` to `active: frontier` in `config/backends.yaml`, then run `./run_ollive.sh frontier`. Full prerequisites and troubleshooting are in [docs/INSTALL.md](docs/INSTALL.md).


## Design choices

- **Shared agent spec**: system prompt, last-N memory, tools (`lookup_kb`, `search_web`)
- **Semantic continuation gate**: a dedicated constrained LLM call decides whether the current message has its own substantive subject or requires the preceding dialogue. The application then uses either the current user text or one bounded prior user turn plus the current text; no regex, keyword list, model-written query, or similarity threshold controls this decision.
- **Medical boundary**: a semantic urgency selector chooses one of two application-owned responses; named-drug facts cannot be generated or cited on this route.
- **Swappable backends** via `config/backends.yaml`
  - OSS: **`Qwen/Qwen3.5-9B` on local vLLM** (OpenAI-compatible; `VLLM_API_KEY=EMPTY`)
  - Frontier: `gpt-5.4-mini` (needs `OPENAI_API_KEY`)
- **Local grounding**: paragraph chunks from `assignment_kb/`, indexed by `doc_type`, FAISS + `BAAI/bge-small-en-v1.5`
- **Citations**: every grounded claim selects a current-turn marker, then an isolated verifier checks that the selected passage entails the claim

- **Streamlit UI**: chat, backend switcher, token/latency sidebar, expandable sources
- **Observability**: local JSONL traces in `data/traces/` (no Langfuse keys)

## Architecture

The system uses ports and adapters so the model backend can change without
changing routing, retrieval, validation, or memory. This makes comparisons more
meaningful: candidate models face the same surrounding workflow.

The diagram is a responsibility map, not a multi-agent hierarchy.
![Ollive agent flowchart](docs/agent_workflow.svg)


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
- bounded memory and response-depth settings
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
current turn through `submit_grounded_answer`; an isolated semantic check verifies each
claim against its selected passage before the application renders it. If an exact
answer cannot be validated, the application states the limitation and retains only
verifier-approved cited guidance; unsupported claims are discarded. The UI source drawer
opens either the KB paragraph or the authoritative external page.

## Architecture decisions & tradeoffs

| Decision | Tradeoff |
|----------|----------|
| Qwen on local vLLM for OSS | Proper tool-calling / throughput; `VLLM_API_KEY=EMPTY` |
| Local JSONL tracer by default | Zero-config OSS observability; no Langfuse keys |
| `bge-small-en-v1.5` over MiniLM | Better English retrieval for tiny KB |
| FAISS IndexFlatIP | Exact search; fine for <1k chunks |

## Evaluation

### What the current results mean

The latest matched comparison shows backend divergence: Qwen passes 63/72 (87.5%), while GPT-5.4 mini passes 51/72 (70.8%). Relative to the prior matched run, Qwen improves by 13.9 points and frontier regresses by 15.3 points. Both complete 72/72 attempts with 100% citation integrity and query fidelity and no withheld responses. Frontier is 20.4% faster and uses 22.7% fewer tokens. These are structural results; semantic human review remains pending.

Start with the [current detailed comparison](evaluation/reports/oss_frontier_best_effort_20260721/report.md), the [evaluated change ledger](evaluation/reports/oss_frontier_best_effort_20260721/CHANGE_LEDGER.md), and the current [one-page PDF](REPORT.pdf).
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
- Calibrate the model-based entailment gate against blinded human labels and compare it with an independently trained NLI verifier.
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
