# Independent Review: Gemma 4 Reasoner v3 Prompt Recovery

Review the recovery without editing files. Report findings by severity, with exact file and line references where applicable. If there are no findings, state that explicitly and list any residual validation gap.

## Intent

Restore the byte-exact Reasoner v3 prompt used by the proven Gemma 4 26B-A4B AWQ submission and prevent future bundle/provenance drift. Do not change or rerun the model, the 8,500-row inference, parser semantics, dataset, or prior submission artifacts.

## Proven Facts

- Proven submission: Public `0.9634166667`, 8,500/8,500 valid, 0 failures/retries, 2506.961842 seconds.
- Model: `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`.
- Model revision: `4033b16200f4152e55e100ea12dc388c537df622`.
- Required Reasoner v3 SHA-256: `87d694d0b968ccef4606a979f52c5de63454e870be71a6d9f4e91ef942067cb6`.
- `runpod-gemma4-repro 2/runtime/configs/prompts/reasoner_v3.yaml` is a stale candidate with SHA-256 `adaf83a9d7e3f94fdccd9de7aae56fc09c12b3f966e138259e0deb25c24be0fd` and was intentionally not used or modified.

## Files to Review

- `configs/prompts/reasoner_v3.yaml`
- `deploy/runpod/gemma4-repro/runtime/configs/prompts/reasoner_v3.yaml`
- `deploy/runpod/gemma4-repro/validate_bundle.py`
- `deploy/runpod/gemma4-repro/SHA256SUMS`
- `deploy/runpod/gemma4-repro/README.md`
- `deploy/runpod/gemma4-repro/NEXT_SESSION_PROMPT.md`
- `tests/test_runpod_gemma4_repro.py`
- `spec-runpod-gemma4-26b-repro-handoff.md`
- `spec-runpod-gemma4-repro-bundle.md`
- `runpod-gemma4-repro-20260621-gemma26.tar.gz`
- `runpod-gemma4-repro-20260621-gemma26.tar.gz.sha256`

## Review Questions

1. Do both active prompt files match the required SHA-256 byte-for-byte, including EOF behavior?
2. Do both `provenance/known-good-runtime*.json` manifests declare that same prompt hash?
3. Does `validate_bundle.py` reliably reject malformed provenance and prompt/provenance mismatches without weakening the existing secret, payload, and checksum checks?
4. Does `SHA256SUMS` cover the recovered prompt and all intended bundle files?
5. Does the regenerated archive pass its sidecar checksum and contain the recovered prompt hash?
6. Did the recovery avoid model, runtime, parser, previous predictions, and submission changes?
7. Are there missing regression tests or edge cases that could allow silent prompt drift?

## Verification Already Run

```text
ruff: all checks passed
pytest: 100 passed
validate_bundle.py: OK
archive sidecar checksum: OK
archive-contained prompt SHA-256: 87d694d0b968ccef4606a979f52c5de63454e870be71a6d9f4e91ef942067cb6
```

Do not request or run a new 8,500-row inference merely to validate this static recovery.
