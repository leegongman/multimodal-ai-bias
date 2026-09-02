---
baseline_commit: NO_VCS
---

# Story 2.6: Generate Validated Final Predictions and Submission CSV

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a competition developer,
I want final predictions and Multimodal submission files generated only through the approved submission command,
so that invalid or ad hoc submission files cannot be produced accidentally.

## Acceptance Criteria

1. Given a completed run containing UTF-8 `parsed_reasoner.csv` and the matching official Multimodal input, when `make-submission` runs for that run ID, then it writes `final_predictions.csv` and `submission.csv` under the same run directory without modifying `raw_reasoner.jsonl` or `parsed_reasoner.csv`.
2. Given one valid parsed Reasoner row for every official test sample, when final predictions are built, then each ordered row preserves the exact `run_id` and `sample_id`, copies the model-generated `parsed_label` unchanged to a typed `final_label`, records `source_stage="reasoner"` and an auditable non-empty decision reason, and never derives a label from rules, question text, answer position, risk flags, or Public leaderboard behavior.
3. Given `final_predictions.csv`, when the submission artifact is generated, then `submission.csv` contains exactly the UTF-8 header `sample_id,label`, one row per official test sample in official `test.csv`/`sample_submission.csv` order, and only exact string labels `"0"`, `"1"`, or `"2"`.
4. Given missing, unreadable, malformed, empty, duplicate-header, duplicate-ID, mixed-run, wrong-order, wrong-count, invalid-label, or non-`valid` parsed input, when `make-submission` runs, then it raises `SubmissionFormatError`, exits cleanly without traceback, and creates neither complete-looking final nor submission artifact; no invalid parse or source failure is converted to a fallback label in this story.
5. Given existing `final_predictions.csv` or `submission.csv`, a destination outside the selected run directory, a run ID that escapes the configured `runs_root`, a write failure, or concurrent publication, when generation is attempted, then completed artifacts are not overwritten, sibling temporary files are cleaned, and the operation does not leave a newly published partial pair.
6. CPU-safe unit and CLI tests cover the valid path, exact headers/encoding/order/count/labels, strict parsed-input and run-lineage failures, existing-output and injected-write failure behavior, CLI error mapping, and all existing regressions without official Multimodal data, model weights, GPU, network, PyTorch, Transformers, Accelerate, or Pillow.

## Tasks / Subtasks

- [x] Define typed final-prediction and submission result contracts (AC: 1, 2, 3)
  - [x] Add the architecture-required `FinalPrediction` frozen dataclass and stable `FinalSourceStage` label to `src/multimodal_bias/schemas.py`; include `run_id`, `sample_id`, `final_label`, `source_stage`, and `decision_reason`.
  - [x] Reuse `ReasonerLabel` for `final_label`; do not introduce integer labels or coercion between numeric and string labels.
  - [x] Add a typed orchestration result containing both artifact paths, ordered final predictions, and total sample count so CLI/submission boundaries do not exchange anonymous dictionaries.
  - [x] Keep the source-stage type future-compatible with Story 3 arbitration while emitting only `reasoner` in this story.

- [x] Implement strict submission orchestration in `src/multimodal_bias/submission.py` (AC: 1, 2, 3, 4, 5)
  - [x] Define fixed filenames and headers for `final_predictions.csv` and `submission.csv`; the Multimodal file header must be exactly `sample_id,label`.
  - [x] Read `parsed_reasoner.csv` as UTF-8 with the standard `csv` parser and `newline=""`; reuse `PARSED_REASONER_FIELDNAMES`, require that exact header once, and reject unnamed/extra fields, blank logical records, empty files, malformed CSV, invalid Unicode, and unreadable artifacts with `SubmissionFormatError` context.
  - [x] Never pre-parse CSV with `splitlines()` or one-line assumptions: Story 2.5 intentionally allows quoted newlines in `evidence_summary`, and those records must round-trip correctly.
  - [x] Validate the complete Story 2.5 valid-row contract: selected non-empty `run_id`; unique non-empty UTF-8 `sample_id`; exact `parsed_label`; non-empty UTF-8 evidence; supported evidence type; lowercase `true`/`false` uncertainty; deterministic JSON-array risk flags containing only supported flags; `parse_status="valid"`; and empty `parse_error`. Do not strip, coerce, repair, or infer labels.
  - [x] Require exact ordered sample-ID equality with the official test set, not only set equality or row-count equality, and reject duplicate, missing, extra, or reordered rows before opening output files.
  - [x] Build one typed `FinalPrediction` per validated parsed row by copying the Reasoner label unchanged, setting `source_stage="reasoner"`, and recording a stable reason such as `validated_reasoner_output`.
  - [x] Stage both CSV files as unique exclusive siblings, validate the staged `final_predictions.csv` before deriving/staging `submission.csv`, and publish with no-clobber semantics only after all reads, validation, and writes succeed.
  - [x] Treat the two files as one publication operation: on failure while publishing the second file, remove only the first artifact newly published by the current operation; never remove or replace a pre-existing artifact.
  - [x] Clean all temporary files in `finally` paths and reject output paths that are not the canonical filenames directly inside the selected run directory.
  - [x] Keep `submission.py` free of model execution, prompt logic, verifier triggers, arbitration, validation metrics, top-level `submissions/` copying, and any rule-based fallback.

- [x] Add the approved `make-submission` CLI command (AC: 1, 3, 4, 5)
  - [x] Register `make-submission` only through `src/multimodal_bias/cli.py`, using the existing runtime `--config` and a required `--run-id` to select `{runs_root}/{run_id}`.
  - [x] Resolve the run directory under configured `runs_root`; reject absolute IDs, separators, `.`/`..`, NUL, symlink/path escape, missing run directories, and mismatches between directory name, parsed row `run_id`, and expected run ID.
  - [x] Load the official ordered test records through the existing data-loader boundary so test/sample-submission lineage remains the source of truth and existing layout checks are preserved.
  - [x] Catch `ConfigurationError`, `DataLayoutError`, `SubmissionFormatError`, and artifact `OSError` with concise stderr output and exit code `1` without traceback.
  - [x] On success, report `run_id`, `final_predictions_path`, `submission_path`, and `total_samples`; preserve `infer` behavior so it still creates neither downstream artifact.

- [x] Add CPU-safe submission and CLI coverage (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add `tests/test_submission.py` covering a valid multi-row artifact, stable order, typed results, exact final/submission headers, labels, UTF-8 and CSV escaping, and unchanged source artifacts.
  - [x] Add table-driven failures for missing/extra/duplicate headers, unnamed fields, blank/empty/malformed rows, invalid UTF-8, unreadable input, invalid/missing labels, every non-valid parse status, non-empty parse errors, duplicate IDs, mixed/wrong run IDs, and sample count/order mismatches.
  - [x] Cover output path escapes, existing artifacts, unique temporary files, injected first/second write and publish failures, concurrent publication, cleanup, and the guarantee that no partial pair remains.
  - [x] Extend `tests/test_cli.py` with `make-submission` help/success/error cases and assertions that `infer` alone still stops at `parsed_reasoner.csv`.
  - [x] Build all official-layout and run artifacts in temporary directories; do not require the real 8,500-row dataset.

- [x] Run validation (AC: 6)
  - [x] Run `uv sync`.
  - [x] Run `uv run pytest`.
  - [x] Run `uv run ruff check src tests`.
  - [x] Run `uv run ruff format --check src tests`.
  - [x] Run `uv run multimodal-bias --help` and confirm `make-submission` is listed.
  - [x] Run `uv run multimodal-bias --version`.
  - [x] Run a CPU-safe `infer` followed by `make-submission` smoke path using temporary official-layout fixtures and the dummy adapter; inspect both CSV artifacts and confirm no files are written under top-level `submissions/`.
  - [x] Remove generated `src/**/__pycache__` and `tests/**/__pycache__`, then rerun scaffold/cache guard checks.

### Review Findings

- [x] [Review][Patch] Validate staged final predictions against in-memory parsed predictions [src/multimodal_bias/submission.py:113]
- [x] [Review][Patch] Prevent temporary-file cleanup errors from masking a completed publication or the original failure [src/multimodal_bias/submission.py:121]
- [x] [Review][Patch] Harden rollback cleanup when second artifact publication fails [src/multimodal_bias/submission.py:508]
- [x] [Review][Patch] Validate public submission API context inputs before tuple conversion [src/multimodal_bias/submission.py:144]
- [x] [Review][Patch] Open CSV sources with no-follow semantics to preserve symlink-escape guards during read [src/multimodal_bias/submission.py:318]
- [x] [Review][Patch] Add resolver coverage for every required unsafe or missing run ID case [tests/test_cli.py:618]
- [x] [Review][Patch] Cover missing parsed input, actual unnamed fields, negative labels, extra samples, and invalid-status no-output guarantees [tests/test_submission.py:153]
- [x] [Review][Patch] Cover symmetric output/path guards for existing final predictions and escaped submission path [tests/test_submission.py:379]

## Dev Notes

### Current Workspace State

- Stories 1.1 through 2.5 are complete and marked `done`; Story 2.5's review-patch validation passed with 180 tests.
- There is no git repository, `_bmad/bmm/config.yaml`, `project-context.md`, or `sprint-status.yaml`; this story therefore uses `baseline_commit: NO_VCS` and status is tracked in the story file itself.
- `src/multimodal_bias/submission.py` currently contains only a module docstring and is the primary implementation target.
- `SubmissionFormatError` already exists in `exceptions.py`; reuse it rather than adding a second submission exception hierarchy.
- `schemas.py` already owns `ReasonerLabel`, `ParsedReasonerRecord`, and parse results but does not yet define the architecture-required `FinalPrediction`.
- `cli.py` currently exposes `validate-data`, `start-run`, `infer`, and `smoke-model`; `infer` writes raw and parsed Reasoner artifacts and intentionally stops before final/submission output.
- `data_loader.py` already validates exact ordered equality between `test/test.csv` and `sample_submission.csv`, rejects duplicate IDs/headers, and returns ordered typed `SampleRecord` objects through `load_test_records()`.
- Story 2.5's parser uses strict UTF-8 CSV fields, stable parse statuses, exact string labels, expected run/sample lineage, unique temporary files, and no-clobber publication. Match its safety posture without re-parsing model text.

### Story 2.6 Scope and Pipeline Position

This story establishes the safe Reasoner-only submission baseline:

```text
official test order + parsed_reasoner.csv
  -> strict submission validation
  -> typed FinalPrediction rows (label copied unchanged)
  -> final_predictions.csv
  -> exact sample_id,label submission.csv
```

The copied final label still originates in generated LLM text and is not a deterministic answer rule. This story may validate and serialize that label, but it must not select a fallback for an invalid row. Story 3 will add trigger detection, conditional verification, and arbitration. The `FinalPrediction`/CSV contract should therefore leave room for future source stages without pretending that arbitration already occurred.

If any parsed row is invalid, `make-submission` must fail the entire run. The architecture allows recoverable failures to become label `2` only through arbitration; submission generation is not that layer.

### Proposed Artifact Contracts

`final_predictions.csv` fixed columns:

```text
run_id,sample_id,final_label,source_stage,decision_reason
```

Story 2.6 values:

- `final_label`: exact copied `parsed_label` string (`0`, `1`, or `2`)
- `source_stage`: `reasoner`
- `decision_reason`: stable non-empty value such as `validated_reasoner_output`

`submission.csv` fixed columns:

```text
sample_id,label
```

Do not add an index column, pandas-generated unnamed column, diagnostics, run metadata, evidence, or risk flags to `submission.csv`. Use Python's standard-library `csv` module with explicit `encoding="utf-8"`, `newline=""`, and a stable `lineterminator="\n"`.

### Atomicity and Immutability Requirements

- Validate all source rows and official lineage before creating either destination.
- Use unique exclusive sibling temporary files, not predictable `.tmp` names.
- Both destination filenames are immutable/no-clobber. Re-running against a completed run must fail rather than silently replace a candidate.
- Multi-file publication cannot be one filesystem atomic primitive. Implement transactional cleanup: publish only after both staged files are complete; if publication of the second destination fails, remove the first only when this invocation can prove it created that file.
- Never delete a destination that existed before this invocation, and never clean another process's temporary file.
- The completed result is valid only when both files exist and match the same ordered typed predictions.

### Existing Files To Update

- `src/multimodal_bias/submission.py`: currently only a module docstring; add strict artifact readers/builders, fixed contracts, atomic pair writing, and the public orchestration function.
- `src/multimodal_bias/schemas.py`: preserve all frozen dataclasses/literals and add `FinalPrediction`, source-stage, and submission-result types.
- `src/multimodal_bias/cli.py`: preserve every existing command/error path and add only the approved `make-submission` surface.
- `tests/test_cli.py`: preserve current infer/model/data coverage and add make-submission integration/error behavior.
- `tests/test_submission.py`: new focused CPU-safe suite.

Do not change `parsing.py` unless a small shared public constant/type extraction is strictly necessary. Do not add submission creation to `reasoner.py`, `parsing.py`, or `run_logging.py`.

### Architecture and Compliance Guardrails

- `submission.csv` can only be written by the `make-submission` flow and only from a validated final-prediction artifact; no other command or module may emit Multimodal format.
- Final labels must remain traceable to generated LLM text. Copying a valid parsed label is allowed; keyword rules, fixed answer lists, distribution correction, Public-LB tuning, and deterministic invalid-row fallback are forbidden.
- Keep official evaluation data inference-only. Submission validation may compare IDs/order but must not inspect question wording, answers, images, or inferred semantics to choose labels.
- Keep both artifacts under `runs/{run_id}/` for audit. This story does not promote/copy candidates into top-level `submissions/`; candidate promotion belongs to later workflow.
- Preserve local/offline operation. No external package, network call, pandas dependency, database, or UI is needed.
- Target Python remains `>=3.10,<3.11`; use only Python 3.10-compatible syntax and APIs.
- Keep raw/parsed Reasoner artifacts immutable and preserve all existing run metadata.

### Previous Story Intelligence

- Story 2.5 established a fixed parsed header: `run_id`, `sample_id`, `parsed_label`, `evidence_summary`, `evidence_type`, `uncertainty_signal`, `risk_flags`, `parse_status`, `parse_error`.
- Valid parsed rows always have a strict string label; invalid/source-failure rows have no label, carry `invalid_parse`, and retain actionable `parse_error` context.
- Parser output order is checked against the active run's exact inference sample set. Submission must independently check that lineage against the official input because run artifacts can be missing, stale, or tampered with later.
- Parsed artifact publication already uses unique temporary files and no-clobber semantics. Submission output should match or strengthen that concurrency behavior.
- CLI errors are concise, use exit code `1`, and suppress traceback with `raise typer.Exit(1) from None`.
- Existing tests are CPU-only and construct minimal official layouts in `tmp_path`; reuse those patterns without requiring official data or optional model dependencies.
- Two pre-existing review concerns remain deferred: installed console-script path resolution and a lazy-import `sys.modules` cleanup issue. Do not broaden this story to unrelated cleanup unless the implementation directly touches those tests.

### Testing Requirements

Minimum assertions:

- all-valid parsed rows produce one ordered typed final prediction per official sample
- final labels are exact copies of generated parsed labels and include no fallback path
- `final_predictions.csv` has only its fixed audit columns
- `submission.csv` has exactly `sample_id,label` and no index/extra column
- labels `3`, `-1`, whitespace-padded values, empty values, and non-valid parse rows fail
- mixed/wrong run IDs, duplicates, missing/extra/reordered IDs, and count mismatch fail before output creation
- malformed/duplicate headers, extra unnamed fields, invalid UTF-8, malformed CSV, blank logical records, empty source, and unreadable source fail cleanly while quoted evidence newlines remain valid
- existing destination, path escape, symlink escape, write/publish failure, and a concurrent writer never overwrite artifacts or leave a partial new pair
- CSV quoting and UTF-8 round-trip through `csv.DictReader`
- source `raw_reasoner.jsonl` and `parsed_reasoner.csv` bytes are unchanged
- `infer` still does not create final/submission artifacts
- `make-submission` success/failure output contains no traceback
- no test imports or requires GPU/model dependencies

### Latest Technical Notes

- The official Multimodal data page states that `test` has 8,500 samples and `sample_submission.csv` contains `sample_id,label`, with labels restricted to `0`, `1`, and `2`.
- The official rules require UTF-8 CSV output and require final answers to come from generated LLM text rather than simple rules, conditional mappings, predefined answer lists, or simple voting.
- Python 3.10's standard-library `csv` documentation recommends opening CSV files with `newline=""`; `DictReader` preserves header order and exposes extra fields under the `None` key, while `DictWriter` uses the supplied `fieldnames` order. No new dependency is required.

### References

- [Source: docs/history/epics.md#Story-2.6-Generate-Validated-Final-Predictions-and-Submission-CSV]
- [Source: docs/history/epics.md#Epic-2-Offline-Evidence-Grounded-Submission-Pipeline]
- [Source: docs/history/architecture.md#Submission-Safety-Pattern]
- [Source: docs/history/architecture.md#Architectural-Boundaries]
- [Source: docs/history/architecture.md#Data-Architecture]
- [Source: docs/history/architecture.md#Format-Patterns]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md#Capabilities]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md#Constraints]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/strategy.md#Submission-Selection-Policy]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/compliance-references.md#Competition-Rules-That-Bend-Design]
- [Source: docs/history/stories/2-5-parse-reasoner-outputs-into-structured-predictions.md#Previous-Story-Intelligence]
- [Source: src/multimodal_bias/parsing.py]
- [Source: src/multimodal_bias/data_loader.py]
- [Source: 공식 원문 링크 제외]
- [Source: 공식 원문 링크 제외]
- [Source: https://docs.python.org/3.10/library/csv.html]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-06-18: Started fresh Story 2.6 implementation with `baseline_commit: NO_VCS`; no sprint-status tracking is configured.
- 2026-06-18: RED confirmed for missing final-prediction schemas, submission API, and `make-submission` command before each implementation phase.
- 2026-06-18: GREEN confirmed with 36 submission tests, 25 CLI tests, and 221 full CPU-safe tests.
- 2026-06-18: Validation passed with uv sync, pytest, Ruff lint/format, CLI help/version, infer-to-submission smoke, and cache guards.
- 2026-06-18: Review patches applied for staged artifact identity/equality checks, cleanup/rollback hardening, no-follow CSV reads, API context validation, and expanded edge-case coverage.

### Implementation Plan

- Add focused submission tests first, then define typed final-prediction/result contracts.
- Implement strict parsed-artifact validation and transactional no-clobber CSV publication in `submission.py`.
- Register `make-submission`, add CLI integration coverage, and run the complete validation matrix.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Added frozen typed `FinalPrediction`, future-compatible source-stage, and `SubmissionResult` contracts; focused and full regression tests passed (181 tests).
- Implemented strict parsed-row validation plus transactional final/submission CSV publication with no overwrite, rollback, and temporary-file cleanup; 23 focused and 203 full tests passed.
- Added path-safe `make-submission` CLI integration with official sample-order validation and clean error mapping; 24 CLI and 207 full tests passed.
- Expanded CPU-safe malformed-input, lineage, symlink, write, and concurrent-publication coverage; 61 focused and 221 full tests passed.
- Completed the required validation matrix and temporary dummy-adapter end-to-end smoke without creating top-level submission artifacts.
- Story 2.6 implementation is complete and ready for adversarial code review.
- Applied all Story 2.6 review patches; 94 focused submission/CLI tests and 254 full regression tests passed.

### File List

- docs/history/stories/2-6-generate-validated-final-predictions-and-submission-csv.md
- src/multimodal_bias/cli.py
- src/multimodal_bias/submission.py
- src/multimodal_bias/schemas.py
- tests/test_cli.py
- tests/test_submission.py

## Change Log

- 2026-06-18: Created comprehensive Story 2.6 context and moved status to ready-for-dev.
- 2026-06-18: Implemented typed final predictions, strict submission validation, transactional CSV publication, `make-submission`, and CPU-safe coverage; moved status to review.
- 2026-06-18: Applied code-review patches, completed validation, and moved status to done.
