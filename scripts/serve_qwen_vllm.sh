#!/usr/bin/env bash
# Serve Qwen on local vLLM (OpenAI-compatible). No API key required.
set -euo pipefail

require_positive_integer() {
  local name="$1" value="$2"
  if [[ ! "${value}" =~ ^[0-9]+$ ]] || (( 10#${value} < 1 )); then
    echo "${name} must be a positive integer; received '${value}'." >&2
    exit 2
  fi
}

MODEL="${OLLIVE_OSS_MODEL:-Qwen/Qwen3.5-9B}"
# Loopback is the safe default; network exposure requires an explicit override.
PORT="${OLLIVE_VLLM_PORT:-8000}"
HOST="${OLLIVE_VLLM_HOST:-127.0.0.1}"
MAX_LEN="${OLLIVE_VLLM_MAX_LEN:-32768}"
TP="${OLLIVE_VLLM_TP:-1}"
QUANTIZATION="${OLLIVE_VLLM_QUANTIZATION:-fp8}"
# Disable FlashInfer sampling by default because the supported GPU/runtime is more
# reliable with vLLM's standard sampler.
export VLLM_USE_FLASHINFER_SAMPLER="${OLLIVE_VLLM_USE_FLASHINFER_SAMPLER:-0}"

if [[ ! "${PORT}" =~ ^[0-9]{1,5}$ ]] || (( 10#${PORT} < 1 || 10#${PORT} > 65535 )); then
  echo "OLLIVE_VLLM_PORT must be an integer from 1 to 65535; received '${PORT}'." >&2
  exit 2
fi
require_positive_integer OLLIVE_VLLM_MAX_LEN "${MAX_LEN}"
require_positive_integer OLLIVE_VLLM_TP "${TP}"


if ! command -v vllm >/dev/null 2>&1; then
  echo "vllm not found in the active environment." >&2
  echo "Activate ollive and install requirements.txt." >&2
  exit 1
fi
VLLM_BIN="$(command -v vllm)"

echo "Starting vLLM: model=${MODEL} port=${PORT} quantization=${QUANTIZATION}"
echo "Client should use VLLM_BASE_URL=http://localhost:${PORT}/v1  VLLM_API_KEY=EMPTY"

exec "${VLLM_BIN}" serve "${MODEL}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --tensor-parallel-size "${TP}" \
  --max-model-len "${MAX_LEN}" \
  --quantization "${QUANTIZATION}" \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --served-model-name "${MODEL}"
