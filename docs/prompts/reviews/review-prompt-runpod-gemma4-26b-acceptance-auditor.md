# Acceptance Auditor — Gemma 4 26B RunPod Bundle

Read:

- `spec-runpod-gemma4-26b-repro-handoff.md`
- `spec-runpod-gemma4-repro-bundle.md`
- `deploy/runpod/gemma4-repro/`
- `tests/test_runpod_gemma4_repro.py`
- `runpod-gemma4-repro-20260621-gemma26.tar.gz`
- `runpod-gemma4-repro-20260621-gemma26.tar.gz.sha256`

Audit the implementation against every frozen boundary, I/O matrix row, task, acceptance criterion, design note, and verification command. Confirm the existing 12B profile remains usable and the default 26B AWQ profile pins model `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`, revision `4033b16200f4152e55e100ea12dc388c537df622`, vLLM/Torch cu129 stack, `--generation-config vllm`, c32, 256→512 retry, and unchanged Reasoner v3.

Check the new-session prompt is sufficient to identify local transfer files, build the exact Python 3.12 venv, install all critical packages, verify hardware/data/server, run smoke, gate Full, validate 8,500 rows, and preserve artifacts. Confirm no credentials, weights, datasets, environments, prior runs, or unrelated models enter the archive.

Return a requirements matrix with Pass/Fail and evidence by file:line, followed by actionable findings only.
