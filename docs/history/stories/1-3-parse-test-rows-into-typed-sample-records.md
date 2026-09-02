---
baseline_commit: NO_VCS
---

# Story 1.3: Parse Test Rows Into Typed Sample Records

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a competition developer,
I want each `test.csv` row parsed into a typed sample object,
so that prompt building and inference never depend on raw ad hoc dictionaries.

## Acceptance Criteria

1. Given a valid official `data/raw/open/` layout, when test rows are loaded, then the data loader returns ordered typed `SampleRecord` objects.
2. Each `SampleRecord` contains `sample_id`, resolved `image_path`, `context`, `question`, and `answers` parsed as exactly three answer strings.
3. Parsed records preserve the original `test.csv` row order.
4. Malformed `answers` JSON, non-list answers JSON, invalid answer count, non-string answers, or empty answer text raise `DataLayoutError` with `test/test.csv` row context.
5. The parser reuses Story 1.2 layout validation and safe image-path checks instead of reimplementing a parallel validator.
6. CPU-safe tests cover valid parsing, ordering, malformed JSON, invalid answer count/type/content, and inherited layout failure behavior without official Multimodal data, model weights, GPU, or network access.

## Tasks / Subtasks

- [x] Define the typed sample boundary (AC: 1, 2)
  - [x] Add `SampleRecord` to `src/multimodal_bias/schemas.py` as a frozen stdlib dataclass.
  - [x] Use explicit fields: `sample_id: str`, `image_path: Path`, `context: str`, `question: str`, `answers: tuple[str, str, str]`, and `row_number: int`.
  - [x] Keep `answers` immutable as a 3-item tuple, not a raw JSON string, list, dict, or anonymous structure.
  - [x] Do not add Pydantic or any new runtime dependency for this story.

- [x] Implement test-row parsing in `data_loader.py` (AC: 1, 2, 3, 4, 5)
  - [x] Add `load_test_records(data_root: Path | str = DEFAULT_DATA_ROOT) -> tuple[SampleRecord, ...]`.
  - [x] Call `validate_data_layout(data_root)` before parsing records so required files, columns, UTF-8, row emptiness, duplicate IDs, sample-submission alignment, and image path safety remain centralized.
  - [x] Read `test/test.csv` with `encoding="utf-8"` and `newline=""` using stdlib `csv.DictReader`.
  - [x] Preserve row order by appending records in CSV iteration order and returning a tuple.
  - [x] Resolve each `image_path` under the configured `open/` root after validation; do not normalize or write official data.
  - [x] Parse `answers` with stdlib `json.loads` in a dedicated helper such as `_parse_answers(...)`.
  - [x] Reject malformed JSON, JSON values that are not a list, lists with length other than 3, non-string entries, and entries that become empty after trimming.
  - [x] Include deterministic error text with `test/test.csv`, row number, and the failing condition.
  - [x] Raise the existing `DataLayoutError`; reserve `ParseError` for later generated-model-output parsing stories.

- [x] Add CPU-safe tests (AC: 1, 2, 3, 4, 5, 6)
  - [x] Extend `tests/test_data_loader.py` using the existing `build_valid_open_layout(tmp_path)` helper.
  - [x] Test a valid layout returns one `SampleRecord` with resolved image path, row number `2`, and `answers == ("first person", "second person", "uncertain")`.
  - [x] Test multiple test rows preserve `sample_id` order and produce matching `sample_submission.csv` rows.
  - [x] Parametrize invalid `answers` cases: malformed JSON, object JSON, two answers, four answers, non-string answer, and empty/whitespace-only answer.
  - [x] Test `load_test_records` surfaces inherited layout validation failures, such as missing test image or wrong split image path.
  - [x] Keep all fixtures temporary; do not add Multimodal data, image fixtures, generated CSV fixtures, or non-`.gitkeep` files under scaffold artifact directories.

- [x] Preserve CLI and validation behavior (AC: 5, 6)
  - [x] Keep `validate-data` as CLI orchestration only; do not put row parsing logic in `cli.py`.
  - [x] Ensure existing CLI help/version and `validate-data` tests still pass.
  - [x] Do not add inference, prompt construction, image loading/decoding, model loading, submission writing, or validation metrics in this story.

- [x] Run validation (AC: 6)
  - [x] Run `uv sync`.
  - [x] Run `uv run pytest`.
  - [x] Run `uv run ruff check src tests`.
  - [x] Run `uv run ruff format --check src tests`.
  - [x] Run `uv run multimodal-bias --help`.
  - [x] Run `uv run multimodal-bias --version`.
  - [x] Run `uv run multimodal-bias validate-data --data-root data/raw/open` and confirm it still fails clearly until official extracted data is present.

### Review Findings

- [x] [Review][Patch] Guard missing `image_path` cell values before path validation [src/multimodal_bias/data_loader.py:298]
- [x] [Review][Patch] Guard missing `label` cell values before label validation [src/multimodal_bias/data_loader.py:339]
- [x] [Review][Patch] Reject CSV rows with extra unnamed fields [src/multimodal_bias/data_loader.py:184]

## Dev Notes

### Current Workspace State

- Story 1.1 and Story 1.2 are complete and marked `done`.
- There is no git repository and no `_bmad/bmm/config.yaml` or `sprint-status.yaml` in this workspace.
- `pyproject.toml` targets Python `>=3.10,<3.11`; `.python-version` is `3.10`.
- The project uses a packaged `src/multimodal_bias/` layout, Typer CLI, pytest, Ruff, and `uv`.
- `src/multimodal_bias/schemas.py` currently contains `DataLayoutReport` only.
- `src/multimodal_bias/data_loader.py` owns `validate_data_layout`, required Multimodal layout constants, CSV validation, safe split image-path checks, duplicate header/ID checks, and sample-submission alignment.
- `src/multimodal_bias/exceptions.py` already defines `DataLayoutError` and `ParseError`; use `DataLayoutError` for malformed official CSV data in this story.
- `data/raw/open/` currently contains only `.gitkeep`; official `open.zip` is not present.

### Story 1.3 Scope

Implement typed test-row parsing only.

Do not implement:

- train-row record parsing
- image loading, decoding, resizing, or PIL integration
- prompt construction
- model adapter or inference
- generated model output parsing
- verifier, arbitration, submission generation, or validation metrics
- any prompt rule, training example, validation example, or answer mapping derived from `test.csv`

### Data Contract

Official `test.csv` columns are:

```text
sample_id,image_path,context,question,answers
```

`answers` is a JSON-format string containing exactly three choices. Story 1.3 must turn that JSON string into `tuple[str, str, str]` on `SampleRecord`.

Recommended `SampleRecord` shape:

```python
@dataclass(frozen=True)
class SampleRecord:
    sample_id: str
    image_path: Path
    context: str
    question: str
    answers: tuple[str, str, str]
    row_number: int
```

Use the resolved absolute `image_path` under the configured `open/` root. Story 1.2 already enforces that `test.csv` image paths are relative, stay under the root, are under `test/images`, and exist.

### Implementation Guidance

- Prefer adding a small public loader function, `load_test_records`, to `data_loader.py`; this keeps future prompt and inference stories away from raw dictionaries.
- Reuse `validate_data_layout` at the start of `load_test_records`. Do not fork Story 1.2 validation rules into a second implementation.
- Keep parsing deterministic and strict. The parser should not silently coerce numbers, nulls, nested objects, or missing answers into strings.
- It is acceptable to strip leading/trailing whitespace from answer strings before storing them, as long as empty-after-strip values are rejected.
- If multiple answer rows are malformed, collecting all row errors into one `DataLayoutError` is consistent with Story 1.2. Failing fast is acceptable only if tests lock deterministic row context.
- Keep helpers private unless a later story needs them. A private `_parse_answers` helper is enough.
- Do not add dependencies such as `pandas`, `Pillow`, `pydantic`, `torch`, or model libraries.

### Previous Story Intelligence

- Story 1.2 established `DataLayoutError` as the failure boundary for malformed official input data.
- Story 1.2 validates `sample_submission.csv` row count and ordered `sample_id` values against `test/test.csv`; multi-row tests in this story must keep those files aligned.
- Story 1.2 review patches added split-specific image path checks, duplicate CSV header checks, duplicate `sample_id` checks, and header-only CSV rejection. `load_test_records` must not bypass those safeguards.
- Story 1.1 scaffold guards require artifact placeholder directories to contain only `.gitkeep`; use `tmp_path` for all test layouts.
- Direct CLI execution can create `__pycache__` under `src/`; remove generated cache artifacts before final pytest if needed so scaffold guard tests pass.

### Architecture and Compliance Guardrails

- Use `src/multimodal_bias/` as the only importable package root.
- Add shared typed data structures to `schemas.py`.
- Keep `cli.py` as orchestration glue only.
- Keep raw data read-only under `data/raw/`; generated artifacts belong under `data/processed/`, `runs/`, or `submissions/`.
- No database, web UI, network API, remote model API, or interactive labeling product is allowed.
- `test.csv` and images are inference-only inputs. This story may parse fields needed for inference, but must not derive prompt rules, training data, validation examples, answer mappings, or heuristics from evaluation-set wording, choice patterns, images, or inferred labels.
- All CSV/code/comment handling must remain UTF-8.
- The typed `SampleRecord` boundary is a prerequisite for later Reasoner, prompt, image-loader, and submission pipeline stories.

### Testing Requirements

Minimum tests:

- `load_test_records` returns a tuple of `SampleRecord` instances for a valid temp layout
- parsed `answers` are exactly a 3-item string tuple
- resolved `image_path` points to the temp `test/images` file
- record order follows `test.csv`
- malformed `answers` JSON raises `DataLayoutError` with `test/test.csv` and row number
- invalid answer count raises `DataLayoutError`
- non-string or empty answer raises `DataLayoutError`
- inherited layout validation failures still raise `DataLayoutError`
- existing Story 1.1 and Story 1.2 tests remain green

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

- [Source: docs/history/epics.md#Story-1.3-Parse-Test-Rows-Into-Typed-Sample-Records]
- [Source: docs/history/epics.md#Functional-Requirements]
- [Source: docs/history/architecture.md#Implementation-Patterns-&-Consistency-Rules]
- [Source: docs/history/architecture.md#Project-Structure-&-Boundaries]
- [Source: docs/history/architecture.md#Integration-Points]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md#Constraints]
- [Source: Multimodal_236722_평가_요구사항_정리.md#3-데이터-구조와-제출-형식]
- [Source: Multimodal_236722_평가_요구사항_정리.md#11-구현-방향-체크리스트]
- [Source: docs/history/stories/1-2-validate-official-multimodal-data-layout.md#Previous-Story-Intelligence]
- [Source: docs/history/stories/1-2-validate-official-multimodal-data-layout.md#Review-Findings]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Red phase: `uv run pytest tests/test_data_loader.py` failed on missing `load_test_records`, as expected.
- Green phase: `uv run pytest tests/test_data_loader.py` passed with 24 tests.
- Regression validation: `uv run pytest` passed with 36 tests.
- Quality validation: `uv run ruff check src tests` passed.
- Format validation: `uv run ruff format --check src tests` passed after formatting `src/multimodal_bias/data_loader.py`.
- Runtime validation: `uv sync`, `uv run multimodal-bias --help`, and `uv run multimodal-bias --version` passed.
- Expected data validation failure: `uv run multimodal-bias validate-data --data-root data/raw/open` failed clearly because only `.gitkeep` is present and official `open.zip` has not been extracted.
- Cache guard validation: generated `src/multimodal_bias/__pycache__` from direct CLI execution was removed, then `uv run pytest` passed and `src/` plus `tests/` contained no cache artifacts.
- Code review validation: Blind Hunter, Edge Case Hunter, and Acceptance Auditor completed; Acceptance Auditor found no acceptance issues.
- Review patch red phase: `uv run pytest tests/test_data_loader.py` failed on missing `image_path`/`label` cell guards and extra unnamed CSV field acceptance.
- Review patch validation: `uv run pytest tests/test_data_loader.py` passed with 27 tests.
- Review patch validation: `uv sync`, `uv run pytest`, `uv run ruff check src tests`, and `uv run ruff format --check src tests` passed.
- Review patch runtime validation: `uv run multimodal-bias --help`, `uv run multimodal-bias --version`, and the expected placeholder failure for `uv run multimodal-bias validate-data --data-root data/raw/open` passed.
- Review patch cache guard: generated `src/multimodal_bias/__pycache__` from direct CLI execution was removed, then `uv run pytest` passed with 39 tests and `src/` plus `tests/` contained no cache artifacts.

### Implementation Plan

- Added the `SampleRecord` dataclass in `schemas.py` as the typed test-row boundary.
- Added `load_test_records` in `data_loader.py` to reuse `validate_data_layout`, preserve row order, resolve test image paths, and parse `answers` into a 3-item tuple.
- Added strict `_parse_answers` handling for malformed JSON, non-list values, invalid answer counts, non-string entries, and empty strings.
- Added CPU-safe tests for valid typed parsing, ordering, answer parsing failures, and inherited layout validation failures.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented typed `SampleRecord` loading for official `test.csv` rows.
- Reused Story 1.2 layout validation before parsing records, preserving centralized data safety checks.
- Kept `validate-data` as CLI orchestration only; no parsing logic was added to `cli.py`.
- Added no new dependencies and no official Multimodal data or persistent test fixtures.
- Review patches now handle missing `image_path` and `label` cells as `DataLayoutError` validation failures instead of leaking `AttributeError`.
- Review patches now reject rows with extra unnamed CSV fields produced by over-wide rows.

### File List

- `docs/history/stories/1-3-parse-test-rows-into-typed-sample-records.md`
- `src/multimodal_bias/data_loader.py`
- `src/multimodal_bias/schemas.py`
- `tests/test_data_loader.py`

## Change Log

- 2026-06-18: Created Story 1.3 context file and moved status to ready-for-dev.
- 2026-06-18: Implemented Story 1.3 typed test-row parsing and moved status to review.
- 2026-06-18: Applied all Story 1.3 code review patch findings, reran validation, and moved status to done.
