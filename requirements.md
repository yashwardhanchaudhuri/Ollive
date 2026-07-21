# Dependency rationale

| Field | Value |
|---|---|
| Objective | Explain why dependencies are split and what each environment owns |
| Audience | Operators, contributors, and deployment reviewers |
| Verified environment | Python 3.11 application and separate Linux/NVIDIA vLLM environment |

## At a glance

Ollive separates the application from the GPU model server. vLLM owns a
CUDA-sensitive PyTorch stack; the application owns Streamlit, retrieval,
validation, and an HTTP client. Keeping them apart makes compatibility and
failure diagnosis easier to reason about.

See [docs/INSTALL.md](docs/INSTALL.md) for commands and checkpoints.

## Dependency files

| File | Purpose |
|---|---|
| `requirements.txt` | Streamlit application, retrieval, model client, and configured integrations |
| `requirements-dev.txt` | Application dependencies plus the test runner |
| `requirements-vllm.txt` | Dedicated Linux/NVIDIA environment for serving Qwen |
| `environment.yml` | Reproducible Python 3.11 Conda development environment |
| `pyproject.toml` | Installable `ollive` package metadata |

Do not install `requirements-vllm.txt` into the application environment. vLLM
selects PyTorch/CUDA packages for the host GPU, while the application needs only
an OpenAI-compatible HTTP client.

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
| **sentence-transformers** | Local BGE embedding model |
| **numpy** | Embedding arrays |
| **faiss-cpu** | Local paragraph-vector index |
| **tavily-python** | Optional web-search integration |
| **langfuse** | Optional external tracing; local JSONL remains the default |
| **pytest** | Unit and workflow regression tests |

`sentence-transformers` installs its compatible Transformers and PyTorch
dependencies. The configured OSS chat model is not loaded by this application;
Qwen runs in the separate vLLM process.

## Verified working versions

| Component | Verified version |
|---|---:|
| Streamlit | 1.59.2 |
| Pydantic | 2.13.4 |
| OpenAI client | 2.46.0 |
| Sentence Transformers | 5.6.0 |
| FAISS CPU | 1.14.3 |
| vLLM | 0.25.0 |
| Application tests | 39 passing |

These are observed working versions, not universal compatibility guarantees.

## Variations and trade-offs

- Frontier-only operation does not need the vLLM environment.
- Local Qwen still needs the application environment for Streamlit and retrieval.
- Langfuse and Tavily are optional integrations; local tracing works without them.
- CPU FAISS fits the current small corpus but is not a scale benchmark.

## Scope

Dependency health proves that packages resolve together. It does not prove GPU
compatibility, model quality, corpus authority, or deployment security.
