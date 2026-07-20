#!/usr/bin/env bash
# Serve Qwen on local vLLM (OpenAI-compatible). No API key required.
set -euo pipefail

MODEL="${OLLIVE_OSS_MODEL:-Qwen/Qwen3.5-9B}"
PORT="${OLLIVE_VLLM_PORT:-8000}"
MAX_LEN="${OLLIVE_VLLM_MAX_LEN:-32768}"
TP="${OLLIVE_VLLM_TP:-1}"

# Prefer a dedicated vLLM env if present
if [[ -n "${CONDA_PREFIX:-}" ]] && command -v vllm >/dev/null 2>&1; then
  VLLM_BIN="$(command -v vllm)"
elif [[ -x "${HOME}/miniconda3/envs/aaai-vllm/bin/vllm" ]]; then
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate aaai-vllm
  VLLM_BIN="$(command -v vllm)"
else
  echo "vllm not found. Install/activate a vLLM environment first." >&2
  exit 1
fi

echo "Starting vLLM: model=${MODEL} port=${PORT}"
echo "Client should use VLLM_BASE_URL=http://localhost:${PORT}/v1  VLLM_API_KEY=EMPTY"

exec "${VLLM_BIN}" serve "${MODEL}" \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --tensor-parallel-size "${TP}" \
  --max-model-len "${MAX_LEN}" \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --served-model-name "${MODEL}"
