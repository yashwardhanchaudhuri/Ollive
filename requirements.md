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
vLLM's CUDA/PyTorch constraints now affect the full local environment. The frontier backend is selected at runtime; it uses the same installed environment.

See [docs/INSTALL.md](docs/INSTALL.md) for commands and checkpoints.

## Dependency files

| File | Purpose |
|---|---|
| `requirements.txt` | Unified application, retrieval, vLLM, integration, and test dependencies |
| `environment.yml` | One reproducible Python 3.11 Conda environment |
| `pyproject.toml` | Base frontier-capable package plus optional `local` and `dev` extras |

The requirements file is the supported unified runtime. Package extras remain available for packaging, but they are not a second recommended environment.

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
| **FFmpeg** | Included by the Conda environment; a venv setup may require corresponding system libraries for the validated local stack. |
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

The unified Python 3.11 environment resolves and runs on the project L40S host with
vLLM 0.25.0, PyTorch 2.11.0, NumPy 2.3.5, and FFmpeg 8.0.1. A live Qwen request,
local retrieval, trusted-domain web completion, citation validation, and the full
test suite all complete from that environment.

These versions describe the validated host, not a universal compatibility guarantee
for every NVIDIA driver and GPU combination.

| Component | Known working version |
|---|---:|
| Streamlit | 1.59.2 |
| Pydantic | 2.13.4 |
| OpenAI client | 2.46.0 |
| Sentence Transformers | 5.6.0 |
| FAISS CPU | 1.14.3 |
| vLLM | 0.25.0 |
| PyTorch | 2.11.0+cu130 |
| FFmpeg | 8.0.1 |
| Application tests | 56 passing |

The application regression suite remains the behavioral checkpoint after
installation. GPU startup and a request through vLLM remain machine-specific
acceptance checks.

## Variations and trade-offs

- Local Qwen and development checks use the same `requirements.txt` environment.
- Langfuse and Tavily are optional integrations; local tracing works without them.
- CPU FAISS fits the current small corpus but is not a scale benchmark.
- Separate containers can still be used for deployment isolation without changing
  the development setup.

## Scope

Dependency health proves that packages resolve together. It does not prove GPU
compatibility, model quality, corpus authority, or deployment security.
