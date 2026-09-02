---
title: 'Extend the RunPod bundle with the proven Gemma 4 26B AWQ runtime and handoff'
type: 'chore'
created: '2026-06-21'
status: 'in-review'
baseline_commit: 'NO_VCS'
context:
  - 'spec-runpod-gemma4-repro-bundle.md'
  - 'deploy/runpod/gemma4-repro/README.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The local reproduction bundle only captures the older Gemma 4 12B run, while the best proven result—Gemma 4 26B-A4B AWQ, Public 0.9634, 8,500/8,500 valid, 41m47s—depends on configuration and artifacts that currently live mainly in the disposable RunPod and conversation history.

**Approach:** Extend the existing bundle with an explicit Gemma 4 26B-A4B AWQ profile, exact model/runtime provenance, server and inference commands, validation, packaging, and a copy-ready prompt that lets a fresh Codex conversation rebuild the same environment on a new RTX A6000 RunPod without bundling weights, data, credentials, environments, or runs.

## Boundaries & Constraints

**Always:** Preserve the existing 12B profile; make the proven 26B AWQ profile explicit and reproducible; pin model `cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit` revision `4033b16200f4152e55e100ea12dc388c537df622`; preserve Python 3.12, Torch 2.11.0+cu129, vLLM 0.23.0+cu129, Transformers 5.12.1, OpenAI 2.43.0, FastAPI 0.116.1, Starlette 0.47.3, instrumentator 7.1.0, and Ninja 1.13.0; preserve A6000 driver 550.127.08, TP=1, 32K context, GPU utilization 0.90, `--generation-config vllm`, concurrency 32, 256→512 selective retry, and the unchanged Reasoner v3 prompt; validate health, served model ID, revision, artifacts, row ordering, and checksums before claiming success.

**Ask First:** Any deletion of existing local/remote artifacts, replacement of the known-good package stack, model/revision/quantization change, prompt change, or materially different GPU class requires approval.

**Never:** Bundle credentials, SSH keys, Hugging Face tokens, model weights, datasets, virtual environments, RunPod outputs, or unrelated candidate-model artifacts; overwrite an existing run; silently fall back to a different model or dependency; claim that a new pod is reproduced before smoke and environment validation pass.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|---------------------------|----------------|
| Fresh A6000 pod | Bundle archive, project data, network access | Create exact venv, download pinned 26B snapshot, serve, smoke, and allow Full | Fail before inference with the mismatched prerequisite |
| Existing 12B workflow | User selects 12B profile | Original model/revision/runner remain usable | Reject mixed profile artifacts or served IDs |
| Resume tomorrow | New Codex conversation receives handoff prompt | It knows what local files to transfer and the exact command order | It must inspect state rather than redownload or overwrite blindly |
| Completed 26B Full | 8,500-row run directory | Validate 8,500/8,500, zero failures, ordered submission and hashes | Do not publish submission when any gate fails |

</frozen-after-approval>

## Code Map

- `deploy/runpod/gemma4-repro/` -- existing portable bundle to extend without embedding large or secret payloads.
- `deploy/runpod/gemma4-repro/env.sh` and profile files -- select exact 12B or 26B model/runtime constants.
- `deploy/runpod/gemma4-repro/{bootstrap,download_model,serve,smoke,run_full,stop_server}.sh` -- rebuild and operate the selected profile.
- `deploy/runpod/gemma4-repro/runtime/scripts/` -- isolated model-specific Reasoner v3 runners.
- `deploy/runpod/gemma4-repro/provenance/` -- known-good package, hardware, model, runtime, score, and hash evidence.
- `deploy/runpod/gemma4-repro/NEXT_SESSION_PROMPT.md` -- copy-ready instructions for a fresh Codex conversation.

## Tasks & Acceptance

**Execution:**
- [x] Extend bundle profile selection and environment verification while preserving the 12B path.
- [x] Add the exact 26B runner, model download verification, vLLM arguments, smoke/full commands, and run validator expectations.
- [x] Record the proven 26B revision, runtime, package versions, 41m47s execution, 8,500 valid rows, and Public 0.9634 without copying generated outputs.
- [x] Write the complete next-session prompt, required local file transfer list, venv/bootstrap order, server health gate, smoke/full flow, and recovery checks.
- [x] Regenerate checksums/archive and run syntax, unit, bundle-content, and archive-integrity validation.

**Acceptance Criteria:**
- Given a fresh compatible A6000 pod, when the 26B profile instructions are followed, then the exact pinned environment, snapshot, server configuration, and Reasoner v3 pipeline can be rebuilt without undocumented commands.
- Given the existing 12B profile, when the bundle is updated, then its pinned runner and model path remain selectable and validated.
- Given the handoff prompt in a new conversation, when Codex reads it, then it can identify every file to transfer and every command/check required before a paid Full run.
- Given the packaged archive, when validated, then it contains no secrets, weights, data, environments, or run outputs and all included files match `SHA256SUMS`.

## Spec Change Log

- 2026-06-21: Recovered the exact successful Reasoner v3 prompt (`87d694d0b968ccef4606a979f52c5de63454e870be71a6d9f4e91ef942067cb6`) after detecting that the packaged prompt did not match both known-good runtime manifests. Bundle validation now rejects prompt/provenance drift, and the Gemma26 archive was rebuilt without changing the model, runtime, parser, or inference outputs.

## Design Notes

Use named profiles rather than overwriting 12B constants. Default operational examples should use the current best 26B AWQ profile, while profile selection must be visible in every command and recorded in run provenance.

## Verification

**Commands:**
- `bash -n deploy/runpod/gemma4-repro/*.sh deploy/runpod/gemma4-repro/profiles/*.sh` -- all shell files parse.
- `uv run pytest -q tests/test_runpod_gemma4_repro.py tests/test_gemma4_v3_runner.py` -- existing and added profile behavior passes.
- `python deploy/runpod/gemma4-repro/validate_bundle.py runpod-gemma4-repro` -- no forbidden or secret payload and checksums match.
- `deploy/runpod/gemma4-repro/package.sh` plus `tar -tzf` and `shasum -a 256 -c` -- archive is complete and intact.
