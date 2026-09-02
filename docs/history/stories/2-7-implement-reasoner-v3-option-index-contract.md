---
baseline_commit: NO_VCS
created_at: 2026-06-20
---

# Story 2.7: Implement Reasoner v3 Option-Index Contract

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a competition developer,
I want Reasoner outputs to identify the selected answer and uncertainty answer positions independently,
so that every choice order is interpreted correctly and downstream stages never infer semantics from a number.

## Acceptance Criteria

1. Given any sample whose uncertainty option is at index 0, 1, or 2, when Reasoner v3 output is generated and parsed, then strict `FINAL_ANSWER_JSON` contains `label`, integer `uncertainty_option_index`, evidence fields, risk fields, and `schema_version="reasoner_output_v3"`.
2. Given a generated Reasoner v3 output, when parsing succeeds, then `uncertainty_signal == (label == str(uncertainty_option_index))` is enforced, uncertainty selections require `evidence_type="insufficient_evidence"`, and decisive selections require a decisive evidence type.
3. Given invalid or semantically inconsistent output, when parsing runs, then the row is invalid with no parsed label, no invented uncertainty index, no regex repair, no fixed-position mapping, and no fallback label.
4. Given `infer` produces raw Reasoner rows, when v3 is active, then raw prompt text, prompt SHA-256, image SHA-256, raw output, parse status, parse errors, `schema_version`, and `uncertainty_option_index` remain auditable.
5. Given Reasoner v2 artifacts or prompt templates, when Story 2.7 is implemented, then v2 remains unchanged for isolated A/B reproduction.
6. Given runtime configuration and prompt loading, when no explicit override is supplied, then the active Reasoner default selects the v3 prompt/schema pair; v2 can be selected only by explicit versioned path/config for A/B.
7. Given run artifacts, when parser, submission, verifier input, arbitration, or validation code reads Reasoner outputs, then v2 and v3 artifacts cannot be silently mixed in one run; incompatible headers or schema versions fail closed.
8. Given downstream code consumes parsed Reasoner rows, when this story is complete, then `ParsedReasonerRecord` preserves `uncertainty_option_index` and `schema_version` for later Story 3.1/3.2/3.3 lineage work.
9. Given an explicit v2 A/B run is requested, when the v2 prompt/schema pair is selected, then the v2 parser/artifact path remains available only under explicit v2 mode and cannot be consumed as an active v3 run.
10. CPU-safe tests cover all uncertainty positions 0/1/2, valid uncertainty and decisive cases, semantic mismatch failures, v2 preservation, header/schema mismatch failure, artifact read/write round trip, prompt loading, and no fixed-label/fallback behavior.

## Tasks / Subtasks

- [x] Define the v3 Reasoner schema contract in `src/multimodal_bias/schemas.py` and prompt guards (AC: 1, 2, 8)
  - [x] Extend `ReasonerOutput` with `uncertainty_option_index: int` and `schema_version: str`.
  - [x] Extend `ParsedReasonerRecord` with `uncertainty_option_index: int | None` and `schema_version: str | None`.
  - [x] Preserve `ReasonerLabel = Literal["0", "1", "2"]`; do not introduce integer labels or semantic label aliases.
  - [x] Add a stable schema-version constant for `reasoner_output_v3`; do not hard-code this string in multiple modules.
  - [x] Update `ReasonerOutputContract` / guard constants so v3 fields are exact and ordered.

- [x] Add `configs/prompts/reasoner_v3.yaml` while preserving v1/v2 (AC: 1, 5, 6)
  - [x] Include output fields exactly: `label`, `uncertainty_option_index`, `evidence`, `evidence_type`, `uncertainty_signal`, `protected_attribute_risk`, `schema_version`.
  - [x] Instruct that `label` is a string answer-choice index and `uncertainty_option_index` is a JSON integer answer-choice index.
  - [x] State that no numeric label has inherent person/uncertainty meaning.
  - [x] Require `schema_version="reasoner_output_v3"`.
  - [x] Keep v1 and v2 files byte-for-byte semantically available for reproduction; tests should prove they still load explicitly.

- [x] Make v3 the active default prompt/schema pair without deleting v2 (AC: 5, 6)
  - [x] Change `DEFAULT_REASONER_PROMPT_PATH` to `configs/prompts/reasoner_v3.yaml`.
  - [x] Ensure active default tests expect `reasoner_v3`.
  - [x] Keep explicit `reasoner_v1.yaml` and `reasoner_v2.yaml` load tests for A/B.
  - [x] Introduce a single source of truth for Reasoner schema mode/version so prompt version, parser expected fields, and artifact `schema_version` cannot diverge.
  - [x] Do not change model adapter, image pixel budget, decoding, or engine behavior in this story.

- [x] Implement strict v3 parsing and semantic validation in `src/multimodal_bias/parsing.py` (AC: 1, 2, 3, 4, 7, 8, 9)
  - [x] Accept only the final non-empty line starting with `FINAL_ANSWER_JSON:`.
  - [x] Reject duplicate keys, extra fields, missing fields, non-object JSON, wrong types, non-UTF-8 evidence, labels outside exact strings `"0"`, `"1"`, `"2"`, uncertainty indexes outside integer `0..2`, and wrong schema version.
  - [x] Enforce `uncertainty_signal == (label == str(uncertainty_option_index))`.
  - [x] Enforce uncertainty selection uses `insufficient_evidence`.
  - [x] Enforce decisive selection uses one of `stated_text_fact`, `objective_visible_evidence`, or `elimination`.
  - [x] Invalid rows must leave parsed label, evidence fields, uncertainty index, and schema version empty while preserving parse error context.
  - [x] Do not infer `uncertainty_option_index` from answer text, unknown phrases, label value, or regex.
  - [x] Keep any v2 parsing compatibility behind an explicit v2 schema mode; the active/default parser path must be v3.

- [x] Extend `parsed_reasoner.csv` artifact contract safely (AC: 4, 7, 8, 9)
  - [x] Update `PARSED_REASONER_FIELDNAMES` to include `uncertainty_option_index` and `schema_version`.
  - [x] Update CSV write/read paths so valid v3 rows round-trip these fields exactly.
  - [x] Reject parsed artifacts missing v3 fields when active v3 mode is expected.
  - [x] If v2 A/B parsed artifacts remain supported, define a distinct v2 fieldname constant/path expectation rather than accepting old headers through the v3 reader.
  - [x] Reject valid rows with empty or malformed v3 lineage fields.
  - [x] Update callers/tests that construct parsed rows manually.
  - [x] Preserve no-clobber atomic publication behavior from Story 2.5.

- [x] Preserve submission safety while accepting the extended parsed artifact (AC: 7, 8)
  - [x] Update `submission.py` validation to read the extended parsed header through `PARSED_REASONER_FIELDNAMES`.
  - [x] Keep `final_label` as the exact copied generated `parsed_label` in the reasoner-only path.
  - [x] Do not allow `make-submission` to synthesize labels for invalid rows.
  - [x] Keep `final_predictions.csv` and `submission.csv` headers unchanged in this story.

- [x] Prepare downstream lineage boundaries without completing Epic 3 work (AC: 7, 8)
  - [x] Update types and helper constructors so Story 3.1 can read `uncertainty_option_index` and `schema_version`.
  - [x] Do not implement Story 3.1 trigger correction here except where existing tests must be adjusted to compile with the new parsed record shape.
  - [x] If existing verifier/arbitration code still has numeric-semantic branches, leave the full logic correction to Stories 3.1–3.3 but mark tests or compatibility shims so v3 parsed records are not silently downgraded.

- [x] Add CPU-safe tests and update existing tests (AC: 1–9)
  - [x] Add parser cases for valid uncertainty at indexes 0, 1, and 2.
  - [x] Add parser cases for valid decisive labels when uncertainty is at a different index.
  - [x] Add failures for missing/wrong `schema_version`, missing/non-integer/out-of-range `uncertainty_option_index`, mismatch between `label` and `uncertainty_signal`, uncertainty with decisive evidence, decisive label with `insufficient_evidence`, duplicate JSON keys, and extra fields.
  - [x] Add prompt tests proving default prompt is v3 and explicit v2/v1 are still loadable.
  - [x] Add artifact tests proving v3 columns are written/read and old/mixed headers fail closed where required.
  - [x] Add reasoner raw-run tests proving prompt version and prompt hash/image hash audit fields remain present.
  - [x] Update submission/CLI tests to use v3 parsed headers and preserve final/submission artifact behavior.
  - [x] Search tests and code for `label 2 = uncertainty`, `parsed_label == "2"`, and `PERSON_LABELS={"0","1"}` assumptions; remove or defer only with explicit story boundary notes.

- [x] Run validation (AC: 9)
  - [x] `uv run pytest`
  - [x] `uv run ruff check src tests`
  - [x] `uv run ruff format --check src tests`
  - [x] `uv run multimodal-bias --help`
  - [x] `uv run multimodal-bias --version`
  - [x] CPU-safe dummy `infer` smoke proving `raw_reasoner.jsonl` and v3 `parsed_reasoner.csv` are produced without final/submission artifacts.

### Review Findings

- [x] [Review][Patch] Reject unknown Reasoner prompt versions instead of silently routing them to the legacy schema [src/multimodal_bias/prompting/templates.py:120]
- [x] [Review][Patch] Validate every raw row's `prompt_version` against the selected schema mode and reject mixed-version artifacts [src/multimodal_bias/parsing.py:575]
- [x] [Review][Patch] Reject whitespace-only evidence when hydrating parsed Reasoner CSV rows [src/multimodal_bias/parsing.py:397]
- [x] [Review][Patch] Reject contradictory `parse_status="valid"` plus `invalid_parse` risk flags [src/multimodal_bias/parsing.py:359]
- [x] [Review][Patch] Require a non-empty UTF-8 `parse_error` for every non-valid parsed row [src/multimodal_bias/parsing.py:368]
- [x] [Review][Patch] Validate `schema_mode` before inspecting untrusted model output [src/multimodal_bias/parsing.py:91]
- [x] [Review][Patch] Fail closed when active v3 records enter legacy fixed-label Verifier/arbitration paths, including the existing invented-label fallback [src/multimodal_bias/verifier.py:191]
- [x] [Review][Defer] Replace dummy stage routing based on an arbitrary prompt substring with an explicit generation stage [src/multimodal_bias/models/dummy.py:73] — deferred, pre-existing
- [x] [Review][Defer] Harden submission publication against concurrent same-inode source mutation [src/multimodal_bias/submission.py:593] — deferred, pre-existing

## Dev Notes

### Current Workspace State

- Stories 1.1 through 2.6 are complete and marked `done`.
- Sprint tracking exists at `sprint-status.yaml`; this story is the next corrected Gate A story.
- Existing active default prompt is `configs/prompts/reasoner_v2.yaml`.
- `configs/prompts/reasoner_v1.yaml` still contains historical fixed `label 2` uncertainty wording and must remain available only for reproduction.
- `configs/prompts/reasoner_v2.yaml` removed the fixed label-2 wording but does not require a generated `uncertainty_option_index` or `schema_version`.
- `src/multimodal_bias/parsing.py` currently parses v1/v2 fields only: `label`, `evidence`, `evidence_type`, `uncertainty_signal`, `protected_attribute_risk`.
- `PARSED_REASONER_FIELDNAMES` currently lacks `uncertainty_option_index` and `schema_version`.
- There is currently no explicit Reasoner schema-mode abstraction; prompt version and parser fields are coupled by convention. Story 2.7 should make this coupling explicit to prevent v2/v3 artifact mixing.
- `src/multimodal_bias/reasoner.py` already records raw prompt text, `prompt_sha256`, `image_sha256`, raw output, generation metadata, image status, and model load metadata. Preserve this audit contract.
- `src/multimodal_bias/submission.py` imports `PARSED_REASONER_FIELDNAMES` and should inherit the extended parsed header; final/submission output headers must not change.

### Story 2.7 Scope and Pipeline Position

This story changes the Reasoner contract and parsed artifact lineage:

```text
SampleRecord + image
  -> reasoner_v3 prompt
  -> raw_reasoner.jsonl with prompt/image/raw-output audit
  -> strict v3 parser
  -> parsed_reasoner.csv with label + uncertainty_option_index + schema_version
  -> existing reasoner-only make-submission path remains fail-closed
```

This story does not select a new model, change image resolution, run the model tournament, implement Shadow Private, or start GPU production.

This story should not fully implement corrected Verifier v2 or arbitration. It should make enough schema and artifact changes for Stories 3.1–3.3 to consume v3 lineage without guessing.

### v2 A/B Preservation Rule

Reasoner v2 remains a reproduction/control path, not the active pipeline. The implementation must support one of these safe patterns:

- Preferred: explicit schema mode/version parameters where default is v3 and v2 is accepted only when the caller explicitly requests v2; or
- Acceptable: separate v2-only helper/constants retained for tests and historical A/B fixtures while all production/infer defaults use v3.

Do not let a v2 parsed artifact pass through the active v3 reader by accident. Header differences and missing `schema_version`/`uncertainty_option_index` must fail closed in active mode.

### Required v3 Output Contract

The final generated line must be:

```text
FINAL_ANSWER_JSON:{
  "label":"0|1|2",
  "uncertainty_option_index":0|1|2,
  "evidence":"non-empty UTF-8 text",
  "evidence_type":"stated_text_fact|objective_visible_evidence|elimination|insufficient_evidence",
  "uncertainty_signal":true|false,
  "protected_attribute_risk":true|false,
  "schema_version":"reasoner_output_v3"
}
```

Semantic validation:

- If `label == str(uncertainty_option_index)`, then `uncertainty_signal` must be `true` and `evidence_type` must be `insufficient_evidence`.
- If `label != str(uncertainty_option_index)`, then `uncertainty_signal` must be `false` and `evidence_type` must be one of `stated_text_fact`, `objective_visible_evidence`, or `elimination`.
- Any mismatch is `invalid_schema`, not a repaired candidate.

### Existing Files To Update

- `configs/prompts/reasoner_v3.yaml`: new active prompt template.
- `src/multimodal_bias/prompting/guards.py`: v3 output field constants and schema version constant.
- `src/multimodal_bias/prompting/templates.py`: default prompt path and strict output-contract validation.
- `src/multimodal_bias/schemas.py`: `ReasonerOutput`, `ParsedReasonerRecord`, and related schema lineage fields.
- `src/multimodal_bias/parsing.py`: v3 strict parser, semantic validation, CSV fieldnames, artifact reader/writer.
- `src/multimodal_bias/submission.py`: parsed header validation compatibility only; do not alter final/submission headers.
- `src/multimodal_bias/models/dummy.py`: update dummy Reasoner output to emit v3 fields for CPU tests while preserving Verifier behavior.
- `tests/test_prompting.py`, `tests/test_parsing.py`, `tests/test_reasoner.py`, `tests/test_submission.py`, `tests/test_cli.py`, and any affected verifier/arbitration tests.

### Files To Avoid Unless Strictly Necessary

- Do not change `src/multimodal_bias/models/hf_vlm.py`, `models/minicpm_v.py`, or model configs for this story.
- Do not change GPU/runtime dependencies or `uv.lock` unless a test-only import issue directly requires it.
- Do not change `data_loader.py` or `image_io.py` unless current tests reveal a strict type mismatch caused by v3 fields.
- Do not alter Multimodal `submission.csv` shape.

### Known Numeric-Semantic Assumptions To Remove Or Fence

These are known hazards found during story creation:

- `src/multimodal_bias/verifier.py` currently defines `PERSON_LABELS = frozenset({"0", "1"})` and has branches such as `parsed_label == "2"`.
- `src/multimodal_bias/parsing.py` currently validates Verifier output with `label 2` as insufficient evidence.
- `src/multimodal_bias/arbitration.py` currently contains validation text requiring `label 2` to mean insufficient evidence.
- `configs/prompts/verifier_v1.yaml` still instructs “Choose label 2 when objective support is insufficient.”

Story 2.7 must remove numeric-semantic assumptions from Reasoner v3 prompt/parser/artifacts. Full Verifier and arbitration correction belongs to Stories 3.1–3.3, but this story must not add new label-2 assumptions or silently hide the old ones.

### Previous Story Intelligence

- Story 2.6 established strict reasoner-only submission publication. Keep `final_predictions.csv` and `submission.csv` immutable/no-clobber and fail-closed.
- Story 2.6 uses `PARSED_REASONER_FIELDNAMES` from `parsing.py`; changing parsed columns will affect submission tests.
- Story 2.5 established final-line-only parsing, duplicate-key rejection, deterministic JSON risk flags, source-failure rows, no fallback label, exact sample order, no-clobber parsed artifact publication, and CPU-safe tests. Preserve these patterns.
- Story 2.4 established `raw_reasoner.jsonl` with prompt/image/model audit metadata. Do not drop fields or weaken partial-file preservation behavior.
- Existing CLI errors should stay concise, exit with code `1`, and avoid tracebacks.

### Testing Requirements

Minimum focused tests:

- `parse_reasoner_output` accepts valid v3 uncertainty at index 0, 1, and 2.
- `parse_reasoner_output` accepts decisive labels with each decisive evidence type when the label differs from `uncertainty_option_index`.
- Parser rejects boolean/integer/string type mistakes exactly: label must be string, uncertainty index must be integer, booleans must be JSON booleans.
- Parser rejects `"uncertainty_option_index":"2"` as wrong type.
- Parser rejects `label == uncertainty_index` with `uncertainty_signal=false`.
- Parser rejects `label != uncertainty_index` with `uncertainty_signal=true`.
- Parser rejects uncertainty with decisive evidence and decisive selection with `insufficient_evidence`.
- Parser rejects missing/extra fields and duplicate JSON keys.
- `parse_reasoner_artifact` writes v3 parsed columns and invalid rows leave v3 semantic fields empty.
- `read_parsed_reasoner_artifact` rejects old v1/v2 headers where v3 is expected.
- Explicit v2 A/B parsing, if retained, is only reachable by explicit schema mode/helper and never by default.
- `make-submission` still succeeds for valid v3 parsed rows and still fails for invalid/source-failure rows.
- `build_reasoner_prompt()` defaults to `reasoner_v3`.
- Explicit `load_reasoner_prompt_template("configs/prompts/reasoner_v2.yaml")` and v1 still work for A/B reproduction.
- Dummy adapter Reasoner output and CLI `infer` smoke produce `prompt_version="reasoner_v3"`.
- No tests require official Multimodal data, model weights, GPU, PyTorch, Transformers, Accelerate, Pillow, or network.

### Project Structure Notes

- Importable code remains only under `src/multimodal_bias/`.
- Prompt templates stay under `configs/prompts/`.
- Run artifacts stay under `runs/{run_id}/`.
- Generated data, model weights, submissions, and run outputs must not be added to source package files.
- This is CLI-only; no UX document or UI implementation applies.

### References

- [Source: docs/history/epics.md#Story-2.7-Implement-Reasoner-v3-Option-Index-Contract]
- [Source: _bmad-output/specs/spec-reasoner-v3-contract/SPEC.md]
- [Source: _bmad-output/specs/spec-reasoner-v3-contract/output-contract.md]
- [Source: docs/history/architecture.md#Reasoner-Conditional-Verifier]
- [Source: docs/history/architecture.md#Naming-Patterns]
- [Source: docs/history/architecture.md#Format-Patterns]
- [Source: docs/history/architecture.md#Submission-Safety-Pattern]
- [Source: docs/history/stories/2-6-generate-validated-final-predictions-and-submission-csv.md]
- [Source: src/multimodal_bias/schemas.py]
- [Source: src/multimodal_bias/parsing.py]
- [Source: src/multimodal_bias/prompting/guards.py]
- [Source: src/multimodal_bias/prompting/templates.py]
- [Source: src/multimodal_bias/reasoner.py]
- [Source: src/multimodal_bias/submission.py]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-06-20: RED test confirmed missing v3 schema constant before implementation.
- 2026-06-20: Full regression initially exposed legacy v2 fixtures; migrated active fixtures to v3 and retained explicit v2 mode.

### Implementation Plan

1. Update tests for the v3 contract first.
2. Add v3 prompt/guard/schema constants.
3. Extend schema dataclasses and parsed CSV contract.
4. Implement strict parser semantic validation.
5. Update reasoner/dummy/submission/CLI tests.
6. Run full CPU-safe validation.

### Completion Notes List

- Story context created from corrected Epic 2.7, Reasoner v3 SPEC, architecture, current code, and previous Story 2.6 learnings.
- Added strict Reasoner v3 option-index schema, semantic invariants, versioned parsed artifact lineage, and fail-closed submission validation.
- Kept v1/v2 prompt files unchanged and isolated legacy parsing/artifact headers behind explicit v2 mode; active/default mode is v3.
- Preserved raw prompt/image hashes, atomic no-clobber publication, and unchanged final/submission CSV contracts.
- Validation passed: 382 tests, Ruff check/format, CLI help/version, and CPU dummy infer smoke.
- Code review patches completed: strict prompt-version whitelist, raw lineage matching, parsed-row audit invariants, v3 legacy-stage fences, and no invented arbitration fallback.
- Post-review validation passed: 388 tests and Ruff check/format.

### File List

- docs/history/stories/2-7-implement-reasoner-v3-option-index-contract.md
- sprint-status.yaml
- deferred-work.md
- review-prompt-story-2-7-acceptance-auditor.md
- review-prompt-story-2-7-blind-hunter.md
- review-prompt-story-2-7-edge-case-hunter.md
- configs/prompts/reasoner_v3.yaml
- src/multimodal_bias/cli.py
- src/multimodal_bias/models/dummy.py
- src/multimodal_bias/parsing.py
- src/multimodal_bias/prompting/guards.py
- src/multimodal_bias/prompting/templates.py
- src/multimodal_bias/schemas.py
- src/multimodal_bias/submission.py
- src/multimodal_bias/verifier.py
- src/multimodal_bias/arbitration.py
- tests/test_cli.py
- tests/test_model_adapter.py
- tests/test_parsing.py
- tests/test_prompting.py
- tests/test_reasoner.py
- tests/test_reasoner_v3_contract.py
- tests/test_submission.py
- tests/test_arbitration.py

## Change Log

- 2026-06-20: Created comprehensive Story 2.7 context and moved status to ready-for-dev.
- 2026-06-20: Implemented and validated Reasoner v3 option-index contract; moved story to review.
- 2026-06-20: Resolved all 7 code-review patch findings; marked Story 2.7 done with 2 pre-existing items deferred.
