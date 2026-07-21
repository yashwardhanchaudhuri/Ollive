#!/usr/bin/env bash
# Serve Qwen on local vLLM (OpenAI-compatible). No API key required.
set -euo pipefail

MODEL="${OLLIVE_OSS_MODEL:-Qwen/Qwen3.5-9B}"
# Loopback is the safe default; network exposure requires an explicit override.
PORT="${OLLIVE_VLLM_PORT:-8000}"
HOST="${OLLIVE_VLLM_HOST:-127.0.0.1}"
MAX_LEN="${OLLIVE_VLLM_MAX_LEN:-32768}"
TP="${OLLIVE_VLLM_TP:-1}"
# Disable FlashInfer sampling by default because the supported GPU/runtime is more
# reliable with vLLM's standard sampler.
export VLLM_USE_FLASHINFER_SAMPLER="${OLLIVE_VLLM_USE_FLASHINFER_SAMPLER:-0}"

if ! command -v vllm >/dev/null 2>&1; then
  echo "vllm not found in the active environment." >&2
  echo "Activate ollive and install requirements.txt." >&2
  exit 1
fi
VLLM_BIN="$(command -v vllm)"

echo "Starting vLLM: model=${MODEL} port=${PORT}"
echo "Client should use VLLM_BASE_URL=http://localhost:${PORT}/v1  VLLM_API_KEY=EMPTY"

exec "${VLLM_BIN}" serve "${MODEL}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --tensor-parallel-size "${TP}" \
  --max-model-len "${MAX_LEN}" \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --served-model-name "${MODEL}"
