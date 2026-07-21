# Ollive installation and model downloads

This guide uses one Python environment for the local application, retrieval, tests,
and vLLM. Qwen and Streamlit still run as separate processes.

A frontier-only installation can omit vLLM through the package extras described
below.

## What this guide produces

At the end of the local OSS path:

- One `ollive` environment contains application and model-server dependencies.
- Qwen serves an OpenAI-compatible API on port 8000.
- The application has a paragraph-level vector index built with FAISS.
- Streamlit serves Ollive on port 8501.
- Tests and dependency checks pass in the same environment.

## Choose a path

| Goal | Installation | Model download |
|---|---|---:|
| Local Qwen | `requirements-dev.txt` or `environment.yml` | Qwen and embedding model |
| Frontier only | `pip install -e ".[dev]"` | Embedding model |
| Local runtime without tests | `requirements.txt` | Qwen and embedding model |

The unified local environment is simpler to operate. Its trade-off is that vLLM
and its CUDA/PyTorch constraints now participate in the same dependency resolution.

## Prerequisites

- Linux or WSL2
- Git
- Conda/Miniconda, or Python 3.11 with `venv`
- Internet access for Python packages and Hugging Face model downloads
- For local Qwen: a supported NVIDIA GPU, driver, and sufficient VRAM

Run every command from the repository root.

## 1. Install the application

### Conda

```bash
conda env create -f environment.yml
conda activate ollive
python -m pip install -e . --no-deps
```

### Python venv

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

For tests and development tools, use:

```bash
python -m pip install -r requirements-dev.txt
```

For a frontier-only environment without vLLM:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

**Checkpoint:** `python -m pip check` should report no broken requirements.
This verifies dependency consistency, not model access or GPU compatibility.

## 2. Configure environment variables

```bash
cp .env.example .env
```

The local Qwen configuration needs only:

```dotenv
VLLM_BASE_URL=http://127.0.0.1:8000/v1
VLLM_API_KEY=EMPTY
OLLIVE_ACTIVE_BACKEND=oss
```

To use the frontier backend instead:

```dotenv
OPENAI_API_KEY=replace_me
OPENAI_BASE_URL=https://api.openai.com/v1
OLLIVE_ACTIVE_BACKEND=frontier
```

`TAVILY_API_KEY` and Langfuse variables are optional. Never commit the populated
`.env` file.

## 3. Verify the local model server dependency

The full local requirements already install vLLM:

```bash
conda activate ollive
vllm --version
```

Skip this check for a frontier-only installation. If vLLM cannot find a
compatible wheel during installation, consult its CUDA compatibility guidance
for the driver and hardware on the machine.

## 4. Download the models

The first index build automatically downloads the embedding model, and the first
vLLM launch automatically downloads Qwen. To download both ahead of time:

```bash
conda activate ollive
hf auth login                     # optional for public models
hf download Qwen/Qwen3.5-9B
hf download BAAI/bge-small-en-v1.5
```

Hugging Face stores both downloads in the same shared cache. Set `HF_HOME` in `.env` or
the shell before downloading if the cache must live on a larger disk.

To serve a pre-downloaded model from a specific directory, set
`OLLIVE_OSS_MODEL=/absolute/path/to/model` before starting the server.

## 5. Start Qwen through vLLM

With the Ollive environment active:

```bash
conda activate ollive
./scripts/serve_qwen_vllm.sh
```

Optional server settings:

```bash
export OLLIVE_VLLM_PORT=8000
export OLLIVE_VLLM_TP=1
export OLLIVE_VLLM_MAX_LEN=32768
export OLLIVE_OSS_MODEL=Qwen/Qwen3.5-9B
./scripts/serve_qwen_vllm.sh
```

Check the server from another terminal:

```bash
curl http://127.0.0.1:8000/v1/models
```

The server must stay running while the OSS backend is selected.

**Checkpoint:** `curl http://127.0.0.1:8000/v1/models` should return a JSON
model list containing the served model. A successful connection alone does not
prove tool calling works.

## 6. Build the knowledge index

From the same environment:

```bash
conda activate ollive
python scripts/build_index.py
```

This downloads `BAAI/bge-small-en-v1.5` when necessary and writes the FAISS
index under `data/indexes/`.

Rebuild the index whenever documents in `assignment_kb/` change.

**Checkpoint:** `data/indexes/` should contain `faiss.index`, `chunks.pkl`,
and `meta.json`. Indexed document types must match the configured enum.

## 7. Start Streamlit

```bash
conda activate ollive
streamlit run src/ollive/ui/streamlit_app.py \
  --server.address 0.0.0.0 \
  --server.port 8501
```

Open `http://localhost:8501`.

If accessing a remote machine, allow TCP port 8501 only from trusted addresses
in the host firewall or cloud security group. Streamlit is not configured with
application-level authentication, so do not expose it directly to the public
internet.

## 8. Verify the installation

```bash
python -m pip check
pytest -q
```

For the OSS backend, also confirm that both ports are listening:

```bash
ss -ltnp | grep -E ':8000|:8501'
```

Passing tests establishes code-level invariants and fixture behavior. It does
not establish model quality; use the evaluation bundle for behavioral evidence.

## Troubleshooting

### The local Qwen service is unavailable

Confirm that vLLM is running and that `VLLM_BASE_URL` includes the `/v1`
suffix. Test `curl http://127.0.0.1:8000/v1/models`.

### CUDA out of memory

Reduce `OLLIVE_VLLM_MAX_LEN`, stop other GPU workloads, or use more tensor
parallel workers when multiple compatible GPUs are available.

### Model downloads fill the system disk

Set `HF_HOME` to a larger volume before running either `hf download` command,
then restart the indexer and vLLM with the same value.

### Frontier requests fail

Set `OPENAI_API_KEY`, select the `frontier` backend, and confirm that
`OPENAI_BASE_URL` is either unset or points to an OpenAI-compatible `/v1`
endpoint.

## Scope and security

- The Streamlit UI has no application-level authentication.
- `VLLM_API_KEY=EMPTY` is appropriate only for a controlled local endpoint.
- Public deployment needs a trusted proxy, access control, TLS, and network restrictions.
- Installation success does not validate the authority of the wellness corpus.
- GPU compatibility varies by driver, CUDA runtime, vLLM wheel, and hardware.
