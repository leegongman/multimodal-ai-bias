---
baseline_commit: NO_VCS
---

# Story 3.2: Run Conditional Verifier for Triggered Samples

Status: backlog

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a competition developer,
I want the Verifier to independently review only triggered samples,
so that risky predictions can be corrected without turning the pipeline into an expensive unconditional two-pass system.

## Acceptance Criteria

1. Given ordered Reasoner v3, trigger-decision, and sample inputs from one run, when conditional verification runs, then only triggered samples are attempted while run/sample order, schema version, selected-label lineage, and Reasoner uncertainty-index lineage are preserved.
2. Given a triggered sample, when Verifier v2 runs, then it independently generates strict JSON containing selected answer index, integer `uncertainty_option_index`, reason, evidence type, uncertainty signal, protected-attribute risk, concrete-defect signal, and objective-support signal.
3. Given generated Verifier text, when it is parsed, then only the approved final marker and exact schema are accepted; the same option-index semantic invariant as Reasoner v3 is enforced and malformed output produces no candidate.
4. Given the complete ordered set, when `verification.jsonl` is written, then every row records prompt/schema version and hashes, before/after label and uncertainty-index lineage, raw output, parsed fields, generation metadata, status, timing, and errors; non-triggered rows remain explicit.
5. Given successful Verifier parsing, when both candidates are valid and their selected indexes differ, then the verification record includes the post-Verifier `reasoner_verifier_conflict` event; no-conflict, one-invalid and both-invalid states remain distinct, and the event does not trigger a second pass or select the final label.
6. Given image, prompt, generation, or parse failure for a triggered sample, when verification continues, then the failure is recorded per sample without creating any label; Story 3.3 may use only surviving generated candidates.
7. Given `uv run multimodal-bias verify-risky --run-id <run_id>`, when the configured run and official inputs are valid, then the command reads that run's immutable `parsed_reasoner.csv`, writes `verification.jsonl` beside it exactly once, reports triggered/verified/skipped/failed counts, and rejects unsafe run IDs, mixed run IDs, duplicate or reordered sample IDs, malformed artifacts, existing output, and remote/non-local model configuration without a traceback.
8. CPU-safe tests cover triggered-only generation, option-index positions 0/1/2, semantic mismatch rejection, all output states, deterministic ordering, conflict recording, immutable publication, CLI behavior, and zero-trigger behavior.

## Corrective Work Required (2026-06-20)

- [ ] Add `configs/prompts/verifier_v2.yaml`; preserve `verifier_v1.yaml` unchanged for reproduction.
- [ ] Extend Verifier schemas/parser/artifact with integer `uncertainty_option_index` and schema version.
- [ ] Remove all instructions or parser branches that assign uncertainty meaning to numeric label 2.
- [ ] Pass original ordered answers plus Reasoner v3 semantic fields without allowing trigger-to-label mapping.
- [ ] Move `reasoner_verifier_conflict` out of the pre-Verifier trigger type/order into a distinct post-Verifier comparison event contract.
- [ ] Add position 0/1/2 and malformed-semantic regression tests, then rerun review.

## Historical Tasks / Subtasks (pre-correction implementation)

- [x] Define typed Verifier prompt, output, record, and run-result contracts in `src/multimodal_bias/schemas.py` (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add the architecture-required `VerifierOutput` dataclass with `label`, `reason`, `evidence_type`, `reasoner_defect_found`, and `objective_support`; reuse `ReasonerLabel` and `EvidenceType`.
  - [x] Add frozen Verifier prompt/template contracts, `VerifierParseStatus` values parallel to Reasoner parsing, and stable execution status literals for `verified`, `skipped_not_triggered`, `image_failed`, `prompt_failed`, `inference_failed`, and `parse_failed`.
  - [x] Add a frozen parsed-Verifier result that contains `VerifierOutput | None`, exact parse status, and parse error so malformed generated text is data rather than an uncaught per-sample exception.
  - [x] Add a frozen per-sample verification record carrying run/sample lineage, ordered trigger tuple, before/after labels, raw output, parsed fields, model/generation metadata, elapsed time, status, and error fields.
  - [x] Add a frozen run result with `verification_path`, ordered records, total, triggered, verified, skipped, and failed counts.
  - [x] Keep `after_label` explicitly defined as the parsed Verifier candidate, not the final arbitrated label.

- [x] Add a versioned independent Verifier prompt contract (AC: 2, 3, 5)
  - [x] Add `configs/prompts/verifier_v1.yaml` with a dedicated `FINAL_VERIFICATION_JSON` marker and exact fields `label`, `reason`, `evidence_type`, `reasoner_defect_found`, and `objective_support`.
  - [x] Extend `src/multimodal_bias/prompting/guards.py` with separate `VERIFIER_*` marker, field, template-key, and placeholder constants without changing the existing Reasoner constants.
  - [x] Extend `src/multimodal_bias/prompting/templates.py` with strict UTF-8/YAML/key/placeholder/schema validation and a builder that accepts `SampleRecord`, `ParsedReasonerRecord`, and ordered triggers.
  - [x] Historical Verifier v1 behavior is preserved only for reproduction; Verifier v2 selects the uncertainty answer wherever it appears and never assigns semantic meaning to label 2.
  - [x] Do not include answer mappings, evaluation-set-derived rules/examples, Public LB hints, or deterministic instructions to flip a specific trigger category.

- [x] Implement strict Verifier-output parsing and parsed-Reasoner artifact loading in `src/multimodal_bias/parsing.py` (AC: 3, 6, 7)
  - [x] Add a pure `parse_verifier_output` path that inspects the final non-empty line, requires `FINAL_VERIFICATION_JSON:`, reuses the existing strict JSON helper, rejects duplicate/non-standard JSON keys and extra/missing fields, validates exact label/evidence/boolean types, and returns a typed invalid result with no label on failure.
  - [x] Preserve `parse_reasoner_output`, `parse_reasoner_artifact`, `PARSED_REASONER_FIELDNAMES`, and all Story 2.5 behavior unchanged.
  - [x] Add a public strict reader for existing `parsed_reasoner.csv` that validates exact headers, UTF-8, regular-file/no-follow behavior where supported, expected run ID, unique sample IDs, expected ordering/count, status/risk flag vocabulary, and field consistency before hydrating typed records.
  - [x] Never call `parse_reasoner_artifact` to overwrite or regenerate an existing parsed artifact during verification.

- [x] Implement conditional Verifier orchestration and immutable JSONL writing in `src/multimodal_bias/verifier.py` (AC: 1, 2, 4, 5, 6, 7)
  - [x] Reuse `detect_verification_trigger_report`; do not duplicate or weaken Story 3.1 trigger semantics.
  - [x] Align parsed records, trigger decisions, and sample records by exact ordered IDs before model or file side effects.
  - [x] Validate the Verifier prompt template for every command, then filter to triggered samples before image loading and model generation; if zero rows are triggered, do not instantiate/load the model and still write one explicit skipped record per sample.
  - [x] Load the configured local adapter once when at least one trigger exists, then call `generate` exactly once per triggered sample using image bytes and the independent Verifier prompt.
  - [x] Emit per-sample failure records for image, prompt, inference, and parse failures while continuing later samples; leave `after_label=None` for all failures.
  - [x] Append `reasoner_verifier_conflict` only to a successful verification record whose non-null before/after labels differ, preserving `VERIFICATION_TRIGGER_NAMES` order and never scheduling another pass.
  - [x] Write all rows as UTF-8 JSONL via a temporary file plus no-overwrite atomic publication; reject pre-existing `verification.jsonl`, symlink/path escapes, mixed run IDs, duplicates, reordered IDs, and partial output on run-level failure.
  - [x] Keep `submission.py`, `final_predictions.csv`, `submission.csv`, and `arbitration.py` untouched; Story 3.2 records candidates and evidence but does not select final labels.

- [x] Register the `verify-risky` command in `src/multimodal_bias/cli.py` (AC: 7)
  - [x] Historical CLI defaulted to `verifier_v1.yaml`; corrective implementation changes the default to `configs/prompts/verifier_v2.yaml` while retaining an explicit v1 reproduction path.
  - [x] Resolve the run directory through the existing safe run-ID boundary, load official sample records in exact order, load/validate the run's parsed Reasoner artifact, and invoke conditional verification.
  - [x] Map `ConfigurationError`, `DataLayoutError`, `ModelLoadError`, `InferenceError`, `ParseError`, and artifact `OSError` to concise non-zero CLI exits without tracebacks.
  - [x] Print `run_id`, `verification_path`, total, triggered, verified, skipped, and failed counts on success.

- [x] Keep the CPU dummy adapter useful for end-to-end Verifier tests (AC: 2, 3, 8)
  - [x] Update `src/multimodal_bias/models/dummy.py` to emit deterministic Verifier-schema output only when the prompt requests `FINAL_VERIFICATION_JSON`, while preserving its existing Reasoner output byte-for-byte for Reasoner prompts.
  - [x] Do not add runtime ML dependencies or import PyTorch/Transformers/Pillow in default CPU tests.

- [x] Add focused CPU-safe coverage (AC: 1, 2, 3, 4, 5, 6, 7, 8)
  - [x] Extend `tests/test_verifier.py` for safe/triggered mixes, zero-trigger runs, exact adapter call counts, full ordered JSONL rows, all failure statuses, before/after lineage, conflict category ordering, non-mutation, and no partial/existing artifact behavior.
  - [x] Extend `tests/test_parsing.py` for valid and malformed Verifier output plus strict parsed-Reasoner artifact reads without regressing Reasoner parsing.
  - [x] Extend `tests/test_prompting.py` for Verifier template schema, placeholders, safety instructions, malformed YAML, duplicates, missing/extra keys, and exact marker/field contracts.
  - [x] Extend `tests/test_cli.py` for `verify-risky` help, dummy success, zero-trigger success, unsafe/missing run ID, malformed parsed artifact, invalid prompt/model/data, existing output, and clean exception mapping.
  - [x] Extend `tests/test_model_adapter.py` to prove dummy Verifier output support and unchanged Reasoner behavior.
  - [x] Assert that non-triggered rows never invoke image loading or `adapter.generate`, that zero-trigger runs never load an adapter, and that no final/submission artifact is written.

- [x] Run validation (AC: 8)
  - [x] Run `uv sync`.
  - [x] Run `uv run pytest`.
  - [x] Run `uv run ruff check src tests`.
  - [x] Run `uv run ruff format --check src tests`.
  - [x] Run `uv run multimodal-bias --help` and confirm `verify-risky` is listed.
  - [x] Run `uv run multimodal-bias --version`.
  - [x] Remove generated `src/**/__pycache__` and `tests/**/__pycache__`, then run `uv run python -B -m pytest tests/test_scaffold.py -q`.

## Dev Notes

### Current Workspace State

- Stories 1.1 through 3.1 are complete and marked `done`; Story 3.1 finished with all six review patches resolved, 35 focused Verifier-trigger tests, and 289 full CPU-safe tests.
- There is no git repository, `_bmad/bmm/config.yaml`, `project-context.md`, or `sprint-status.yaml`; use `baseline_commit: NO_VCS` and track status in this story file.
- `src/multimodal_bias/verifier.py` currently owns pure deterministic trigger detection. Preserve the six pre-Verifier names and ordering, invalid-parse short-circuiting, sole-support appearance semantics, visual grounding normalization, immutable report counts, and defensive input validation; move conflict to the distinct post-Verifier event contract.
- `src/multimodal_bias/schemas.py` already contains `ParsedReasonerRecord`, trigger decision/report contracts, model request/result metadata, and run/sample schemas. Extend these typed boundaries instead of passing anonymous dictionaries.
- `src/multimodal_bias/models/adapter.py` already enforces an existing local snapshot, `local_files_only=True`, pinned revision/hash for `hf_local`, and lazy optional dependency imports. Reuse it unchanged unless a narrowly scoped adapter contract correction is required.
- `src/multimodal_bias/reasoner.py` demonstrates prepare-before-side-effects, one adapter load, per-sample failure records, raw-output preservation, and temporary JSONL publication. Reuse these patterns without coupling Verifier business logic to Reasoner internals.
- `src/multimodal_bias/parsing.py` owns strict generated-output parsing and immutable artifact behavior. Extend it without changing the Reasoner marker, schema, CSV field order, or existing failure classifications.
- `src/multimodal_bias/cli.py` uses Typer `Annotated` options and explicit project-exception mapping. Follow the same command shape and `CliRunner` test style.

### Story 3.2 Scope and Pipeline Position

```text
parsed_reasoner.csv + official ordered samples
  -> Story 3.1 trigger decisions
  -> triggered-only image load + local Verifier generation
  -> strict Verifier parse
  -> verification.jsonl (one row per sample, including skips/failures)
  -> Story 3.3 arbitration chooses final labels
```

This story does not arbitrate, write final predictions, or change submission behavior. `after_label` is only the Verifier's parsed candidate. A disagreement may add `reasoner_verifier_conflict`, but it must not automatically flip the final answer.

### Verification Record Contract

Use stable JSON field names and deterministic serialization. At minimum each row should contain:

```text
run_id
sample_id
triggers
requires_verification
before_label
raw_verifier_output
after_label
verifier_reason
verifier_evidence_type
reasoner_defect_found
objective_support
prompt_version
image_status
verifier_parse_status
generation_metadata
model_load_metadata
elapsed_seconds
status
error_type
error_message
```

Status invariants:

- `skipped_not_triggered`: empty triggers, `requires_verification=false`, prompt version retained, and all generated-output/parse/model/error fields null except elapsed time if measured.
- `verified`: non-empty trigger tuple, raw output present, valid parsed fields present, no error.
- `image_failed`, `prompt_failed`, `inference_failed`: triggered row, `after_label=None`, appropriate error context; raw output is null except where a later-stage failure already produced it.
- `parse_failed`: triggered row, raw output preserved, parsed fields and `after_label` null, parse error present.
- A successful differing before/after label appends `reasoner_verifier_conflict`; failures and null before labels do not.

### Conditional Execution and Runtime Guardrails

- Do not preprocess all images merely to discard safe rows. Build the trigger report first, then load images for triggered `SampleRecord` values only.
- Do not instantiate/load the model when `triggered_sample_count == 0`.
- Load one adapter per command, not one adapter per sample.
- Do not retry a generated answer inside this story; retries could silently turn conditional verification into an uncontrolled multi-pass system. Record failure and leave recovery to later policy work.
- Preserve practical runtime and report elapsed time for every generated attempt. The primary strategy remains one Reasoner pass plus sparse verification, not unconditional two-pass inference.

### Prompt and Parser Guardrails

- The Verifier prompt must be independent: it may inspect the Reasoner candidate, evidence, parse state, and trigger category, but it must solve from the original context/question/answers/image and identify a concrete defect rather than blindly oppose the Reasoner.
- Use the same evidence vocabulary: `stated_text_fact`, `objective_visible_evidence`, `elimination`, `insufficient_evidence`.
- `reasoner_defect_found=true` means the Verifier identified a concrete first-pass defect. Evidence and uncertainty consistency are determined from the Verifier-generated answer index and uncertainty index, never from a fixed numeric label.
- Parser validation must reject inconsistent boolean/label/evidence combinations as `parse_failed` or preserve enough typed data for Story 3.3 to reject them. Do not normalize an invalid output into a valid candidate.
- Keep strict final-line parsing and duplicate-key rejection consistent with Story 2.5. Do not search arbitrary earlier text for a convenient label.

### Artifact Safety and Traceability

- `verification.jsonl` belongs inside the existing `runs/{run_id}/`; `verify-risky` must not create a second run directory or modify `config.resolved.yaml`, `environment.json`, `raw_reasoner.jsonl`, or `parsed_reasoner.csv`.
- Validate exact run/sample identity and ordering before model calls. Do not join by position after detecting mismatched IDs.
- Publish the output only after every expected row has been serialized. Use a temporary sibling file and a no-overwrite atomic link/publication pattern matching existing parser/submission safety behavior.
- A pre-existing regular file or symlink named `verification.jsonl` is an immutable-artifact conflict and must fail without replacement.
- JSONL must be UTF-8 with one object per line, no blank lines, and no NaN/Infinity values; serialize with an explicit non-finite-value guard such as `allow_nan=False`.

### Architecture and Compliance Guardrails

- Final labels must remain generated-model candidates plus later arbitration, never pure rules, majority vote, fixed answer lists, or trigger-to-label mappings.
- Use only local filesystem inputs and local model snapshots; no remote API, Hub inference, or network fallback.
- Do not inspect evaluation-set wording, answer positions, image patterns, inferred labels, or Public LB movement to create Verifier prompt rules.
- Keep data and generated run artifacts outside importable source. Do not add a database, service, notebook dependency, web UI, or network endpoint.
- Python remains `>=3.10,<3.11`; no new package is required for this story.

### Existing Files To Update

- `configs/prompts/verifier_v2.yaml`: corrected option-index Verifier prompt; preserve `verifier_v1.yaml` unchanged.
- `src/multimodal_bias/schemas.py`: typed Verifier contracts and statuses.
- `src/multimodal_bias/prompting/guards.py`: Verifier marker/field constants.
- `src/multimodal_bias/prompting/templates.py`: strict Verifier template load/build path while preserving Reasoner behavior.
- `src/multimodal_bias/parsing.py`: Verifier output parser and strict parsed-Reasoner reader.
- `src/multimodal_bias/verifier.py`: conditional execution and immutable `verification.jsonl` writer; preserve trigger detection.
- `src/multimodal_bias/models/dummy.py`: deterministic Verifier output branch for CPU tests; preserve Reasoner branch.
- `src/multimodal_bias/cli.py`: register `verify-risky`.
- `tests/test_prompting.py`, `tests/test_parsing.py`, `tests/test_verifier.py`, `tests/test_model_adapter.py`, `tests/test_cli.py`: focused CPU-safe coverage.
- `docs/history/stories/3-2-run-conditional-verifier-for-triggered-samples.md`: task/status/agent record updates during implementation.

Do not update:

- `src/multimodal_bias/arbitration.py`: Story 3.3 owns final decision policy.
- `src/multimodal_bias/submission.py`: Story 2.6 Reasoner-only submission remains unchanged until arbitration integration.
- `configs/prompts/reasoner_v1.yaml`: Verifier work must not alter the proven Reasoner prompt contract.
- `pyproject.toml` or `uv.lock`: no new dependency is needed.

### Previous Story Intelligence

- Story 3.1 review fixed invalid-parse short-circuiting. A triggered invalid row may have no before label or evidence; Verifier orchestration must still reconstruct the independent task from `SampleRecord` and must not demand valid Reasoner fields.
- The strict parsed-artifact reader must preserve the same short-circuit contract: an `invalid_parse` risk flag is sufficient to permit absent valid-row fields even if an externally constructed row reports `parse_status="valid"`; do not validate those fields before classifying the row.
- Appearance-only detection now requires sole-support semantics, and visual cues are punctuation-normalized with negation-aware concrete grounding. Reuse the emitted trigger decisions; do not reclassify evidence in the orchestration layer.
- `VerificationTriggerReport.per_trigger_counts` is immutable. Do not mutate its mappings or decisions to add conflict; construct a new ordered tuple only in the resulting verification record.
- Existing report detection rejects non-sequences with `ParseError`; retain typed sequence validation at new public boundaries.
- Existing validation commands can create `__pycache__`; remove generated caches before final scaffold/cache guard validation.
- Story 2.4 established prepared inputs, raw output preservation, per-sample error containment, and temporary-file cleanup. Story 2.5 established strict final-line JSON parsing with duplicate-key rejection. Story 2.6 established no-follow reads, exact run/sample identity checks, no-overwrite publication, and rollback on partial artifact failure.

### Testing Requirements

Minimum assertions:

- a mixed safe/triggered input calls adapter generation only for triggered IDs and writes rows for every ID in original order
- an image or prompt failure for a triggered ID causes zero generation calls for that ID, while a prepared triggered ID causes exactly one
- zero-trigger input does not create/load an adapter and writes only `skipped_not_triggered`
- all six pre-Verifier trigger names remain stable; conflict exists only as one post-Verifier event and is never appended to the initial trigger tuple
- invalid Reasoner parse rows can be verified with `before_label=None`
- Verifier output accepts only the final non-empty `FINAL_VERIFICATION_JSON:` line and exact field set
- duplicate keys, non-standard constants, invalid labels, empty/non-UTF-8 reason, unsupported evidence type, non-boolean flags, and inconsistent field combinations fail without fallback
- generated raw text survives parse failure in `verification.jsonl`
- image/prompt/inference/parse failures remain per-sample and do not stop later rows
- expected run ID/sample order/count, duplicate IDs, malformed CSV booleans/risk flags/statuses, unsafe paths, symlinks, existing output, and write failures are rejected cleanly
- output publication is atomic and leaves no temporary/partial `verification.jsonl`
- `verify-risky --help` is installed and success/failure output contains no traceback
- no verification path writes `final_predictions.csv` or `submission.csv`
- default test imports remain free of PyTorch, Transformers, Accelerate, and Pillow

### Latest Technical Notes

- Current Transformers guidance uses `HF_HUB_OFFLINE=1` to prevent Hub HTTP calls and `local_files_only=True` for local-only `from_pretrained` resolution. The existing adapter already enforces the latter; do not introduce a network fallback. [Source: https://huggingface.co/docs/transformers/main/installation#offline-mode]
- Current Typer guidance tests commands with `typer.testing.CliRunner`, `runner.invoke`, explicit exit-code/output assertions, and separate stdout/stderr access. Continue the repository's existing test pattern. [Source: https://typer.tiangolo.com/tutorial/testing/]
- Do not upgrade Typer, PyYAML, pytest, Ruff, Transformers, or model runtime dependencies in this story. Version changes require separate validation and are unrelated to FR10.

### References

- [Source: docs/history/epics.md#Story-3.2-Run-Conditional-Verifier-for-Triggered-Samples]
- [Source: docs/history/epics.md#Epic-3-Bias-Safe-Conditional-Verification-and-Arbitration]
- [Source: docs/history/epics.md#Requirements-Inventory]
- [Source: docs/history/architecture.md#Reasoner-+-Conditional-Verifier]
- [Source: docs/history/architecture.md#Run-Artifact-Formats]
- [Source: docs/history/architecture.md#Architectural-Boundaries]
- [Source: docs/history/architecture.md#Error-Handling-Patterns]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md#Capabilities]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md#Constraints]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/strategy.md#Conditional-Verification]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/strategy.md#Runtime-and-Logging-Contract]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/compliance-references.md#Competition-Rules-That-Bend-Design]
- [Source: docs/history/stories/3-1-detect-verification-trigger-conditions.md#Previous-Story-Intelligence]
- [Source: src/multimodal_bias/schemas.py]
- [Source: src/multimodal_bias/verifier.py]
- [Source: src/multimodal_bias/reasoner.py]
- [Source: src/multimodal_bias/parsing.py]
- [Source: src/multimodal_bias/prompting/templates.py]
- [Source: src/multimodal_bias/models/adapter.py]
- [Source: src/multimodal_bias/cli.py]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-06-19: Created Story 3.2 context with `baseline_commit: NO_VCS`; no sprint-status tracking is configured.
- 2026-06-19: RED confirmed for missing Verifier schema/prompt, parser/reader, conditional runner, dummy output, and `verify-risky` CLI contracts.
- 2026-06-19: GREEN completed with triggered-only generation, full ordered verification records, per-sample failure containment, conflict logging, and immutable JSONL publication.
- 2026-06-19: Final validation passed with 336 CPU-safe tests, Ruff lint/format, installed CLI help/version, and clean scaffold/cache guards.

### Implementation Plan

- Add failing CPU-safe tests first for Verifier prompt/parser contracts, triggered-only model calls, full-row JSONL traceability, and CLI behavior.
- Add typed contracts and versioned Verifier prompt, then implement strict parsing and parsed-artifact hydration.
- Implement conditional orchestration and immutable artifact publication, register `verify-risky`, and run full validation.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Added frozen Verifier prompt/output/parse/record/run contracts and a versioned independent Verifier prompt with strict schema validation.
- Added strict Verifier final-line parsing and a no-follow typed reader for existing `parsed_reasoner.csv` artifacts.
- Implemented triggered-only local Verifier execution, explicit skip/failure rows, stable conflict categorization, UTF-8-safe raw output preservation, and no-overwrite atomic `verification.jsonl` publication.
- Registered `verify-risky` and extended the CPU dummy adapter without changing existing Reasoner output behavior.
- Added CPU-safe prompt, parser, orchestration, adapter, artifact-safety, and CLI coverage; completed final validation with 336 tests passing.

### File List

- docs/history/stories/3-2-run-conditional-verifier-for-triggered-samples.md
- configs/prompts/verifier_v1.yaml
- src/multimodal_bias/cli.py
- src/multimodal_bias/models/dummy.py
- src/multimodal_bias/parsing.py
- src/multimodal_bias/prompting/guards.py
- src/multimodal_bias/prompting/templates.py
- src/multimodal_bias/schemas.py
- src/multimodal_bias/verifier.py
- tests/test_cli.py
- tests/test_model_adapter.py
- tests/test_parsing.py
- tests/test_prompting.py
- tests/test_verifier.py

## Change Log

- 2026-06-20: Reopened by approved Correct Course; Verifier v2 must generate and preserve option-index semantics.
- 2026-06-19: Created Story 3.2 context file and set status to ready-for-dev.
- 2026-06-19: Implemented conditional Verifier contracts, prompt/parser, triggered-only execution, immutable verification artifact, `verify-risky` CLI, and CPU-safe tests; moved status to review.
