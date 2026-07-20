# Ollive installation and model downloads

This guide keeps the Streamlit application and the vLLM GPU server in separate
Python environments. The application can also run against the OpenAI frontier
backend without installing vLLM or downloading Qwen.

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

## 3. Install the vLLM server

Skip this section when using only the frontier backend.

Create a dedicated environment so vLLM can manage its own PyTorch and CUDA
dependencies:

```bash
conda create -n ollive-vllm python=3.11 -y
conda activate ollive-vllm
python -m pip install --upgrade pip
python -m pip install -r requirements-vllm.txt
vllm --version
```

If vLLM cannot find a compatible wheel, consult the vLLM installation guidance
for the CUDA version installed on the machine. Do not install the application
requirements into this environment.

## 4. Download the models

The first index build automatically downloads the embedding model, and the first
vLLM launch automatically downloads Qwen. To download both ahead of time:

```bash
conda activate ollive-vllm
hf auth login                     # optional for public models
hf download Qwen/Qwen3.5-9B
```

Then download the embedding model from the application environment:

```bash
conda activate ollive
hf download BAAI/bge-small-en-v1.5
```

Hugging Face stores the files in its shared cache. Set `HF_HOME` in `.env` or
the shell before downloading if the cache must live on a larger disk.

To serve a pre-downloaded model from a specific directory, set
`OLLIVE_OSS_MODEL=/absolute/path/to/model` before starting the server.

## 5. Start Qwen through vLLM

With the vLLM environment active:

```bash
conda activate ollive-vllm
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

## 6. Build the knowledge index

In the application environment:

```bash
conda activate ollive
python scripts/build_index.py
```

This downloads `BAAI/bge-small-en-v1.5` when necessary and writes the FAISS
index under `data/indexes/`.

Rebuild the index whenever documents in `assignment_kb/` change.

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
