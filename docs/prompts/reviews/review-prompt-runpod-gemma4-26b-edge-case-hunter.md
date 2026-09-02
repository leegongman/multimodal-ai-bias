# Edge Case Hunter Review — Gemma 4 26B RunPod Bundle

Use the `bmad-review-edge-case-hunter` skill.

Inspect `deploy/runpod/gemma4-repro/`, `tests/test_runpod_gemma4_repro.py`, and the generated `runpod-gemma4-repro-20260621-gemma26.tar.gz`.

Walk every branch in profile loading, bootstrap, download/revision verification, vLLM startup/reuse/shutdown, smoke, Full, run validation, bundle validation, checksum generation, and packaging. Confirm both `gemma4-26b-a4b-awq` and `gemma4-12b` paths.

Report only unhandled edge cases caused by this change. Pay particular attention to unknown profiles, empty profile variables, partial snapshots, profiles sharing port 8000, stale PID files from a different profile, existing but unmarked snapshots, interrupted installs/downloads, `/workspace` availability, shell array/`set -u` behavior, model architecture aliases, HTTP 500/timeouts, run no-clobber, data ordering, and portable SHA-256 verification.

For each finding include severity, exact file and line, triggering state, observed bad behavior, and a targeted test/fix.
