---
baseline_commit: NO_VCS
---

# Story 3.3: Arbitrate Final Labels With Evidence Preservation

Status: backlog

## Story

As a competition developer,
I want final labels selected through explicit arbitration rules,
so that verifier changes are justified by stronger evidence and not deterministic post-hoc mapping.

## Acceptance Criteria

1. Given parsed Reasoner v3 outputs and optional Verifier v2 outputs, when arbitration runs, then only samples with at least one valid generated candidate receive a `FinalPrediction`; others receive an explicit `unresolved` result.
2. Given a Verifier output that finds no concrete Reasoner defect, when arbitration runs, then the Reasoner label is kept and the decision reason records that the Verifier did not justify a change.
3. Given a valid Verifier output with a concrete Reasoner defect and stronger support for a different generated label, when arbitration runs, then the final label and uncertainty-index lineage are taken from the Verifier and the source stage records `verifier`.
4. Given a valid stage output concluding evidence is insufficient, when arbitration runs, then it may use only that stage's generated uncertainty-choice index; no numeric index is treated as inherently uncertain.
5. Given a recoverable Verifier failure, when the Reasoner candidate is valid, then it keeps that generated Reasoner candidate and records the failure; when neither candidate is valid, it returns `unresolved`.
6. Given a strict `verification.jsonl` artifact from Story 3.2, when submission generation is requested with verification enabled, then final artifacts are generated only if every required sample has a valid arbitrated generated candidate and unresolved count is zero.
7. Given submission generation without verification enabled, when the existing reasoner-only path is used, then current Story 2.6 behavior remains unchanged.
8. Given malformed, duplicate, missing, wrong-run, or wrong-order verification rows, when arbitration/submission reads the artifact, then it fails closed with a typed validation error and does not publish partial final artifacts.
9. Every final prediction records `run_id`, `sample_id`, `final_label`, `source_stage`, non-empty `decision_reason`, schema version, and Reasoner/Verifier option-index lineage; no deterministic answer mapping, majority vote, handcrafted override, or invented fallback is introduced.

## Corrective Work Required (2026-06-20)

- [ ] Add typed unresolved arbitration result and final-publication guard.
- [ ] Consume Reasoner/Verifier schema versions and uncertainty-index lineage.
- [ ] Remove all paths that synthesize label 2 or any other label when valid generated candidates are absent.
- [ ] Preserve Reasoner candidate on Verifier failure only when Reasoner v3 is valid.
- [ ] Add position 0/1/2, both-invalid, one-valid, semantic-mismatch, and atomic-publication tests.

## Historical Tasks / Subtasks (pre-correction implementation)

- [x] Add strict arbitration inputs and verification artifact reading.
  - [x] Read `verification.jsonl` into typed `VerificationRecord` instances.
  - [x] Validate exact expected sample ids, exact run id, duplicate-free rows, label domain, trigger status consistency, and non-empty verifier metadata where required.
  - [x] Keep parsing and validation deterministic without changing label decisions.
- [x] Implement final label arbitration in `arbitration.py`.
  - [x] Keep the Reasoner label when the Verifier finds no concrete defect.
  - [x] Adopt the Verifier label only when `reasoner_defect_found` and `objective_support` justify a stronger person-specific label.
  - [x] Historical fixed-label fallback is superseded; corrective implementation uses only valid stage-generated candidates or `unresolved`.
  - [x] Produce `FinalPrediction` records with stable source-stage and decision-reason values.
- [x] Connect arbitrated predictions to submission generation.
  - [x] Add a submission boundary that accepts validated `FinalPrediction` records.
  - [x] Preserve the existing reasoner-only `generate_submission_artifacts(...)` behavior.
  - [x] Add an explicit CLI path for verifier-aware submission generation.
- [x] Add CPU-safe tests.
  - [x] Cover keep, flip, uncertainty, verifier failure, invalid artifact, and missing artifact cases.
  - [x] Cover both reasoner-only and verifier-aware `make-submission` paths.
  - [x] Cover final artifact validation for non-reasoner source stages.
- [x] Run validation.
  - [x] `uv run pytest -q`
  - [x] `uv run ruff check src tests`
  - [x] `uv run ruff format --check src tests`
  - [x] CLI smoke check for the package entry point.

## Dev Notes

### Previous Story Insights

- Story 3.1 added typed trigger detection in `schemas.py` and `verifier.py`.
- Story 3.2 added conditional verification, `VerifierOutput`, `ParsedVerifierOutput`, `VerificationRecord`, `VerifierRunResult`, the `verify-risky` CLI command, and `verification.jsonl`.
- Story 3.2 intentionally does not create `final_predictions.csv` or `submission.csv`; Story 3.3 owns the submission path that consumes verifier output.
- Story 2.6 currently generates reasoner-only `final_predictions.csv` and `submission.csv`; this path must remain available and behavior-compatible.

### Architecture Context

- `arbitration.py` is the only component allowed to choose final labels after verifier input.
- `submission.py` can consume only validated final predictions and is responsible for atomic publication of `final_predictions.csv` and `submission.csv`.
- `verifier.py` only evaluates risky samples and writes audit records; it must not decide final labels.
- Do not introduce deterministic post-hoc answer mapping, majority vote, or handcrafted label replacement.

### Data Contracts

- Reasoner input contract: `ParsedReasonerRecord`.
- Verifier input contract: `VerificationRecord` from `verification.jsonl`.
- Final output contract: `FinalPrediction`.
- Existing source stages are `reasoner`, `verifier`, and `arbitration`.
- `FinalPrediction.final_label` must be one of `0`, `1`, `2`.

### Expected Arbitration Semantics

- `skipped_not_triggered`: keep the valid Reasoner label.
- Verifier finds no concrete defect: keep the valid Reasoner label.
- Verifier finds a concrete defect with objective support for a person label: use the Verifier label.
- A valid Verifier or Reasoner may supply its generated uncertainty-choice index when evidence is insufficient.
- If both candidates are invalid, return `unresolved` and block final artifact publication.
- If the Verifier fails but the Reasoner has a valid label, keep the Reasoner label and record that the Verifier did not supply usable support.

### Files Likely To Change

- `src/multimodal_bias/arbitration.py`
- `src/multimodal_bias/submission.py`
- `src/multimodal_bias/cli.py`
- `tests/test_arbitration.py`
- `tests/test_submission.py`
- `tests/test_cli.py`

## Testing

- Unit tests should avoid GPU/model loading and use in-memory or temporary JSONL/CSV fixtures.
- CLI tests should use the existing temporary run directory/config patterns.
- Validation should include full pytest and ruff checks.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-06-19: Started dev-story implementation.
- 2026-06-19: `uv run pytest -q` passed, 365 tests.
- 2026-06-19: `uv run ruff check src tests` passed.
- 2026-06-19: `uv run ruff format --check src tests` passed.
- 2026-06-19: `uv run multimodal-bias --help` and `--version` passed.

### Completion Notes List

- Implemented strict `verification.jsonl` reader and final-label arbitration in `arbitration.py`.
- Added verifier-aware final prediction publication while preserving the existing reasoner-only submission path.
- Added explicit `make-submission --use-verification` CLI flow that reads `parsed_reasoner.csv`, reads `verification.jsonl`, arbitrates labels, and publishes `final_predictions.csv` plus `submission.csv`.
- Added CPU-safe unit and CLI coverage for keep, flip, uncertainty, verifier failure, invalid verification artifacts, missing verification artifacts, and non-reasoner source stages.

### File List

- docs/history/stories/3-3-arbitrate-final-labels-with-evidence-preservation.md
- src/multimodal_bias/arbitration.py
- src/multimodal_bias/submission.py
- src/multimodal_bias/cli.py
- tests/test_arbitration.py
- tests/test_submission.py
- tests/test_cli.py

## Change Log

- 2026-06-20: Reopened by approved Correct Course; removed fixed-label fallback and added unresolved fail-closed contract.
- 2026-06-19: Created story from Epic 3.3 requirements and current Story 3.1/3.2 implementation context.
- 2026-06-19: Implemented Story 3.3 arbitration, verifier-aware submission path, and validation coverage.
