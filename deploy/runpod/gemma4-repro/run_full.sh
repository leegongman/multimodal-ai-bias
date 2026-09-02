#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/env.sh"

curl -fsS "$VLLM_BASE_URL/health" >/dev/null || { echo "ERROR: vLLM is not healthy" >&2; exit 1; }
[[ -f "$DATA_ROOT/test/test.csv" ]] || { echo "ERROR: missing official test.csv" >&2; exit 1; }
mkdir -p "$RUNS_DIR"
run_id="${RUN_ID:-${PROFILE_SLUG}_v3_full_c32_$(date -u +%Y%m%dT%H%M%SZ)}"
output_dir="$RUNS_DIR/$run_id"
[[ ! -e "$output_dir" ]] || { echo "ERROR: run directory already exists: $output_dir" >&2; exit 1; }
export PYTHONPATH="$BUNDLE_ROOT/runtime/src"

"$PYTHON" "$BUNDLE_ROOT/runtime/scripts/$RUNNER_SCRIPT" \
  --data-root "$DATA_ROOT" \
  --prompt-template "$BUNDLE_ROOT/runtime/configs/prompts/reasoner_v3.yaml" \
  --output-dir "$output_dir" \
  --model-revision "$MODEL_REVISION" \
  --concurrency 32 \
  --initial-max-tokens 256 \
  --retry-max-tokens 512

"$PYTHON" "$BUNDLE_ROOT/validate_run.py" "$output_dir" \
  --expected-rows 8500 \
  --profile "$GEMMA_PROFILE" \
  --data-root "$DATA_ROOT"
echo "OK: validated submission at $output_dir/submission.csv"
