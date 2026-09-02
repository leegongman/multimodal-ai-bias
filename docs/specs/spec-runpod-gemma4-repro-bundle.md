---
title: 'Package the proven Gemma 4 RunPod runtime for exact rebuilds'
type: 'chore'
created: '2026-06-21'
status: 'in-review'
baseline_commit: 'NO_VCS'
context:
  - 'spec-gemma4-12b-reasoner-v3-run.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The proven Gemma 4 12B runtime currently exists only on a disposable RunPod instance. Terminating the pod would lose the exact environment, server options, model revision, and operational commands that produced the valid 0.9490833333 submission.

**Approach:** Create one self-contained local reproduction folder containing immutable version pins, the minimal Reasoner v3 runtime source, idempotent setup/download/server/run/validation scripts, and a concise runbook. A new Ubuntu 24.04 RTX A6000 RunPod must be rebuildable from this folder without copying the 23GB model or 13GB virtual environment.

## Boundaries & Constraints

**Always:** Pin official `google/gemma-4-12B-it` revision `5926caa4ec0cac5cbfadaf4077420520de1d5205`; preserve vLLM `0.23.0+cu129`, Torch `2.11.0+cu129`, Transformers `5.12.1`, FastAPI `0.116.1`, Starlette `0.47.3`, and instrumentator `7.1.0`; start vLLM with the environment's `bin` directory first in `PATH` so `ninja` resolves; preserve served name, loopback host, port 8000, 32K context, TP=1, and GPU utilization 0.90; require both `/health` and `/v1/models` to pass before inference; use concurrency 32, 256→512 selective retry, and unchanged Reasoner v3 prompt; perform preflight checks before expensive inference; keep scripts rerunnable and fail-fast.

**Ask First:** Any switch of model, revision, quantization, CUDA/vLLM stack, prompt, parser semantics, output token policy, or hardware class requires explicit approval.

**Never:** Bundle credentials, SSH keys, Hugging Face tokens, model weights, datasets, virtual environments, RunPod outputs, or unrelated/frozen model files; silently install a fallback dependency; overwrite an existing run directory; claim exact reproducibility on a materially different GPU/driver without re-benchmarking.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|---------------------------|----------------|
| Fresh compatible pod | Ubuntu 24.04, Python 3.12, RTX A6000, sufficient disk | Build isolated env, fetch exact snapshot, pass health and smoke checks | Stop at the failing stage with actionable output |
| Re-run | Env or snapshot already exists | Verify and reuse matching artifacts | Reject mismatched revision or package versions |
| Incompatible host | Missing GPU, insufficient disk, wrong model files, unhealthy API | Do not start full inference | Exit non-zero before paid full run |
| Full run | Official data mounted at expected path | Produce 8,500 valid rows and 8,501-line submission | Publish no submission when validation fails |

</frozen-after-approval>

## Code Map

- `deploy/runpod/gemma4-repro/` -- portable reproduction bundle and runbook.
- `deploy/runpod/gemma4-repro/bootstrap.sh` -- host preflight, isolated Python environment, exact dependency installation.
- `deploy/runpod/gemma4-repro/download_model.sh` -- exact-revision official snapshot download and verification.
- `deploy/runpod/gemma4-repro/serve.sh` -- proven vLLM server configuration and health gate.
- `deploy/runpod/gemma4-repro/smoke.sh` -- real-image one-row and measured-subset gates.
- `deploy/runpod/gemma4-repro/run_full.sh` -- no-clobber 8,500-row c32 execution.
- `deploy/runpod/gemma4-repro/validate_run.py` -- artifact, ID/order, parse-count, and submission validation.
- `deploy/runpod/gemma4-repro/runtime/` -- minimal runner, prompt, and required `multimodal_bias` modules.

## Tasks & Acceptance

**Execution:**
- [x] Capture the exact proven system/package/model manifest without secrets.
- [x] Build idempotent setup, model-download, server, smoke, full-run, and validation commands.
- [x] Copy only the minimal runtime source and Reasoner v3 prompt into the bundle.
- [x] Add shell/Python tests that exercise help, preflight failures, no-clobber behavior, and validation using fixtures.
- [x] Package the folder as a checksum-addressed archive suitable for `scp` to a new RunPod.

**Acceptance Criteria:**
- Given a fresh compatible RunPod, when the runbook is followed, then every command and required path is explicit and the exact known-good dependency/model revisions are enforced.
- Given missing data, GPU, disk, server health, or matching model revision, when a gated script runs, then it fails before full inference with a clear message.
- Given a completed full run, when validation runs, then it requires 8,500 unique ordered IDs, zero invalid parses, and an 8,501-line submission.
- Given the generated archive, when inspected, then it contains no credentials, model weights, datasets, environments, or prior generated outputs.

## Spec Change Log

- 2026-06-21: Restored the byte-exact proven Reasoner v3 prompt and added a packaging gate that compares it with every `known-good-runtime*.json` prompt hash.

## Design Notes

The full `pip freeze` is retained as provenance, while bootstrap installs the exact top-level known-good stack and validates resolved critical versions. This avoids coupling rebuilds to transient indirect packages that are embedded in a platform-specific vLLM wheel while still detecting drift before inference. The server gate explicitly detects the three failures seen during the successful setup: a CUDA-incompatible vLLM wheel (`libcudart.so.13`), missing `ninja` caused by an incomplete `PATH`, and HTTP 500 responses caused by incompatible FastAPI/Starlette/instrumentator versions.

## Verification

**Commands:**
- `bash -n deploy/runpod/gemma4-repro/*.sh` -- expected: all shell scripts parse.
- `uv run pytest -q tests/test_runpod_gemma4_repro.py tests/test_gemma4_v3_runner.py` -- expected: all tests pass.
- `python deploy/runpod/gemma4-repro/validate_bundle.py runpod-gemma4-repro` -- expected: exact files/checksums, no forbidden payloads or secret-like content.
- `tar -tzf runpod-gemma4-repro-20260621.tar.gz` -- expected: only the approved bundle tree.
