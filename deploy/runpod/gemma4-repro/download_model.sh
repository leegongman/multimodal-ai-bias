#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/env.sh"

[[ -x "$PYTHON" ]] || { echo "ERROR: run bootstrap.sh first" >&2; exit 1; }
mkdir -p "$(dirname "$MODEL_DIR")"

if [[ -f "$MODEL_DIR/.model-revision" ]]; then
  [[ "$(<"$MODEL_DIR/.model-revision")" == "$MODEL_REVISION" ]] || {
    echo "ERROR: existing model revision marker does not match $MODEL_REVISION" >&2
    exit 1
  }
else
  MODEL_ID="$MODEL_ID" MODEL_REVISION="$MODEL_REVISION" MODEL_DIR="$MODEL_DIR" "$PYTHON" - <<'PY'
import os
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id=os.environ["MODEL_ID"],
    revision=os.environ["MODEL_REVISION"],
    local_dir=os.environ["MODEL_DIR"],
)
PY
  printf '%s\n' "$MODEL_REVISION" > "$MODEL_DIR/.model-revision"
fi

MODEL_DIR="$MODEL_DIR" MODEL_REVISION="$MODEL_REVISION" MODEL_ARCHITECTURES="$MODEL_ARCHITECTURES" "$PYTHON" - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["MODEL_DIR"])
required = ["config.json", "tokenizer.json", "model.safetensors.index.json"]
missing = [name for name in required if not (root / name).is_file()]
if missing:
    raise SystemExit(f"ERROR: model snapshot is incomplete: {missing}")
config = json.loads((root / "config.json").read_text())
architectures = config.get("architectures", [])
expected_architectures = set(os.environ["MODEL_ARCHITECTURES"].split(","))
if not expected_architectures.intersection(architectures):
    raise SystemExit(f"ERROR: unexpected model architecture: {architectures}")
marker = (root / ".model-revision").read_text().strip()
if marker != os.environ["MODEL_REVISION"]:
    raise SystemExit(f"ERROR: revision marker mismatch: {marker}")
print("OK: exact selected Gemma 4 model snapshot verified")
PY
