---
baseline_commit: NO_VCS
---

# Story 1.4: Load Images With Per-Sample Status

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a competition developer,
I want image loading and preprocessing to report per-sample status,
so that image failures are auditable and do not silently corrupt predictions.

## Acceptance Criteria

1. Given parsed `SampleRecord` objects, when the image loader processes them, then it returns one structured result per sample in input order.
2. Valid local image files are loaded into a model-adapter-ready payload containing `sample_id`, resolved path, image bytes, and detected image format.
3. Missing, unreadable, or corrupt/unrecognized image files produce structured failure status with `sample_id`, path, and an actionable error message.
4. Image-load success and failure counts are available for later run metrics without scanning raw logs.
5. The image loader lives in `src/multimodal_bias/image_io.py`; shared typed result objects live in `schemas.py`.
6. CPU-safe tests cover success, ordering, missing files, unreadable paths, corrupt/unrecognized bytes, and failure counts without official Multimodal data, model weights, GPU, Pillow, torch, or network access.

## Tasks / Subtasks

- [x] Define image-load result schemas (AC: 1, 2, 3, 4, 5)
  - [x] Add typed image status values in `src/multimodal_bias/schemas.py`, such as `ImageLoadStatus = Literal["loaded", "missing", "unreadable", "corrupt"]`.
  - [x] Add `ImageLoadResult` as a frozen dataclass with `sample_id`, `image_path`, `status`, `image_bytes`, `image_format`, and `error_message`.
  - [x] Add `ImageLoadReport` as a frozen dataclass containing ordered `results` plus `success_count` and `failure_count` properties.
  - [x] Keep schemas stdlib-only. Do not add Pydantic or model/image dependencies.

- [x] Implement CPU-safe image loading in `image_io.py` (AC: 1, 2, 3, 4, 5)
  - [x] Add `load_sample_images(records: Iterable[SampleRecord]) -> ImageLoadReport`.
  - [x] Preserve input `SampleRecord` ordering exactly.
  - [x] For each record, read bytes from `record.image_path` without modifying data.
  - [x] Detect at least JPEG, PNG, GIF, and WebP by stable byte signatures; official data is expected to be JPEG, but tests should not depend on official data.
  - [x] Return status `loaded` only when bytes are non-empty and a supported image signature is detected.
  - [x] Return status `missing` when the path does not exist.
  - [x] Return status `unreadable` when the path exists but is not a regular file or cannot be read.
  - [x] Return status `corrupt` when bytes are empty or image format is unrecognized.
  - [x] Keep this story limited to bytes + format detection. Do not decode, resize, normalize, create tensors, import PIL, or invoke model processors.

- [x] Add CPU-safe tests (AC: 1, 2, 3, 4, 6)
  - [x] Add `tests/test_image_io.py`.
  - [x] Build `SampleRecord` objects directly in tests; do not use official Multimodal data or persistent fixtures.
  - [x] Test a valid JPEG-like file returns `loaded`, `image_format == "jpeg"`, bytes populated, no error, and correct `sample_id`.
  - [x] Test multiple records preserve result order.
  - [x] Test missing image path returns `missing`.
  - [x] Test directory path or read failure returns `unreadable`.
  - [x] Test invalid bytes and empty files return `corrupt`.
  - [x] Test `ImageLoadReport.success_count` and `failure_count`.

- [x] Preserve existing data-loader and CLI behavior (AC: 5, 6)
  - [x] Do not change `load_test_records` behavior except for imports if needed.
  - [x] Do not add image loading to `validate-data`; layout validation remains metadata/path validation only.
  - [x] Do not add prompt construction, model loading, inference, submission writing, or validation metrics in this story.

- [x] Run validation (AC: 6)
  - [x] Run `uv sync`.
  - [x] Run `uv run pytest`.
  - [x] Run `uv run ruff check src tests`.
  - [x] Run `uv run ruff format --check src tests`.
  - [x] Run `uv run multimodal-bias --help`.
  - [x] Run `uv run multimodal-bias --version`.
  - [x] Run `uv run multimodal-bias validate-data --data-root data/raw/open` and confirm it still fails clearly until official extracted data is present.

### Review Findings

- [x] [Review][Patch] Handle path resolution failures as unreadable per-sample results [src/multimodal_bias/image_io.py:15]
- [x] [Review][Patch] Constrain `image_format` to supported detector values [src/multimodal_bias/schemas.py:41]
- [x] [Review][Patch] Add GIF and WebP detector coverage [tests/test_image_io.py:42]
- [x] [Review][Patch] Add coverage for `read_bytes()` OSError unreadable branch [tests/test_image_io.py:75]

## Dev Notes

### Current Workspace State

- Story 1.1, Story 1.2, and Story 1.3 are complete and marked `done`.
- There is no git repository and no `_bmad/bmm/config.yaml` or `sprint-status.yaml` in this workspace.
- `src/multimodal_bias/image_io.py` currently contains only a module docstring.
- `src/multimodal_bias/schemas.py` currently contains `DataLayoutReport` and `SampleRecord`.
- `src/multimodal_bias/data_loader.py` owns official layout validation and `load_test_records`.
- The project currently has no image-processing dependency. Story 1.4 should stay stdlib-only unless the user explicitly approves a dependency change.

### Story 1.4 Scope

Implement per-sample image IO status only.

Do not implement:

- image resize, normalization, tensor conversion, or batch collation
- PIL/Pillow, torch, transformers, or model processor integration
- model adapter execution
- prompt construction or inference
- run artifact writing, metrics JSON, or validation reports
- any prompt rule, training example, validation example, or answer mapping derived from evaluation-set images

### Image Payload Contract

Use a lightweight bytes-based payload for now because Story 2.3 will define the real model adapter interface later. A loaded result should carry:

- `sample_id`
- resolved `image_path`
- `status == "loaded"`
- raw `image_bytes`
- detected `image_format`, such as `jpeg`, `png`, `gif`, or `webp`
- `error_message is None`

Failure results should carry the same `sample_id` and path, `image_bytes is None`, `image_format is None`, and a short error message suitable for later logs.

### Implementation Guidance

- Implement in `image_io.py`, not in `data_loader.py`.
- Use `collections.abc.Iterable` for the input type and return an immutable tuple inside `ImageLoadReport`.
- Prefer private helpers such as `_load_one_image` and `_detect_image_format`.
- Keep status strings stable because later run metrics and logging will aggregate them.
- A byte-signature detector is sufficient for this story. It should catch empty files and obvious non-image/corrupt files without requiring image decoder dependencies.
- Do not mutate, copy, normalize, or delete files under `data/raw/open`.

### Previous Story Intelligence

- Story 1.2 validates image paths exist under the official split image directory before parsing.
- Story 1.3 `SampleRecord.image_path` is already a resolved path under the configured `open/` root.
- Story 1.3 deliberately did not load or decode images; Story 1.4 owns that boundary.
- Story 1.1 scaffold guards require artifact placeholder directories to contain only `.gitkeep`; use `tmp_path` for all image test files.
- Direct CLI execution can create `__pycache__` under `src/`; remove generated cache artifacts before final pytest if needed so scaffold guard tests pass.

### Architecture and Compliance Guardrails

- Use `src/multimodal_bias/` as the only importable package root.
- Add shared typed data structures to `schemas.py`.
- Keep raw data read-only under `data/raw/`; generated artifacts belong under `data/processed/`, `runs/`, or `submissions/`.
- No database, web UI, network API, remote model API, or interactive labeling product is allowed.
- `test.csv` and images are inference-only inputs. This story may load bytes needed for inference, but must not derive prompt rules, training data, validation examples, answer mappings, or heuristics from evaluation-set images or inferred labels.
- All code and test artifacts must remain UTF-8.
- This image status boundary supports later parse/image-load failure metrics and Private/Hidden generalization auditing.

### Testing Requirements

Minimum tests:

- valid JPEG-like bytes produce one loaded result
- result order follows input `SampleRecord` order
- missing path produces `missing`
- directory path or read failure produces `unreadable`
- empty file and random bytes produce `corrupt`
- report success and failure counts are correct
- existing Story 1.1 through Story 1.3 tests remain green

Recommended commands:

```bash
uv sync
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
uv run multimodal-bias --help
uv run multimodal-bias --version
uv run multimodal-bias validate-data --data-root data/raw/open
```

The final `validate-data` command is expected to fail clearly until official extracted data replaces the current `.gitkeep`-only placeholder.

### References

- [Source: docs/history/epics.md#Story-1.4-Load-Images-With-Per-Sample-Status]
- [Source: docs/history/epics.md#Functional-Requirements]
- [Source: docs/history/architecture.md#Data-Architecture]
- [Source: docs/history/architecture.md#Project-Structure-&-Boundaries]
- [Source: docs/history/architecture.md#Integration-Points]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md#Constraints]
- [Source: docs/history/stories/1-3-parse-test-rows-into-typed-sample-records.md#Previous-Story-Intelligence]
- [Source: docs/history/stories/1-3-parse-test-rows-into-typed-sample-records.md#Review-Findings]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-06-18: RED `uv run pytest tests/test_image_io.py` failed during collection because `load_sample_images` was not implemented yet.
- 2026-06-18: GREEN `uv run pytest tests/test_image_io.py` passed with 5 tests after adding image-load schemas and byte-signature IO.
- 2026-06-18: Full regression `uv run pytest` passed with 44 tests.
- 2026-06-18: Quality checks passed: `uv run ruff check src tests` and `uv run ruff format --check src tests`.
- 2026-06-18: CLI checks passed: `uv run multimodal-bias --help` and `uv run multimodal-bias --version`.
- 2026-06-18: `uv run multimodal-bias validate-data --data-root data/raw/open` failed clearly as expected because official extracted Multimodal data is not present.
- 2026-06-18: Removed generated `src/multimodal_bias/__pycache__`; final cache guard found no `__pycache__`, `.pytest_cache`, or `.ruff_cache` under `src` or `tests`.
- 2026-06-18: Addressed code review patch findings by handling path resolution failures, constraining `image_format`, and adding GIF/WebP plus `read_bytes()` OSError coverage.
- 2026-06-18: Patch validation passed: `uv sync`, `uv run pytest` (47 passed), `uv run ruff check src tests`, `uv run ruff format --check src tests`, CLI `--help`, CLI `--version`, and expected placeholder `validate-data` failure.
- 2026-06-18: Removed generated `src/multimodal_bias/__pycache__` after CLI validation; final source/test cache guard found no cache artifacts.

### Implementation Plan

- Add immutable shared image-load result schemas in `schemas.py`.
- Implement stdlib-only byte loading and signature detection in `image_io.py`.
- Cover success, order preservation, missing path, unreadable path, corrupt bytes, empty file, and aggregate counts with CPU-safe tests.
- Keep `data_loader.py` and `validate-data` behavior unchanged.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented Story 1.4 image IO boundary with per-sample status results and aggregate success/failure counts.
- Added JPEG, PNG, GIF, and WebP byte-signature detection without adding image/model dependencies.
- Added CPU-safe image IO tests using `tmp_path` and direct `SampleRecord` construction.
- Confirmed no image loading was added to `validate-data`; placeholder official data still fails with the existing layout error.
- Resolved all Story 1.4 code review patch findings and moved status to done.

### File List

- `docs/history/stories/1-4-load-images-with-per-sample-status.md`
- `src/multimodal_bias/image_io.py`
- `src/multimodal_bias/schemas.py`
- `tests/test_image_io.py`

## Change Log

- 2026-06-18: Created Story 1.4 context file and moved status to ready-for-dev.
- 2026-06-18: Implemented Story 1.4 image-load status boundary, added tests, validated, and moved status to review.
- 2026-06-18: Addressed Story 1.4 code review patch findings, validated, and moved status to done.
