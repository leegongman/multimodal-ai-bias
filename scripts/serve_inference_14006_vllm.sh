#!/usr/bin/env bash

set -euo pipefail

ROOT="${Multimodal_14006_ROOT:-/workspace/multimodal-14006-repro}"
VENV="${VLLM_VENV:-$ROOT/.venv-vllm-cu129}"
MODEL_DIR="${MODEL_DIR:-$ROOT/model/Qwen3.5-9B}"
MODEL_ID="Qwen/Qwen3.5-9B"
PORT="${VLLM_PORT:-8000}"
LOG="$ROOT/logs/qwen35-9b-vllm-server.log"
PID_FILE="$ROOT/logs/qwen35-9b-vllm-server.pid"

[[ -x "$VENV/bin/vllm" ]] || { echo "missing vLLM environment: $VENV" >&2; exit 1; }
[[ -f "$MODEL_DIR/config.json" ]] || { echo "missing model: $MODEL_DIR" >&2; exit 1; }

if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  models="$(curl -fsS "http://127.0.0.1:$PORT/v1/models")"
  [[ "$models" == *"\"id\":\"$MODEL_ID\""* ]] || {
    echo "port $PORT serves a different model" >&2
    exit 1
  }
  echo "vLLM server already ready"
  exit 0
fi

nohup env PATH="$VENV/bin:$PATH" \
  "$VENV/bin/vllm" serve "$MODEL_DIR" \
  --served-model-name "$MODEL_ID" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --tensor-parallel-size 1 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.90 \
  --generation-config vllm \
  --mm-processor-kwargs '{"max_pixels":200704,"min_pixels":50176}' \
  >"$LOG" 2>&1 < /dev/null &
pid=$!
printf '%s\n' "$pid" > "$PID_FILE"

for _ in $(seq 1 120); do
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "vLLM exited during startup" >&2
    tail -n 120 "$LOG" >&2
    exit 1
  fi
  status="$(curl -sS -o /tmp/qwen35-health-body -w '%{http_code}' "http://127.0.0.1:$PORT/health" || true)"
  if [[ "$status" == "200" ]]; then
    models="$(curl -fsS "http://127.0.0.1:$PORT/v1/models")"
    [[ "$models" == *"\"id\":\"$MODEL_ID\""* ]] || {
      echo "served model ID mismatch" >&2
      exit 1
    }
    echo "vLLM server ready (PID $pid)"
    exit 0
  fi
  sleep 5
done

echo "vLLM health timeout" >&2
tail -n 120 "$LOG" >&2
exit 1
