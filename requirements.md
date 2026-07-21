# Dependency rationale

| Field | Value |
|---|---|
| Objective | Explain how one local environment supports Streamlit, retrieval, tests, and vLLM |
| Audience | Operators, contributors, and deployment reviewers |
| Resolution target | One Python 3.11 Linux/NVIDIA environment for the full local runtime |

## At a glance

The default local setup uses one `ollive` environment. Streamlit and vLLM run
as separate processes, but dependency resolution happens once.

This removes duplicate activation and requirements flows. The trade-off is that
vLLM's CUDA/PyTorch constraints now affect the full local environment. A lighter
frontier-only package installation remains available.

See [docs/INSTALL.md](docs/INSTALL.md) for commands and checkpoints.

## Dependency files

| File | Purpose |
|---|---|
| `requirements.txt` | Complete local runtime: application, retrieval, vLLM, and integrations |
| `requirements-dev.txt` | Full local runtime plus the test runner |
| `environment.yml` | One reproducible Python 3.11 Conda environment |
| `pyproject.toml` | Base frontier-capable package plus optional `local` and `dev` extras |

The requirements files optimize for the local Qwen path. The package metadata
keeps vLLM in the `local` extra so `pip install -e .` can still support a
frontier-only machine.

## Selection method

A dependency belongs in an environment when it owns one clear runtime
responsibility. Major versions are bounded to reduce accidental breaking
upgrades while allowing patch fixes.

These files are environment specifications, not immutable deployment locks. A
release should resolve them on its target platform, run tests and `pip check`,
then archive an exact lock or image digest.

## Application packages

| Package | Role |
|---|---|
| **streamlit** | Chat interface and source drawer |
| **PyYAML** | Backend, retrieval, tool, and observability configuration |
| **python-dotenv** | Local environment-variable loading |
| **pydantic** | Strict message, tool, and grounded-answer validation |
| **openai** | Shared client for OpenAI and the local vLLM endpoint |
| **vllm** | Local OpenAI-compatible Qwen server |
| **huggingface-hub** | Model download and shared cache management |
| **sentence-transformers** | Local BGE embedding model |
| **numpy** | Embedding arrays |
| **faiss-cpu** | Local paragraph-vector index |
| **tavily-python** | Optional web-search integration |
| **langfuse** | Optional external tracing; local JSONL remains the default |
| **pytest** | Unit and workflow regression tests |

vLLM and Sentence Transformers share the environment's compatible PyTorch
resolution. Qwen still runs in a separate server process, so model memory and
request handling remain isolated from Streamlit even though packages are shared.

## Resolution and known versions

A pip dry run resolves `requirements.txt` as one Python 3.11 dependency graph
without conflicts. The resolver selects vLLM 0.25.0, PyTorch 2.11.0, and NumPy
2.3.5 alongside the application packages. This checks package compatibility; it
does not install the graph or prove compatibility with every NVIDIA driver.

The versions below have worked for their respective components in this project.
They are useful reference points rather than proof that the newly consolidated
environment has completed an end-to-end GPU run.

| Component | Known working version |
|---|---:|
| Streamlit | 1.59.2 |
| Pydantic | 2.13.4 |
| OpenAI client | 2.46.0 |
| Sentence Transformers | 5.6.0 |
| FAISS CPU | 1.14.3 |
| vLLM | 0.25.0 |
| Application tests | 40 passing |

The application regression suite remains the behavioral checkpoint after
installation. GPU startup and a request through vLLM remain machine-specific
acceptance checks.

## Variations and trade-offs

- Frontier-only operation can use `pip install -e ".[dev]"` and omit vLLM.
- Local Qwen uses `requirements.txt` or `requirements-dev.txt` in one environment.
- Langfuse and Tavily are optional integrations; local tracing works without them.
- CPU FAISS fits the current small corpus but is not a scale benchmark.
- Separate containers can still be used for deployment isolation without changing
  the development setup.

## Scope

Dependency health proves that packages resolve together. It does not prove GPU
compatibility, model quality, corpus authority, or deployment security.
