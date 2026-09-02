#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/env.sh"

PATH="$VENV_DIR/bin:$PATH" "$PYTHON" "$BUNDLE_ROOT/verify_environment.py"
[[ -f "$MODEL_DIR/.model-revision" ]] || { echo "ERROR: run download_model.sh first" >&2; exit 1; }
[[ "$(<"$MODEL_DIR/.model-revision")" == "$MODEL_REVISION" ]] || {
  echo "ERROR: model revision mismatch" >&2; exit 1;
}
mkdir -p "$RUNS_DIR"

if curl -fsS "$VLLM_BASE_URL/health" >/dev/null 2>&1; then
  models="$(curl -fsS "$VLLM_BASE_URL/v1/models")"
  if [[ "$models" == *"\"id\":\"$MODEL_ID\""* ]]; then
    echo "OK: exact Gemma vLLM server is already healthy; reusing it"
    exit 0
  fi
  echo "ERROR: port $VLLM_PORT serves a different model" >&2
  exit 1
fi

log_path="$RUNS_DIR/${PROFILE_SLUG}_vllm_server.log"
pid_path="$RUNS_DIR/${PROFILE_SLUG}_vllm_server.pid"
nohup env PATH="$VENV_DIR/bin:$PATH" \
  "$VENV_DIR/bin/vllm" serve "$MODEL_DIR" \
  --served-model-name "$MODEL_ID" \
  --host "$VLLM_HOST" \
  --port "$VLLM_PORT" \
  --tensor-parallel-size 1 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.90 \
  --generation-config "$VLLM_GENERATION_CONFIG" \
  >"$log_path" 2>&1 < /dev/null &
server_pid=$!
printf '%s\n' "$server_pid" > "$pid_path"

for _ in $(seq 1 90); do
  if ! kill -0 "$server_pid" 2>/dev/null; then
    echo "ERROR: vLLM exited during startup" >&2
    tail -n 100 "$log_path" >&2
    exit 1
  fi
  status="$(curl -sS -o /tmp/gemma-health-body -w '%{http_code}' "$VLLM_BASE_URL/health" || true)"
  if [[ "$status" == "200" ]]; then
    models="$(curl -fsS "$VLLM_BASE_URL/v1/models")"
    MODEL_ID="$MODEL_ID" MODELS_JSON="$models" "$PYTHON" - <<'PY'
import json
import os

payload = json.loads(os.environ["MODELS_JSON"])
ids = {item["id"] for item in payload.get("data", [])}
if os.environ["MODEL_ID"] not in ids:
    raise SystemExit(f"ERROR: served model ID missing: {ids}")
PY
    echo "OK: $GEMMA_PROFILE vLLM server ready (PID $server_pid, log $log_path)"
    exit 0
  fi
  if [[ "$status" == "500" ]]; then
    echo "ERROR: vLLM API returned HTTP 500; verify FastAPI/Starlette/instrumentator pins" >&2
    tail -n 100 "$log_path" >&2
    exit 1
  fi
  sleep 5
done

echo "ERROR: vLLM health check timed out" >&2
tail -n 100 "$log_path" >&2
exit 1
