#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/env.sh"

curl -fsS "$VLLM_BASE_URL/health" >/dev/null || { echo "ERROR: vLLM is not healthy" >&2; exit 1; }
[[ -f "$DATA_ROOT/test/test.csv" ]] || { echo "ERROR: missing $DATA_ROOT/test/test.csv" >&2; exit 1; }
[[ -d "$DATA_ROOT/test/images" ]] || { echo "ERROR: missing $DATA_ROOT/test/images" >&2; exit 1; }
mkdir -p "$RUNS_DIR"
export PYTHONPATH="$BUNDLE_ROOT/runtime/src"

one_run="${PROFILE_SLUG}_v3_smoke_$(date -u +%Y%m%dT%H%M%SZ)"
"$PYTHON" "$BUNDLE_ROOT/runtime/scripts/$RUNNER_SCRIPT" \
  --data-root "$DATA_ROOT" \
  --prompt-template "$BUNDLE_ROOT/runtime/configs/prompts/reasoner_v3.yaml" \
  --output-dir "$RUNS_DIR/$one_run" \
  --model-revision "$MODEL_REVISION" \
  --limit 1 \
  --concurrency 1 \
  --initial-max-tokens 256 \
  --retry-max-tokens 512
"$PYTHON" "$BUNDLE_ROOT/validate_run.py" "$RUNS_DIR/$one_run" \
  --expected-rows 1 --profile "$GEMMA_PROFILE"

subset_run="${PROFILE_SLUG}_v3_${SMOKE_ROWS}_c32_$(date -u +%Y%m%dT%H%M%SZ)"
"$PYTHON" "$BUNDLE_ROOT/runtime/scripts/$RUNNER_SCRIPT" \
  --data-root "$DATA_ROOT" \
  --prompt-template "$BUNDLE_ROOT/runtime/configs/prompts/reasoner_v3.yaml" \
  --output-dir "$RUNS_DIR/$subset_run" \
  --model-revision "$MODEL_REVISION" \
  --limit "$SMOKE_ROWS" \
  --concurrency 32 \
  --initial-max-tokens 256 \
  --retry-max-tokens 512
"$PYTHON" "$BUNDLE_ROOT/validate_run.py" "$RUNS_DIR/$subset_run" \
  --expected-rows "$SMOKE_ROWS" --profile "$GEMMA_PROFILE"
echo "OK: real-image smoke and ${SMOKE_ROWS}-row c32 gate passed for $GEMMA_PROFILE"
