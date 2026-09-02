---
baseline_commit: NO_VCS
---

# Story 1.2: Validate Official Multimodal Data Layout

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a competition developer,
I want to validate the extracted `open.zip` layout,
so that malformed or incomplete competition data fails before inference.

## Acceptance Criteria

1. Given a configured `data/raw/open/` path, when `validate-data` runs, then it validates the official Multimodal layout without requiring GPU, model weights, network access, or actual hidden labels.
2. The validator checks that the root contains `train/`, `train/images/`, `train/train.csv`, `test/`, `test/images/`, `test/test.csv`, and `sample_submission.csv`.
3. The validator reads CSV files as UTF-8 and verifies required columns:
   - `train/train.csv`: `sample_id,image_path,context,question,answers,label`
   - `test/test.csv`: `sample_id,image_path,context,question,answers`
   - `sample_submission.csv`: `sample_id,label`
4. Missing files, missing columns, unreadable UTF-8, empty required fields, invalid train labels, absolute image paths, path traversal, or image paths that do not exist under the data root raise `DataLayoutError` with actionable path or row context.
5. `validate-data` is exposed through the existing Typer app as CLI orchestration only; validation logic lives in `data_loader.py` and typed result objects live in `schemas.py`.
6. CPU-safe tests cover valid temp layouts, missing required files, missing columns, malformed image paths, UTF-8 failures, `DataLayoutError`, CLI success, and CLI failure behavior.

## Tasks / Subtasks

- [x] Define the data layout contract in source code (AC: 2, 3, 4, 5)
  - [x] Add exact required directory, file, and CSV-column constants in `src/multimodal_bias/data_loader.py`.
  - [x] Add a minimal typed validation result in `src/multimodal_bias/schemas.py`, such as `DataLayoutReport`, using stdlib dataclasses unless a stronger reason to add Pydantic is documented.
  - [x] Reuse the existing `DataLayoutError` from `src/multimodal_bias/exceptions.py`; do not introduce a second exception type for the same failure boundary.

- [x] Implement official layout validation (AC: 1, 2, 3, 4)
  - [x] Implement `validate_data_layout(data_root: Path | str = Path("data/raw/open")) -> DataLayoutReport`.
  - [x] Validate required directories and files before reading row data.
  - [x] Read `train/train.csv`, `test/test.csv`, and `sample_submission.csv` with `encoding="utf-8"` and `newline=""`.
  - [x] Verify required columns are present; tolerate extra columns but do not let extra columns replace or rename the required contract.
  - [x] Validate required row fields are non-empty for `sample_id`, `image_path`, `context`, `question`, and `answers` where those columns exist.
  - [x] Validate `train/train.csv` labels are restricted to `0`, `1`, and `2`.
  - [x] Validate `sample_submission.csv` labels are either empty or restricted to `0`, `1`, and `2`.
  - [x] Validate `image_path` values are relative paths, do not escape the data root, and point to existing files under the root.
  - [x] Return row counts and root path in the report for CLI summary output.

- [x] Add the CLI command boundary (AC: 1, 5)
  - [x] Add a `validate-data` command to `src/multimodal_bias/cli.py`.
  - [x] Support a `--data-root` option defaulting to `data/raw/open`.
  - [x] On success, print a concise summary containing the validated root and row counts.
  - [x] On `DataLayoutError`, exit non-zero and surface the actionable error text without a traceback.
  - [x] Keep `cli.py` as orchestration glue; do not put CSV or path validation logic in the command function.

- [x] Add CPU-safe tests (AC: 1, 4, 5, 6)
  - [x] Add `tests/test_data_loader.py` using `tmp_path` to create valid and invalid `open/` layouts.
  - [x] Do not commit official Multimodal data, sample images, generated CSVs, or fixture files under `tests/fixtures/`; Story 1.1 currently guards that scaffold artifact directories contain only `.gitkeep`.
  - [x] Test valid layout success and report row counts.
  - [x] Test missing required file or directory raises `DataLayoutError`.
  - [x] Test missing required CSV column raises `DataLayoutError` with the file and column in the message.
  - [x] Test unreadable UTF-8 raises `DataLayoutError`.
  - [x] Test absolute, traversal, and missing `image_path` values raise `DataLayoutError`.
  - [x] Extend CLI tests to cover `validate-data --data-root <tmp_path>` success and failure.
  - [x] Preserve installed console script help/version tests from Story 1.1.

- [x] Run validation (AC: 1, 6)
  - [x] Run `uv sync`.
  - [x] Run `uv run pytest`.
  - [x] Run `uv run ruff check src tests`.
  - [x] Run `uv run ruff format --check src tests`.
  - [x] Run `uv run multimodal-bias --help`.
  - [x] Run `uv run multimodal-bias validate-data --data-root data/raw/open` and confirm it fails clearly until the official extracted data is present.

### Review Findings

- [x] [Review][Patch] Constrain split image paths to their official image directory [src/multimodal_bias/data_loader.py:53]
- [x] [Review][Patch] Validate `sample_submission.csv` rows and `sample_id` values against `test/test.csv` [src/multimodal_bias/data_loader.py:73]
- [x] [Review][Patch] Reject duplicate `sample_id` values and duplicate CSV headers [src/multimodal_bias/data_loader.py:107]
- [x] [Review][Patch] Reject empty required CSV files [src/multimodal_bias/data_loader.py:118]

## Dev Notes

### Current Workspace State

- Story 1.1 is complete and marked `done`.
- `pyproject.toml` uses `requires-python = ">=3.10,<3.11"` and Story 1.1 validation passed with Python 3.10.
- `src/multimodal_bias/data_loader.py` currently contains only a module docstring.
- `src/multimodal_bias/schemas.py` currently contains only a module docstring.
- `src/multimodal_bias/exceptions.py` already defines `DataLayoutError`.
- `src/multimodal_bias/cli.py` already defines the Typer app, `--help`, `--version`, and no-args help behavior.
- `data/raw/open/` currently contains only `.gitkeep`; the official Multimodal `open.zip` is not present in the workspace.
- `.gitignore` ignores generated cache files, `.venv/`, and generated data/artifact contents while preserving `.gitkeep` placeholders.
- There is no git repository and no `_bmad/bmm/config.yaml` or `sprint-status.yaml` in this workspace.

### Official Multimodal Data Layout

The official extracted `open.zip` layout is:

```text
open/
├── train/
│   ├── images/
│   │   └── train_img_0000.jpg
│   └── train.csv
├── test/
│   ├── images/
│   │   ├── test_img_0000.jpg
│   │   ├── ...
│   │   └── test_img_8499.jpg
│   └── test.csv
└── sample_submission.csv
```

`train.csv` columns:

```text
sample_id,image_path,context,question,answers,label
```

`test.csv` columns:

```text
sample_id,image_path,context,question,answers
```

`sample_submission.csv` columns:

```text
sample_id,label
```

The official `answers` field is a JSON-format string containing three choices. Story 1.2 should verify the field exists and is non-empty. Detailed parsing into exactly three answers belongs to Story 1.3 unless needed for an unambiguous layout error.

### Scope Boundary

Implement data layout validation only.

Do not implement:

- `SampleRecord` parsing beyond any minimal report type required for validation
- detailed `answers` JSON parsing into choice objects
- image loading, decoding, resizing, or PIL integration
- model loading or inference
- prompt construction
- validation metrics
- submission generation

Use Python stdlib (`csv`, `dataclasses`, `pathlib`) unless a dependency is already present and materially simplifies the implementation. Do not add `pandas`, `Pillow`, `pydantic`, `PyYAML`, `torch`, or model dependencies in this story.

### Implementation Guidance

- Treat `data/raw/open/` as read-only input. The validator must not create, modify, normalize, or delete files inside official data directories.
- Resolve `image_path` relative to the configured `open/` root. For example, `test/images/test_img_0000.jpg` should resolve under the root.
- Reject absolute paths and any path that escapes the root after resolution.
- Prefer deterministic error messages. Include the CSV path, row number, column name, or offending path where applicable.
- It is acceptable to collect all layout errors and raise one `DataLayoutError` summary, or to fail fast on the first error, as long as tests lock the chosen behavior.
- Keep command business logic out of `cli.py`; the CLI should call `validate_data_layout` and format success or failure for the user.

### Previous Story Intelligence

- Story 1.1 review added stricter runtime pinning, installed console script tests, generated cache ignore rules, and scaffold artifact guards.
- Do not add persistent fixture files under `tests/fixtures/`; use `tmp_path` builders in tests to avoid breaking the Story 1.1 scaffold guard.
- If CLI commands are added, test both Typer `CliRunner` behavior and installed console script behavior where practical.
- Keep tests CPU-only and independent of official Multimodal data, model weights, GPU, and network APIs.

### Architecture and Compliance Guardrails

- Use `src/multimodal_bias/` as the only importable package root.
- Add shared typed data structures to `schemas.py`.
- Keep raw data under `data/raw/`; generated artifacts belong under `data/processed/`, `runs/`, or `submissions/`.
- No database, web UI, network API, or interactive labeling product is allowed.
- `test.csv` and images are inference-only inputs. Do not derive prompt rules, training examples, validation examples, or answer mappings from evaluation-set wording, images, or inferred labels.
- All CSV/code/comment handling must remain UTF-8.
- This story supports Private/Hidden generalization indirectly by failing bad inputs early and preserving a clear, reproducible data boundary before inference.

### Testing Requirements

Minimum tests:

- valid official-like temp layout returns a report with expected row counts
- missing required directory/file raises `DataLayoutError`
- missing CSV column raises `DataLayoutError`
- malformed UTF-8 raises `DataLayoutError`
- invalid image paths raise `DataLayoutError`
- invalid train or sample submission labels raise `DataLayoutError`
- `validate-data` CLI succeeds on a valid temp layout
- `validate-data` CLI exits non-zero with actionable text on an invalid temp layout

Recommended commands:

```bash
uv sync
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
uv run multimodal-bias --help
uv run multimodal-bias validate-data --data-root data/raw/open
```

The final command is expected to fail clearly until official extracted data replaces the current `.gitkeep`-only placeholder.

### References

- [Source: docs/history/epics.md#Story-1.2-Validate-Official-Multimodal-Data-Layout]
- [Source: docs/history/epics.md#Functional-Requirements]
- [Source: docs/history/architecture.md#Data-Architecture]
- [Source: docs/history/architecture.md#API-&-Communication-Patterns]
- [Source: docs/history/architecture.md#Implementation-Patterns-&-Consistency-Rules]
- [Source: docs/history/architecture.md#Project-Structure-&-Boundaries]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md#Capabilities]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md#Constraints]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/compliance-references.md#Competition-Rules-That-Bend-Design]
- [Source: Multimodal_236722_평가_요구사항_정리.md#3-데이터-구조와-제출-형식]
- [Source: docs/history/stories/1-1-set-up-initial-project-from-starter-template.md#Review-Findings]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Red phase: `uv run pytest tests/test_data_loader.py tests/test_cli.py` failed on missing `validate_data_layout`, as expected.
- Green phase: `uv run pytest tests/test_data_loader.py tests/test_cli.py` passed with 15 tests.
- Regression validation: `uv run pytest` passed with 21 tests.
- Quality validation: `uv run ruff check src tests` passed.
- Format validation: `uv run ruff format --check src tests` passed.
- Runtime validation: `uv sync`, `uv run multimodal-bias --help`, and `uv run multimodal-bias --version` passed.
- Expected data validation failure: `uv run multimodal-bias validate-data --data-root data/raw/open` failed clearly because only `.gitkeep` is present and official `open.zip` has not been extracted.
- Code review Step 2 note: Blind Hunter completed; Edge Case Hunter and Acceptance Auditor hit usage limits, so review triage used the completed Blind Hunter findings and documented the incomplete layers.
- Review patch validation: `uv sync` passed.
- Review patch validation: `uv run pytest tests/test_data_loader.py tests/test_cli.py` passed with 21 tests.
- Review patch validation: `uv run pytest` passed with 27 tests.
- Review patch validation: `uv run ruff check src tests` and `uv run ruff format --check src tests` passed.
- Review patch runtime validation: `uv run multimodal-bias --help`, `uv run multimodal-bias --version`, and the expected placeholder failure for `uv run multimodal-bias validate-data --data-root data/raw/open` passed.
- Review patch cache guard: generated `src/multimodal_bias/__pycache__` from direct CLI execution was removed, then `uv run pytest` passed and `src/` plus `tests/` contained no cache artifacts.

### Implementation Plan

- Added a stdlib dataclass report boundary in `schemas.py`.
- Implemented layout validation in `data_loader.py` using `csv`, `pathlib`, and the existing `DataLayoutError`.
- Added `validate-data` to the Typer CLI as orchestration glue only.
- Added CPU-safe temp-layout tests without committing Multimodal data or fixture artifacts.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented official Multimodal `open.zip` layout validation for required directories, files, UTF-8 CSV readability, required columns, required row fields, label constraints, and safe relative image paths.
- Added `validate-data --data-root` CLI command with concise success output and non-traceback `DataLayoutError` failure output.
- Added CPU-safe data loader and CLI tests using `tmp_path`; no official Multimodal data, generated CSV fixture, image fixture, GPU dependency, model weight, or network access is required.
- Verified the placeholder `data/raw/open` failure path is explicit until official extracted data is present.
- Review patches now constrain `train.csv` images to `train/images` and `test.csv` images to `test/images`.
- Review patches now require `sample_submission.csv` row count and ordered `sample_id` values to match `test/test.csv`.
- Review patches now reject duplicate CSV headers, duplicate non-empty `sample_id` values, and header-only required CSV files.

### File List

- `docs/history/stories/1-2-validate-official-multimodal-data-layout.md`
- `src/multimodal_bias/cli.py`
- `src/multimodal_bias/data_loader.py`
- `src/multimodal_bias/schemas.py`
- `tests/test_cli.py`
- `tests/test_data_loader.py`

## Change Log

- 2026-06-18: Created Story 1.2 context file and moved status to ready-for-dev.
- 2026-06-18: Implemented official Multimodal data layout validation and moved status to review.
- 2026-06-18: Applied all Story 1.2 code review patch findings, reran validation, and moved status to done.
