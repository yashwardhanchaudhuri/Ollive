# Dependency rationale

Ollive deliberately separates the application environment from the GPU model
server. See [docs/INSTALL.md](docs/INSTALL.md) for complete setup and download
instructions.

## Dependency files

| File | Purpose |
|---|---|
| `requirements.txt` | Streamlit application, RAG, model client, and configured integrations |
| `requirements-dev.txt` | Application dependencies plus the test runner |
| `requirements-vllm.txt` | Dedicated Linux/NVIDIA environment for serving Qwen |
| `environment.yml` | Reproducible Python 3.11 Conda development environment |
| `pyproject.toml` | Installable `ollive` package metadata |

Do not install `requirements-vllm.txt` into the application environment. vLLM
selects PyTorch/CUDA packages for the host GPU, while the application needs only
an OpenAI-compatible HTTP client.

## Application packages

| Package | Role |
|---|---|
| **streamlit** | Chat interface and source drawer |
| **PyYAML** | Backend, RAG, tool, and observability configuration |
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

Version ranges are bounded by major version to permit security and patch updates.
The versions verified in the current working environment are documented by
`python -m pip freeze` when an exact deployment lock is required.
