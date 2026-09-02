#!/usr/bin/env bash

set -euo pipefail

BUNDLE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace/multimodal-bias}"
VENV_DIR="${VENV_DIR:-/workspace/gemma4-vllm-cu129}"
GEMMA_PROFILE="${GEMMA_PROFILE:-gemma4-26b-a4b-awq}"
profile_path="$BUNDLE_ROOT/profiles/$GEMMA_PROFILE.sh"
[[ -f "$profile_path" ]] || {
  echo "ERROR: unknown GEMMA_PROFILE=$GEMMA_PROFILE" >&2
  echo "Available: gemma4-26b-a4b-awq, gemma4-12b" >&2
  return 1 2>/dev/null || exit 1
}
source "$profile_path"
MODEL_DIR="${MODEL_DIR:-${WORKSPACE_ROOT}/models/snapshots/${MODEL_DIR_NAME}}"
DATA_ROOT="${DATA_ROOT:-${WORKSPACE_ROOT}/data/raw/open}"
RUNS_DIR="${RUNS_DIR:-${WORKSPACE_ROOT}/runs}"
VLLM_HOST="127.0.0.1"
VLLM_PORT="8000"
VLLM_BASE_URL="http://${VLLM_HOST}:${VLLM_PORT}"
PYTHON="${VENV_DIR}/bin/python"

export BUNDLE_ROOT WORKSPACE_ROOT VENV_DIR MODEL_DIR DATA_ROOT RUNS_DIR GEMMA_PROFILE
export PROFILE_SLUG MODEL_ID MODEL_REVISION MODEL_ARCHITECTURES RUNNER_SCRIPT SMOKE_ROWS
export VLLM_GENERATION_CONFIG
export VLLM_HOST VLLM_PORT VLLM_BASE_URL PYTHON
