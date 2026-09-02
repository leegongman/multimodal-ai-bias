---
baseline_commit: NO_VCS
created_at: 2026-06-20
---

# Story 2.8: Build Candidate Eligibility and Adapter Smoke Harness

Status: done

## Story

As a competition developer,
I want one eligibility and smoke-test contract for every tournament candidate,
so that ineligible or incorrectly serialized models are rejected before diagnostic evaluation.

## Acceptance Criteria

1. A strict candidate manifest records candidate ID, official repository, exact commit, release/cutoff evidence, license, local snapshot hash, custom-code hashes, dependency-lock evidence, official processor/chat/image serialization evidence, preprocessing metadata, and `remote_api_usage: none`.
2. Manifest loading rejects missing/extra/duplicate fields, unknown remote API use, post-cutoff release dates, unpinned commits, absent local evidence paths, malformed hashes, and non-UTF-8 text with stable machine-readable rejection codes.
3. A real-image Reasoner v3 smoke uses the existing model adapter and v3 prompt/parser, preserving prompt/image hashes, rendered-input/serialization evidence, raw output, load metadata, latency, GPU identity, and peak VRAM.
4. Smoke failure never invents a candidate result: offline-load failure, image failure, generation failure, invalid v3 structured output, missing serialization evidence, or non-A6000 hardware produces explicit rejection codes.
5. `diagnostic_48_allowed` is true only when every eligibility, offline, serialization, structured-output, and RTX A6000 48GB gate passes.
6. Candidate reports are deterministic UTF-8 JSON, written atomically with no clobber, and contain no generated Multimodal prediction/submission artifacts.
7. CPU-safe tests use injected adapters/hardware telemetry and cover success plus every blocking gate; real GPU execution remains an explicit CLI smoke and is excluded from the default unit suite.
8. Story 2.8 does not download models, integrate MiniCPM/LLaVA, run diagnostic-48, select a winner, change Reasoner v3, or authorize 8,500-row production.

## Tasks / Subtasks

- [x] Define typed candidate eligibility/smoke contracts in `schemas.py` (AC: 1, 3, 5)
  - [x] Add immutable manifest, hardware telemetry, rejection, rendered-input evidence, smoke result, and report dataclasses.
  - [x] Keep model-specific behavior behind `VisionLanguageModelAdapter`.
- [x] Implement strict candidate manifest loading and eligibility validation (AC: 1, 2)
  - [x] Use unique-key YAML loading and exact keys.
  - [x] Enforce cutoff `2026-05-31`, pinned 40-hex commit/hash formats, local evidence paths, and remote API `none`.
  - [x] Return stable snake_case rejection codes without network access.
- [x] Implement real-image Reasoner v3 smoke harness (AC: 3–5)
  - [x] Reuse `build_reasoner_prompt`, `ModelGenerationRequest`, adapter load/generate, and `parse_reasoner_output`.
  - [x] Hash prompt/image bytes and record declared official serialization evidence.
  - [x] Capture elapsed latency and injected/real GPU telemetry including peak VRAM.
  - [x] Reject any invalid parsed v3 result and require RTX A6000 with at least 48,000 MiB total VRAM.
- [x] Add atomic candidate report publication and CLI command (AC: 5, 6)
  - [x] Add `candidate-smoke` with manifest, model config, real image, and output arguments.
  - [x] Publish deterministic JSON with no-clobber semantics and concise exit behavior.
- [x] Add CPU-safe tests and validation (AC: 1–8)
  - [x] Cover valid manifest, exact-field/type/hash/cutoff/path failures, remote API rejection, and duplicate YAML keys.
  - [x] Cover pass/fail load, image, output schema, serialization, A6000 identity/VRAM, and report no-clobber.
  - [x] Run full pytest, Ruff check/format, CLI help/version, and confirm no submission artifacts are created.

### Review Findings

- [x] [Review][Patch] Fail closed on dummy/network-enabled adapters, declared snapshot mismatches, and missing or mismatched configured/loaded model identity [src/multimodal_bias/candidate_harness.py:165]
- [x] [Review][Patch] Resolve manifest evidence paths relative to the manifest and reject unsafe YAML keys, noncanonical dates, invalid UTF-8 mappings, normalized duplicates, and unverifiable custom-code hashes [src/multimodal_bias/candidate_harness.py:62]
- [x] [Review][Patch] Require a genuinely decodable image before model loading and cover valid/corrupt image inputs [src/multimodal_bias/candidate_harness.py:176]
- [x] [Review][Patch] Require an exact normalized RTX A6000 identity and valid peak-VRAM telemetry before diagnostic eligibility [src/multimodal_bias/candidate_harness.py:226]
- [x] [Review][Patch] Convert adapter construction and report-publication failures into stable rejection codes and concise CLI errors [src/multimodal_bias/candidate_harness.py:192]

## Dev Notes

### Scope and Architecture

- New orchestration belongs in `src/multimodal_bias/candidate_harness.py`; shared dataclasses belong in `schemas.py`; CLI wiring belongs in `cli.py`.
- Reuse `load_model_config`, `create_model_adapter`, `build_reasoner_prompt`, and `parse_reasoner_output`. Do not add a second adapter interface or parser.
- No network calls or model downloads are permitted. Evidence is declared and locally auditable; model-specific verification happens in Stories 2.9/2.10.
- The harness is a gate, not a tournament. It emits `diagnostic_48_allowed`, not a quality score.
- A CPU dummy can test orchestration but can never pass the A6000 gate in production mode.
- Use explicit stable rejection codes such as `manifest_invalid`, `cutoff_ineligible`, `remote_api_forbidden`, `serialization_evidence_missing`, `offline_load_failed`, `image_invalid`, `structured_output_invalid`, `gpu_not_a6000`, and `vram_insufficient`.

### Previous Story Intelligence

- Story 2.7 made Reasoner v3 the only active contract and added fail-closed version lineage. Candidate smoke must parse with default v3 and must not route into legacy Verifier/arbitration.
- Preserve no-clobber artifact publication and concise CLI errors established in Stories 2.5–2.7.
- Story 2.7 currently has 388 passing CPU tests; this story must not require PyTorch/Transformers/GPU in the default test suite.

### Project Structure Notes

- Importable code remains under `src/multimodal_bias/`.
- Candidate manifests belong under `configs/candidates/`; reports belong under a caller-selected run/diagnostic directory.
- Do not modify model-specific adapters except when a failing common-interface test proves it necessary.

### References

- [Source: docs/history/epics.md#Story-2.8-Build-Candidate-Eligibility-and-Adapter-Smoke-Harness]
- [Source: docs/history/architecture.md#Runtime-Model-Architecture]
- [Source: docs/history/architecture.md#Validation-Strategy]
- [Source: docs/history/architecture.md#Compliance-Security]
- [Source: docs/history/stories/2-7-implement-reasoner-v3-option-index-contract.md]
- [Source: src/multimodal_bias/models/adapter.py]
- [Source: src/multimodal_bias/reasoner.py]
- [Source: src/multimodal_bias/parsing.py]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- RED: candidate harness import failed before implementation.
- GREEN: focused candidate harness suite reached 16 passing tests.
- REGRESSION: 404 project tests passed with bytecode/cache creation disabled.

### Implementation Plan

1. Add failing contract/manifest tests.
2. Implement strict manifest and typed report boundary.
3. Add adapter-backed v3 real-image smoke with injectable telemetry.
4. Add atomic JSON publication and CLI wiring.
5. Run full regression and quality gates.

### Completion Notes List

- Story context created from corrected Gate A order, architecture, Story 2.7 review learnings, and current adapter boundaries.
- Added strict offline candidate manifests with duplicate-key, exact-field, cutoff, hash, evidence-path, serialization, and remote-API gates.
- Added injectable adapter/hardware real-image Reasoner v3 smoke with deterministic evidence hashes and explicit rejection codes.
- Added atomic no-clobber JSON report publication and the `candidate-smoke` CLI command.
- Verified 404 tests, Ruff check/format, CLI help/version, and absence of generated submission/report artifacts.
- Applied all five code-review patches: fail-closed model identity, auditable manifest evidence, decodable-image validation, exact GPU/peak-VRAM gates, and stable setup/publication failures.
- Revalidated with 27 focused candidate-harness tests, 415 full tests, Ruff check/format, and CLI help/version; moved Story 2.8 to `done`.

### File List

- docs/history/stories/2-8-build-candidate-eligibility-and-adapter-smoke-harness.md
- docs/history/stories/2-8-build-candidate-eligibility-and-adapter-smoke-harness.validation.md
- sprint-status.yaml
- src/multimodal_bias/candidate_harness.py
- src/multimodal_bias/cli.py
- src/multimodal_bias/exceptions.py
- src/multimodal_bias/schemas.py
- tests/test_candidate_harness.py

## Change Log

- 2026-06-20: Created Story 2.8 and marked ready for development.
- 2026-06-20: Implemented candidate eligibility and adapter smoke harness; moved to review.
- 2026-06-20: Applied all code-review patches, passed final validation, and moved Story 2.8 to done.
