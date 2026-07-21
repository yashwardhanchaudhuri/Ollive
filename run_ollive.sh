#!/usr/bin/env bash
# Create or update Ollive's single Conda environment, then run the selected local setup.
# Usage: ./run_ollive.sh [oss|frontier]
set -euo pipefail

MODE="${1:-oss}"
case "${MODE}" in
  oss|frontier) ;;
  *)
    echo "Usage: $0 [oss|frontier]" >&2
    exit 2
    ;;
esac

LAUNCHER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${OLLIVE_ROOT:-${LAUNCHER_DIR}}"

if [[ ! -f "${ROOT}/environment.yml" ]]; then
  echo "Ollive repository not found at ${ROOT}. Set OLLIVE_ROOT to its path." >&2
  exit 1
fi

ENV_NAME="${OLLIVE_ENV_NAME:-ollive}"
STREAMLIT_HOST="${OLLIVE_STREAMLIT_HOST:-127.0.0.1}"
STREAMLIT_PORT="${OLLIVE_STREAMLIT_PORT:-8501}"
VLLM_HOST="${OLLIVE_VLLM_HOST:-127.0.0.1}"
VLLM_PORT="${OLLIVE_VLLM_PORT:-8000}"
VLLM_URL="http://${VLLM_HOST}:${VLLM_PORT}/v1"
VLLM_LOG="${ROOT}/data/vllm.log"

cd "${ROOT}"

if ! command -v conda >/dev/null 2>&1; then
  echo "Conda or Miniconda is required. Install it, then rerun this launcher." >&2
  exit 1
fi

# Make conda activate-style commands available in a non-interactive shell.
# shellcheck disable=SC1091
source "$(conda info --base)/etc/profile.d/conda.sh"

if conda env list | awk 'NR > 2 {print $1}' | grep -Fxq "${ENV_NAME}"; then
  echo "Updating Conda environment: ${ENV_NAME}"
  conda env update --name "${ENV_NAME}" --file environment.yml
else
  echo "Creating Conda environment: ${ENV_NAME}"
  conda env create --name "${ENV_NAME}" --file environment.yml
fi

conda run --no-capture-output --name "${ENV_NAME}" \
  python -m pip install --editable . --no-deps

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Add optional provider keys there when needed."
fi
CONFIGURED_BACKEND="$(conda run --no-capture-output --name "${ENV_NAME}" python -c 'from ollive.application.config import load_config; print(load_config()["active"])')"
if [[ "${MODE}" != "${CONFIGURED_BACKEND}" ]]; then
  echo "Launcher mode '${MODE}' does not match config/backends.yaml active '${CONFIGURED_BACKEND}'." >&2
  echo "Edit the YAML active field, then rerun the launcher." >&2
  exit 1
fi

if [[ ! -f data/indexes/faiss.index || ! -f data/indexes/chunks.pkl || ! -f data/indexes/meta.json ]]; then
  echo "Building the local knowledge-base index (first run downloads the embedding model)."
  conda run --no-capture-output --name "${ENV_NAME}" python scripts/build_index.py
fi

VLLM_PID=""
cleanup() {
  if [[ -n "${VLLM_PID}" ]] && kill -0 "${VLLM_PID}" 2>/dev/null; then
    echo "Stopping the vLLM process started by this launcher."
    kill "${VLLM_PID}" 2>/dev/null || true
    wait "${VLLM_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [[ "${MODE}" == "oss" ]]; then
  export VLLM_BASE_URL="${VLLM_URL}"
  export VLLM_API_KEY="${VLLM_API_KEY:-EMPTY}"
  export OLLIVE_VLLM_HOST="${VLLM_HOST}"
  export OLLIVE_VLLM_PORT="${VLLM_PORT}"

  if curl --fail --silent --show-error "${VLLM_URL}/models" >/dev/null; then
    echo "Using the healthy vLLM service already listening at ${VLLM_URL}."
  else
    if ! command -v nvidia-smi >/dev/null 2>&1; then
      echo "The OSS mode needs a supported NVIDIA GPU and nvidia-smi." >&2
      exit 1
    fi
    mkdir -p data
    echo "Starting local Qwen/vLLM; its first launch downloads the model."
    conda run --no-capture-output --name "${ENV_NAME}" \
      bash scripts/serve_qwen_vllm.sh >"${VLLM_LOG}" 2>&1 &
    VLLM_PID=$!

    echo "Waiting for vLLM at ${VLLM_URL} (up to ${OLLIVE_VLLM_READY_TIMEOUT:-600}s)."
    deadline=$((SECONDS + ${OLLIVE_VLLM_READY_TIMEOUT:-600}))
    until curl --fail --silent "${VLLM_URL}/models" >/dev/null; do
      if (( SECONDS >= deadline )); then
        echo "vLLM did not become ready. Recent log output:" >&2
        tail -n 40 "${VLLM_LOG}" >&2 || true
        exit 1
      fi
      if ! kill -0 "${VLLM_PID}" 2>/dev/null; then
        echo "vLLM exited before it became ready. Recent log output:" >&2
        tail -n 40 "${VLLM_LOG}" >&2 || true
        exit 1
      fi
      sleep 2
    done
  fi
else
  if [[ -z "${OPENAI_API_KEY:-}" ]] && ! grep -Eq '^[[:space:]]*OPENAI_API_KEY=[^[:space:]#]+' .env; then
    echo "Frontier mode requires OPENAI_API_KEY in .env or the shell environment." >&2
    exit 1
  fi
fi

STREAMLIT_URL="http://${STREAMLIT_HOST}:${STREAMLIT_PORT}"
if curl --fail --silent "${STREAMLIT_URL}/_stcore/health" >/dev/null; then
  echo "Using the healthy Streamlit service already listening at ${STREAMLIT_URL}."
  exit 0
fi

echo "Starting Ollive (${MODE}) at ${STREAMLIT_URL}"
conda run --no-capture-output --name "${ENV_NAME}" \
  streamlit run src/ollive/ui/streamlit_app.py \
  --server.address "${STREAMLIT_HOST}" \
  --server.port "${STREAMLIT_PORT}"
