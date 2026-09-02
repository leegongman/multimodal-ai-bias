# Acceptance Auditor — RunPod Gemma 4 Reproduction Bundle

Read:

- `spec-runpod-gemma4-repro-bundle.md`
- `spec-gemma4-12b-reasoner-v3-run.md`
- `deploy/runpod/gemma4-repro/`
- `tests/test_runpod_gemma4_repro.py`

Audit the implementation against every frozen boundary, I/O matrix row, task, acceptance criterion, design note, and verification command. Confirm especially that the exact vLLM `0.23.0+cu129` server stack is reproducible and prevents the previously observed `libcudart.so.13`, missing `ninja`, and FastAPI/Starlette/instrumentator HTTP 500 failures.

Check that no credentials, model weights, datasets, environments, or prior runs enter the archive; the exact model revision and server options are enforced; expensive inference is gated; no-clobber behavior is preserved; and full output validation fails closed.

Return a requirements matrix with Pass/Fail and evidence by file:line, followed by actionable findings only.

