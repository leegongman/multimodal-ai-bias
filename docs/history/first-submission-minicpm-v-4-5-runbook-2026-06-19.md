# First Submission Runbook: MiniCPM-V-4_5

> **ARCHIVED / FROZEN — DO NOT EXECUTE:** 이 문서는 미래 참고용으로만 보존한다. 현재 활성 모델은 Qwen2.5-VL-7B뿐이며, MiniCPM-V 4.5 다운로드·설정 변경·로드·smoke·추론·제출은 사용자가 MiniCPM-V 4.5를 명시적으로 해제하기 전까지 금지한다. 이 문서의 과거 “selected/current” 표현은 현재 지시가 아니다. [`../AGENTS.md`](../AGENTS.md)가 우선한다.

Date: 2026-06-19

## Current Position

- BMad implementation baseline is complete through Epic 2 submission pipeline.
- Story 3.2 is paused; first submission should use the Reasoner-only path first.
- Selected first performance attempt model: `openbmb/MiniCPM-V-4_5`.
- Local model config: `configs/models/minicpm_v_4_5.yaml`.
- Local model snapshot is downloaded under `models/snapshots/MiniCPM-V-4_5`.
- Snapshot commit fixed in config: `fd3209b2e0580e346fc33d2c6f85b6e9332eecda`.
- Official Multimodal data is not present yet under `data/raw/open`.

## GPU-Free Preparation

These steps do not require GPU:

1. Download the MiniCPM-V-4_5 Hugging Face snapshot into:
   `models/snapshots/MiniCPM-V-4_5`
2. Confirm the four weight shards exist:
   `model-00001-of-00004.safetensors` through `model-00004-of-00004.safetensors`
3. Replace `snapshot_hash` in `configs/models/minicpm_v_4_5.yaml` with the downloaded revision or snapshot commit if available.
4. Place the official Multimodal open data under:
   `data/raw/open`

Items 1-3 are complete. Item 4 is the current blocker before `validate-data` can pass.

Expected official data layout:

```text
data/raw/open/
  train/
  train/images/
  train/train.csv
  test/
  test/images/
  test/test.csv
  sample_submission.csv
```

Validate after the data is present:

```bash
uv run multimodal-bias validate-data --data-root data/raw/open
```

## GPU Boundary

GPU is first needed when the local VLM is actually loaded or used:

```bash
uv run multimodal-bias smoke-model \
  --model-config configs/models/minicpm_v_4_5.yaml \
  --image-path data/raw/open/test/images/<existing-test-image>.jpg
```

If `smoke-model` passes, run full inference on the GPU machine:

```bash
uv run multimodal-bias infer \
  --config configs/base.yaml \
  --model-config configs/models/minicpm_v_4_5.yaml
```

Then create the Multimodal submission from the generated run:

```bash
uv run multimodal-bias make-submission \
  --config configs/base.yaml \
  --run-id <generated-run-id>
```

## Stop Conditions

- Do not start `smoke-model`, `infer`, or full submission generation until the user gives a GPU execution order.
- Do not generate a real `submission.csv` until official `data/raw/open` is present and `validate-data` passes.
- Do not continue Story 3.2 verifier work until the first Reasoner-only submission path has produced a baseline.
