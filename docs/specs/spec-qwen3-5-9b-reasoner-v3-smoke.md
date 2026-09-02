---
title: 'Run Qwen3.5-9B with Reasoner v3 on RTX A6000'
type: 'feature'
created: '2026-06-20'
status: 'in-progress'
baseline_commit: 'NO_VCS'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The project has no real Qwen3.5-9B Reasoner v3 result, so its quality, strict-output reliability, memory fit, and compliance with the A6000 70-minute target are unknown.

**Approach:** Add the minimum Qwen3.5-9B local configuration and non-thinking serialization support, then use the supplied RunPod RTX A6000 for a real-image smoke, a measured small run, and—only after those gates pass—the 8,500-row v3 inference and validated submission artifact.

## Boundaries & Constraints

**Always:** Use only the official `Qwen/Qwen3.5-9B` checkpoint with an exact pinned revision; keep Reasoner v3 prompt/schema unchanged; disable thinking; use one deterministic generation pass with no Verifier; use official processor/chat-template serialization; preserve raw outputs, hashes, latency, GPU/VRAM metadata, parsed records, and no-clobber artifacts; execute locally on the supplied RTX A6000 after the one-time snapshot download.

**Ask First:** Any change to CUDA, Ubuntu, or Python; use of a non-official quantization; destructive cleanup; continuing to the full run if the measured projection exceeds 70 minutes or v3 parsing is not reliable.

**Never:** Touch or run another model, frozen Story/Epic implementation, Reasoner v4, Verifier/arbitration, remote inference APIs, fallback labels, rule-based final answers, existing run artifacts, or unrelated dependencies and source files.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|----------------------------|----------------|
| Real-image smoke | Official local snapshot, one test image, v3 prompt | Valid `reasoner_output_v3`, evidence hashes, latency and A6000 telemetry | Reject explicitly; do not invent a label |
| Small measured run | Fixed ordered subset, single-pass non-thinking | Stable per-sample/runtime projection and parse statistics | Stop before full inference if projection or reliability gate fails |
| Full run | 8,500 ordered samples after gates pass | Raw 8,500 rows, parsed/submission 8,501 lines, deterministic hashes | Preserve partial output and publish no submission on failure |
| Environment mismatch | Unsupported model class/package/CUDA requirement | Concise compatibility failure with exact dependency context | Do not alter the fixed CUDA/OS/Python environment |

</frozen-after-approval>

## Code Map

- `configs/models/qwen3_5_9b.yaml` -- pinned local Qwen3.5 model configuration.
- `src/multimodal_bias/models/hf_vlm.py` -- official multimodal template and non-thinking generation boundary.
- `tests/test_model_adapter.py` -- CPU-safe proof that Qwen3.5 receives `enable_thinking=False` without changing other model behavior.
- `requirements-gpu-qwen3-5-cu124.txt` -- isolated A6000-compatible model runtime dependencies.
- `configs/prompts/reasoner_v3.yaml` -- immutable prompt/output contract used by every run.

## Tasks & Acceptance

**Execution:**
- [ ] `configs/models/qwen3_5_9b.yaml` -- add the exact official model class, local snapshot, BF16, deterministic short-output settings.
- [ ] `src/multimodal_bias/models/hf_vlm.py`, `tests/test_model_adapter.py` -- pass the official Qwen3.5 non-thinking template option and retain fail-closed output handling.
- [ ] `requirements-gpu-qwen3-5-cu124.txt` -- pin only the packages required by Qwen3.5 in the fixed RunPod environment.
- [ ] RunPod `/workspace/multimodal-bias` -- upload the minimal runtime and official data, install dependencies, pin/download the official snapshot, and verify offline loading.
- [ ] RunPod run artifacts -- execute real-image smoke and a small measured subset; if gates pass, execute full inference, parsing, and submission validation.

**Acceptance Criteria:**
- Given the pinned official snapshot on RTX A6000, when the adapter loads offline, then it uses the official Qwen3.5 processor/model classes without API calls or CPU/disk offload.
- Given a real image and unchanged v3 prompt, when single-pass non-thinking generation completes, then strict v3 parsing succeeds and records model, prompt, image, runtime, and GPU evidence.
- Given the measured small run, when throughput is projected, then the 8,500-row total is at most 70 minutes with operational headroom and parse failures are zero before full inference is authorized.
- Given a successful full run, when submission publication completes, then raw output has 8,500 records and parsed/submission CSV files have 8,501 lines with SHA-256 hashes and no partial artifact presented as complete.

## Spec Change Log

## Design Notes

Qwen3.5 defaults to thinking output, which would consume the runtime budget and can interfere with the strict final-line contract. Disable thinking at the official chat-template boundary rather than editing Reasoner v3 or stripping reasoning text after generation.

## Verification

**Commands:**
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/test_model_adapter.py tests/test_reasoner_v3_contract.py` -- expected: all focused CPU tests pass.
- RunPod real-image smoke -- expected: valid v3 result on NVIDIA RTX A6000 with no load or serialization rejection.
- RunPod measured subset -- expected: zero parse failures and projected full runtime within 70 minutes.
- RunPod full artifact validation -- expected: 8,500 raw records, 8,501 CSV lines, matching sample order, and recorded hashes.
