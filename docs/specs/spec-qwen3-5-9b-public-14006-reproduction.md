---
title: 'Reproduce Multimodal codeshare 14006 with Qwen3.5-9B on RunPod'
type: 'feature'
created: '2026-06-22'
status: 'in-progress'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The existing `Qwen/Qwen3.5-9B + Reasoner v3` result scored about 0.94, while Multimodal codeshare 14006 reports 0.99517 with the same model family and a materially simpler inference prompt. We need a controlled reproduction to determine whether the prompt and inference contract explain the gap without exceeding the competition's 70-minute inference limit.

**Approach:** Preserve the downloaded codeshare notebook's model, prompt, preprocessing, deterministic generation, parsing, and fallback semantics while serving generation through a persistent vLLM engine on the supplied RTX A6000; use a separate no-clobber workspace and gate the 8,500-row run on a real-image smoke and measured throughput projection.

## Boundaries & Constraints

**Always:** Use only `Qwen/Qwen3.5-9B`; pin and record the exact model revision; use a persistent vLLM engine; use the exact notebook `/private/tmp/multimodal_qwen_14006.ipynb` with SHA-256 `8799847b3f306e551f166e9c2598438394d316b3a4bd4aa7a7a3db603b6e5da6` as the behavioral source of truth; preserve its six-rule system prompt, `enable_thinking=False`, BF16, `MAX_PIXELS=200704`, `MIN_PIXELS=50176`, deterministic generation, 200-token cap, answer parser, and unknown fallback; preserve raw outputs, submission, environment, timing, hashes, GPU telemetry, and exact commands; keep all prior runs immutable.

**Ask First:** Continue to all 8,500 rows if measured inference projection exceeds 70 minutes, smoke output is invalid, GPU memory is insufficient, or the vLLM path requires changing CUDA, model precision, image resolution, prompt, parser, or generation settings.

**Never:** Modify Reasoner v3, Gemma files or artifacts, other models, frozen stories or epics, test labels, competition samples, previous submissions, or the downloaded source notebook; use external inference APIs; tune against Public score; silently substitute labels or present a partial run as complete.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|---------------------------|----------------|
| Environment bootstrap | Empty `/workspace`, RTX A6000, `open.zip` | Isolated project/data/model environment with recorded versions and hashes | Preserve logs and stop on checksum, dependency, or model-load failure |
| Real-image smoke | Fixed first official test sample | Non-empty short reasoning and label parsed exactly as notebook logic | Stop before measured/full run on failure |
| Throughput gate | Fixed ordered subset using exact settings | Projection at or below 70 minutes with memory headroom | Stop and request approval if over budget or OOM |
| Full inference | 8,500 official rows after gates pass | 8,500 raw rows and valid `sample_id,label` submission in source order | Preserve partial artifacts; do not publish as complete |
| Parser miss | Output without a parseable label | Select detected uncertainty option exactly as notebook | Record fallback count and sample IDs |

</frozen-after-approval>

## Code Map

- `/private/tmp/multimodal_qwen_14006.ipynb` -- immutable downloaded codeshare 14006 and behavioral reference.
- `scripts/run_qwen35_v3_vllm.py` -- existing v3 runner used only as comparison context; must not be changed.
- `scripts/run_inference_14006_vllm.py` -- persistent vLLM reproduction runner preserving the public prompt and parser semantics.
- `requirements-gpu-qwen3-5-cu124.txt` -- existing dependency evidence; use only if compatible with the notebook's Transformers path.
- `open.zip` -- official competition data archive, SHA-256 `5e291b17927910d33bfc45aaaa4fcc324cb9e962c32d99abd7b4dc8795603d48`.
- RunPod `/workspace/multimodal-14006-repro/` -- isolated remote source, data, logs, and output root.

## Tasks & Acceptance

**Execution:**
- [ ] RunPod `/workspace/multimodal-14006-repro/` -- record OS/GPU/disk state and create a no-clobber experiment root.
- [ ] Notebook/data transfer -- copy and checksum the exact notebook and official data archive.
- [ ] RunPod environment -- install a compatible isolated vLLM runtime and pin/download `Qwen/Qwen3.5-9B` with revision evidence.
- [ ] Reproduction runner -- execute the public prompt and parser semantics through a persistent vLLM engine while adding resumable logging, hashes, and telemetry.
- [ ] Smoke/subset/full artifacts -- run gates in order and execute 8,500 rows only when the measured projection is within 70 minutes.
- [ ] Validation -- verify row count, order, labels, nulls, label distribution, fallback count, duration, and SHA-256 values.

**Acceptance Criteria:**
- Given the immutable notebook and official data, when the remote smoke runs, then model serialization, prompt text, image limits, generation settings, and parser behavior match codeshare 14006.
- Given the measured subset, when runtime is projected to 8,500 rows, then the full run starts only at or below 70 minutes with no correctness or memory failure.
- Given a completed full run, when validation finishes, then submission has exactly 8,500 unique ordered sample IDs, labels only in `{0,1,2}`, no nulls, preserved raw outputs, and recorded hashes and runtime evidence.

## Spec Change Log

## Design Notes

The reproduction isolates prompt/pipeline effects from model-family effects. The exact public prompt is intentionally not merged into Reasoner v3 during this experiment. Per the user's runtime correction, vLLM replaces the notebook's direct Transformers generation while semantic settings remain fixed. Any later Gemma transfer is a separate experiment.

## Verification

**Commands:**
- `sha256sum multimodal_qwen_14006.ipynb open.zip` -- expected: hashes match the frozen values above.
- Remote fixed real-image smoke -- expected: successful BF16 model load, non-empty decoded output, parser label in `{0,1,2}`, and no OOM.
- Remote measured subset -- expected: recorded wall time, per-sample time, peak VRAM, fallback count, and projected 8,500-row duration no greater than 4,200 seconds.
- Remote final validator -- expected: 8,500 raw records, 8,501 CSV lines including header, unique ordered sample IDs, no nulls, valid labels, and output SHA-256 values.
