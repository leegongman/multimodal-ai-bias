# RunPod Reproduction Notes: Qwen2.5-VL-7B

Date: 2026-06-19

## Target

Generate a Multimodal 236722 `submission.csv` on the official-like GPU environment:

- GPU: NVIDIA RTX A6000 48GB
- Driver observed on RunPod: `550.127.08`
- CUDA runtime target: `12.4`
- Python: `3.10.x` (`uv python install 3.10` installed `3.10.18` on RunPod)
- Project path: `/workspace/multimodal-bias`
- Model: `Qwen/Qwen2.5-VL-7B-Instruct`
- Model config: `configs/models/qwen2_5_vl_7b.yaml`
- Engine: in-process Transformers `hf_local` (`model.generate`), not vLLM
- Prompt: `configs/prompts/reasoner_v2.yaml` (mapping-only fix)
- Output contract: keep the existing `FINAL_ANSWER_JSON` Reasoner JSON fields.

## Files To Upload

Upload the refreshed Qwen runtime bundle:

```text
multimodal-bias-runtime-qwen-reasoner-v2-20260619.zip
```

Do not use the older `multimodal-bias-runtime.zip` for this path; that bundle was created before the Qwen model config and Qwen GPU requirements file were added.

Minimal runtime zip contents:

```text
README.md
pyproject.toml
uv.lock
.python-version
conftest.py
configs/
src/
tests/
requirements-gpu-qwen2-5-vl-cu124.txt
```

Before uploading, verify the two Qwen-specific files are present:

```bash
unzip -l multimodal-bias-runtime-qwen-reasoner-v2-20260619.zip | grep -E 'reasoner_v2.yaml|qwen2_5_vl_7b.yaml|requirements-gpu-qwen2-5-vl-cu124.txt'
```

Official Multimodal data:

```text
open.zip
```

Do not upload:

```text
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
runs/
submissions/
models/snapshots/
```

## RunPod Setup

```bash
cd /workspace
mkdir -p multimodal-bias
cd multimodal-bias
unzip multimodal-bias-runtime-qwen-reasoner-v2-20260619.zip
mkdir -p data/raw/open data/processed models/snapshots runs submissions
touch data/raw/open/.gitkeep data/processed/.gitkeep models/snapshots/.gitkeep runs/.gitkeep submissions/.gitkeep
touch README.md
```

`/workspace/multimodal-bias/runs` must be backed by a RunPod persistent/network volume. An ephemeral container disk cannot preserve raw outputs after Pod deletion. Confirm the mount before inference and do not delete the Pod until the final checks below pass.

Install Python and base project dependencies:

```bash
uv python install 3.10
uv sync --python 3.10
```

Install GPU dependencies. Install PyTorch first, then install the pinned auxiliary stack with `--no-deps` so `torch` is not replaced:

```bash
uv pip install --force-reinstall \
  torch==2.6.0+cu124 \
  torchvision==0.21.0+cu124 \
  torchaudio==2.6.0+cu124 \
  --index-url https://download.pytorch.org/whl/cu124

uv pip install --force-reinstall --no-deps \
  -r requirements-gpu-qwen2-5-vl-cu124.txt
```

Verify GPU runtime:

```bash
uv run --no-sync python - <<'PY'
import torch, transformers, accelerate
print(torch.__version__, torch.version.cuda)
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0))
print(transformers.__version__)
print(accelerate.__version__)
PY
```

Expected:

```text
2.6.0+cu124 12.4
True
NVIDIA RTX A6000
4.51.0
1.6.0
```

## Data Setup

Upload `open.zip` to `/workspace/multimodal-bias/open.zip`, then:

```bash
cd /workspace/multimodal-bias
unzip open.zip -d data/raw/open
```

If the official CSV image paths are `./images/...`, rewrite them to the project-normalized paths:

```bash
python - <<'PY'
import csv
from pathlib import Path

def rewrite(csv_path: str, split: str) -> None:
    p = Path(csv_path)
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = []
        for row in reader:
            image_path = row["image_path"].strip()
            if image_path.startswith("./images/"):
                row["image_path"] = f"{split}/images/" + image_path.removeprefix("./images/")
            elif image_path.startswith("images/"):
                row["image_path"] = f"{split}/" + image_path
            rows.append(row)

    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

rewrite("data/raw/open/train/train.csv", "train")
rewrite("data/raw/open/test/test.csv", "test")
PY
```

Validate:

```bash
uv run --no-sync multimodal-bias validate-data --data-root data/raw/open
```

## Model Snapshot

Use a separate Hugging Face download environment so the project `.venv` is not modified:

```bash
uv venv /workspace/hf-download --python 3.10
uv pip install --python /workspace/hf-download/bin/python 'huggingface_hub[cli]' click

/workspace/hf-download/bin/hf download Qwen/Qwen2.5-VL-7B-Instruct \
  --local-dir models/snapshots/Qwen2.5-VL-7B-Instruct \
  --max-workers 4
```

## Full Inference

Current selected speed/quality setting:

```yaml
max_new_tokens: 512
```

Run:

```bash
uv run --no-sync multimodal-bias infer \
  --config configs/base.yaml \
  --model-config configs/models/qwen2_5_vl_7b.yaml
```

Progress check:

```bash
cd /workspace/multimodal-bias
RUN_ID=$(ls -t runs | head -1)

if [ -f "runs/$RUN_ID/raw_reasoner.partial.jsonl" ]; then
  FILE="runs/$RUN_ID/raw_reasoner.partial.jsonl"
elif [ -f "runs/$RUN_ID/raw_reasoner.jsonl" ]; then
  FILE="runs/$RUN_ID/raw_reasoner.jsonl"
else
  FILE=""
fi

DONE=0
[ -n "$FILE" ] && DONE=$(wc -l < "$FILE")
START=$(stat -c %Y "runs/$RUN_ID/config.resolved.yaml")
NOW=$(date +%s)
ELAPSED=$((NOW - START))

python - <<PY
done = int("$DONE")
elapsed = int("$ELAPSED")
total = 8500
print(f"RUN_ID=$RUN_ID")
print(f"DONE={done}/{total}")
if done > 0:
    sps = elapsed / done
    print(f"SEC_PER_SAMPLE={sps:.3f}")
    print(f"EST_TOTAL_MIN={sps * total / 60:.1f}")
    print(f"ETA_MIN={sps * (total - done) / 60:.1f}")
PY

nvidia-smi
```

Observed early speed on RunPod with Qwen2.5-VL-7B and `max_new_tokens: 512`:

```text
64 samples, about 0.125 sec/sample, projected about 17.7 minutes
```

This is well inside the 70-minute target if the generated records are valid.

## Submission

After inference completes:

```bash
RUN_ID=$(ls -t runs | head -1)

uv run --no-sync multimodal-bias make-submission \
  --config configs/base.yaml \
  --run-id "$RUN_ID"

wc -l "runs/$RUN_ID/submission.csv"
head "runs/$RUN_ID/submission.csv"
tail "runs/$RUN_ID/submission.csv"
```

Expected line count is `8501` including the header.

## Required Checks Before Upload

```bash
RUN_ID=$(ls -t runs | head -1)
ls -lh "runs/$RUN_ID"
wc -l "runs/$RUN_ID/raw_reasoner.jsonl"
wc -l "runs/$RUN_ID/parsed_reasoner.csv"
wc -l "runs/$RUN_ID/submission.csv"
tail -1 "runs/$RUN_ID/raw_reasoner.jsonl"
sha256sum \
  "runs/$RUN_ID/raw_reasoner.jsonl" \
  "runs/$RUN_ID/parsed_reasoner.csv" \
  "runs/$RUN_ID/submission.csv"
```

Confirm:

- `raw_reasoner.jsonl` has 8,500 records.
- `parsed_reasoner.csv` has 8,501 lines including header.
- `submission.csv` has 8,501 lines including header.
- Raw output status is `generated`, not `inference_failed`.
- Raw output contains the `FINAL_ANSWER_JSON` marker and required fields.
- Every generated row contains `prompt_text`, `prompt_sha256`, `image_sha256`, `image_byte_count`, and `image_format`.
- `raw_reasoner.partial.jsonl` is absent after normal completion. If inference was interrupted, preserve this partial file instead of treating it as a complete run.
- The run directory remains present after stopping the Pod because it is on persistent/network storage.
