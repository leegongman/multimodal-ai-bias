#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/env.sh"

command -v nvidia-smi >/dev/null || { echo "ERROR: nvidia-smi not found" >&2; exit 1; }
available_kib="$(df -Pk /workspace | awk 'NR==2 {print $4}')"
(( available_kib >= 45 * 1024 * 1024 )) || {
  echo "ERROR: at least 45 GiB free under /workspace is required" >&2
  exit 1
}
gpu_name="$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n1)"
driver="$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -n1)"
[[ "$gpu_name" == "NVIDIA RTX A6000" ]] || {
  echo "ERROR: proven hardware is NVIDIA RTX A6000; found: $gpu_name" >&2
  exit 1
}
[[ "$driver" == "550.127.08" ]] || {
  echo "ERROR: proven driver is 550.127.08; found: $driver" >&2
  exit 1
}

python_bin="${PYTHON_BOOTSTRAP:-python3.12}"
command -v "$python_bin" >/dev/null || {
  echo "ERROR: Python 3.12 is required (set PYTHON_BOOTSTRAP if needed)" >&2
  exit 1
}

if [[ ! -x "$PYTHON" ]]; then
  "$python_bin" -m venv "$VENV_DIR"
fi

"$PYTHON" -m pip install --upgrade "pip==26.0.1" "setuptools==80.10.2"
"$PYTHON" -m pip install -r "$BUNDLE_ROOT/requirements-critical.txt" \
  --constraint "$BUNDLE_ROOT/provenance/pip-freeze-proven.txt" \
  --extra-index-url https://download.pytorch.org/whl/cu129

PATH="$VENV_DIR/bin:$PATH" "$PYTHON" "$BUNDLE_ROOT/verify_environment.py"
echo "OK: environment ready at $VENV_DIR"
