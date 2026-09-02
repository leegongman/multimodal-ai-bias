# Edge Case Hunter Review — RunPod Gemma 4 Reproduction Bundle

Use the `bmad-review-edge-case-hunter` skill.

Inspect `deploy/runpod/gemma4-repro/` and `tests/test_runpod_gemma4_repro.py`. Walk every branch in bootstrap, model download, server startup/reuse/shutdown, smoke, full inference, run validation, bundle validation, checksum generation, and archive creation.

Report only unhandled edge cases caused by this change. Pay particular attention to interrupted installs/downloads, partially existing snapshots, stale PID files, occupied ports, JSON formatting variations, unavailable `/workspace`, pip constraint conflicts, existing run directories, HTTP 500/timeouts, official ID ordering, and checksum staleness.

For each finding include severity, exact file and line, triggering state, observed bad behavior, and a targeted test/fix.

