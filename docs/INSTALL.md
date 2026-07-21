# Ollive installation and local run guide

Ollive uses **one Python environment** for Streamlit, retrieval, tests, the
local Qwen server, and the frontier backend. Qwen and Streamlit are separate
processes, but they use the same installed dependencies. Do not create another environment just for frontier; switch backend through `.env` or the UI instead.

## What this guide produces

- One `ollive` environment with the application, tests, embeddings, and vLLM.
- Qwen on an OpenAI-compatible local API at `127.0.0.1:8000` when the OSS
  backend is used.
- A paragraph-level FAISS index under `data/indexes/`.
- Streamlit at `127.0.0.1:8501`.

## Choose a path: one-command local setup or manual control

From the repository root, run the repository-root launcher:

```bash
./run_ollive.sh oss
```

The launcher creates or updates the single `ollive` Conda environment, installs
the package, copies `.env.example` when `.env` is missing, builds a missing KB
index, starts Qwen/vLLM on `127.0.0.1:8000`, waits for its health endpoint, and
starts Streamlit on `127.0.0.1:8501`. It reuses already healthy local vLLM and Streamlit services rather than starting duplicates. When Streamlit exits, it stops only the
vLLM process it started. The first invocation downloads the embedding and Qwen
models, so it can take several minutes.

For the frontier backend, put `OPENAI_API_KEY` in `.env`, change `active: oss` to `active: frontier` in `config/backends.yaml`, then run:

```bash
./run_ollive.sh frontier
```

The launcher verifies that its mode matches YAML and starts only Streamlit. Restore `active: oss` before the OSS path. `TAVILY_API_KEY`
remains optional for authoritative web-search completion. Both paths bind their
services to loopback by default.

Useful overrides are `OLLIVE_ENV_NAME`, `OLLIVE_STREAMLIT_PORT`,
`OLLIVE_VLLM_PORT`, `OLLIVE_VLLM_MAX_LEN`, `OLLIVE_VLLM_TP`, and
`OLLIVE_VLLM_READY_TIMEOUT`. The launcher writes the server output it starts to
`data/vllm.log` and prints its last 40 lines if readiness fails.

## Manual setup and control

Choose Conda for the project-tested installer or Python venv when you already manage the local CUDA/vLLM prerequisites. Both choices create the same unified Ollive environment and can run either backend.

## Prerequisites

- Linux or WSL2, Git, and internet access for packages and model downloads.
- Conda or Miniconda for the one-command launcher; `curl` is also required for its local health check. Python 3.11 with `venv` remains supported for the manual path.
- For local Qwen: a supported NVIDIA GPU, compatible driver/CUDA stack, and
  sufficient VRAM. Conda installs FFmpeg; a venv setup may need required
  system libraries from the operating-system package manager.

Run all commands from the repository root.

## 1. Create the unified environment manually (optional)

### Conda (recommended)

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

The same environment supports both backends. The OSS backend uses the installed
vLLM server; the frontier backend simply does not start that server.

**Checkpoint:** `python -m pip check` reports no broken requirements. This
checks Python dependency resolution, not GPU or model availability.

## 2. Configure environment variables manually (optional)

```bash
cp .env.example .env
```

For local Qwen:

```dotenv
VLLM_BASE_URL=http://127.0.0.1:8000/v1
VLLM_API_KEY=EMPTY
```

For the frontier backend in the same environment:

```dotenv
OPENAI_API_KEY=replace_me
OPENAI_BASE_URL=https://api.openai.com/v1
```

`TAVILY_API_KEY` is optional and enables authoritative-domain web completion.
Never commit the populated `.env` file.

## 3. Download models and build the KB index manually (optional)

The first index build downloads `BAAI/bge-small-en-v1.5`; the first vLLM launch
downloads Qwen. To pre-download them, run:

```bash
hf download Qwen/Qwen3.5-9B
hf download BAAI/bge-small-en-v1.5
```

Set `HF_HOME` before downloading when the cache belongs on another disk. Then
build the index:

```bash
python scripts/build_index.py
```

This writes `faiss.index`, `chunks.pkl`, and `meta.json` under `data/indexes/`.
Rebuild whenever a file in `assignment_kb/` changes.

## 4. Start the selected backend manually (optional)

For OSS Qwen, keep this process running in a second terminal using the same
environment:

```bash
./scripts/serve_qwen_vllm.sh
```

Useful local-server overrides:

```bash
export OLLIVE_VLLM_PORT=8000
export OLLIVE_VLLM_TP=1
export OLLIVE_VLLM_MAX_LEN=32768
export OLLIVE_OSS_MODEL=Qwen/Qwen3.5-9B
./scripts/serve_qwen_vllm.sh
```

Verify it with:

```bash
curl http://127.0.0.1:8000/v1/models
```

and a valid `OPENAI_API_KEY` instead.

## 5. Start Streamlit manually (optional)

```bash
streamlit run src/ollive/ui/streamlit_app.py \
  --server.address 127.0.0.1 \
  --server.port 8501
```

Open `http://127.0.0.1:8501`. Switching models in the sidebar starts a new
chat because a transcript and usage totals belong to the model that produced
them.

The UI is intentionally bound to localhost. Use an SSH tunnel or trusted
development port-forwarder for remote access; do not expose it publicly without
authentication, TLS, and network controls.

## 6. Verify the installation

```bash
python -m pip check
python -m pytest -q
```

When using OSS Qwen, also confirm both local services:

```bash
ss -ltnp | grep -E ":8000|:8501"
```

Tests establish code-level behavior. Use the evaluation bundle for model
behavior evidence.

## Troubleshooting

### The local Qwen service is unavailable

Confirm vLLM is running and that `VLLM_BASE_URL` includes `/v1`. Then run
`curl http://127.0.0.1:8000/v1/models`.

### vLLM cannot install or start

Use the Conda setup first, then verify GPU driver, CUDA, vLLM-wheel, and
hardware compatibility. If using a venv, install platform libraries required by
your vLLM/PyTorch stack through the operating-system package manager.

### CUDA out of memory

Reduce `OLLIVE_VLLM_MAX_LEN`, stop competing GPU workloads, or increase tensor
parallelism only when multiple compatible GPUs are available.

### Model downloads fill the disk

Set `HF_HOME` to a larger volume before downloading, then restart the indexer
and vLLM with that same value.

### Frontier requests fail

Check `OPENAI_API_KEY`, select `frontier`, and ensure `OPENAI_BASE_URL` is
unset or an OpenAI-compatible `/v1` endpoint.

## Scope and security

- `VLLM_API_KEY=EMPTY` is suitable only for a controlled loopback endpoint.
- The Streamlit UI has no application-level authentication.
- Installation success does not establish model quality, KB authority, or
  production security.
