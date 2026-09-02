---
baseline_commit: NO_VCS
---

# Story 1.1: Set Up Initial Project From Starter Template

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a competition developer,
I want a reproducible Python package scaffold,
so that all later inference and validation work runs through a consistent project structure.

## Acceptance Criteria

1. Given an empty or planning-only workspace, when the project scaffold is initialized, then `pyproject.toml`, `.python-version`, `uv.lock`, `src/multimodal_bias/`, `configs/`, `data/`, `models/`, `runs/`, `submissions/`, and `tests/` exist.
2. The CLI package name is `multimodal-bias`.
3. The scaffold follows `uv init --package --python 3.10 --name multimodal-bias --vcs none .`.
4. CPU-safe tooling for `pytest` and `ruff` is configured.

## Tasks / Subtasks

- [x] Initialize the packaged Python scaffold with `uv` (AC: 1, 2, 3)
  - [x] Confirm the workspace is still planning-only or safely compatible with `uv init`.
  - [x] Run `uv init --package --python 3.10 --name multimodal-bias --vcs none .` from the repository root.
  - [x] Preserve existing planning artifacts; do not move or delete `docs/history/` or Multimodal requirement documents.
  - [x] Verify generated `pyproject.toml`, `.python-version`, `uv.lock`, and `src/multimodal_bias/__init__.py`.

- [x] Configure CPU-safe developer tooling (AC: 4)
  - [x] Add `pytest` as a development dependency.
  - [x] Add `ruff` as a development dependency.
  - [x] Configure Ruff in `pyproject.toml` with Python 3.10 target, `src` and `tests` scope, and standard lint/format settings.
  - [x] Configure pytest in `pyproject.toml` to discover tests under `tests/`.

- [x] Create architecture-required top-level artifact directories (AC: 1)
  - [x] Create `configs/`, `configs/models/`, and `configs/prompts/`.
  - [x] Create `data/raw/open/` and `data/processed/`.
  - [x] Create `models/snapshots/`, `runs/`, `submissions/`, and `tests/fixtures/`.
  - [x] Add lightweight placeholder files only where needed to keep empty directories visible; do not place generated data, raw competition data, model weights, run outputs, or submissions inside importable source code.

- [x] Establish initial source package boundaries (AC: 1, 2)
  - [x] Ensure `src/multimodal_bias/` is the only importable package root.
  - [x] Add empty or minimal architecture modules required by later stories: `cli.py`, `config.py`, `schemas.py`, `exceptions.py`, `data_loader.py`, `image_io.py`, `parsing.py`, `reasoner.py`, `verifier.py`, `arbitration.py`, `validation.py`, `compliance.py`, `submission.py`, `run_logging.py`, and `run_comparison.py`.
  - [x] Add package directories `src/multimodal_bias/prompting/` and `src/multimodal_bias/models/` with `__init__.py`.
  - [x] Add minimal files `prompting/templates.py`, `prompting/guards.py`, `models/adapter.py`, `models/hf_vlm.py`, and `models/dummy.py`.
  - [x] Keep module implementations minimal; this story must scaffold boundaries, not implement data loading, inference, parsing, verification, validation, or submission behavior.

- [x] Add minimal CLI entrypoint and smoke tests (AC: 2, 4)
  - [x] Configure `[project.scripts]` so `multimodal-bias` resolves to the package CLI.
  - [x] Implement a minimal Typer app in `src/multimodal_bias/cli.py` with a non-destructive version/help path.
  - [x] Add a CPU-safe test proving the package imports.
  - [x] Add a CPU-safe test proving the CLI help command exits successfully.

- [x] Run scaffold validation (AC: 1, 2, 3, 4)
  - [x] Run `uv sync`.
  - [x] Run `uv run pytest`.
  - [x] Run `uv run ruff check src tests`.
  - [x] Run `uv run ruff format --check src tests`.
  - [x] Run `uv run multimodal-bias --help`.
  - [x] Confirm no tests require GPU, official Multimodal data, model weights, or network model APIs.

### Review Findings

- [x] [Review][Patch] Enforce Python 3.10 runtime range [pyproject.toml:6]
- [x] [Review][Patch] Cover installed console script, CLI help shape, and version behavior [tests/test_cli.py:6]
- [x] [Review][Patch] Add generated cache/artifact ignore rules and a test rejecting cache artifacts under source/test code [tests/test_scaffold.py:43]
- [x] [Review][Patch] Guard scaffold artifact directories against non-placeholder files during Story 1.1 [tests/test_scaffold.py:48]

## Dev Notes

### Current Workspace State

- The workspace currently contains planning artifacts only: `docs/history/`, `Multimodal_236722_평가_요구사항_정리.md`, and no implementation package.
- No `_bmad/bmm/config.yaml`, `sprint-status.yaml`, or existing source tree is present. This story file is stored under `docs/history/stories/` and can be passed directly to `bmad-dev-story`.
- There are no existing implementation files to update. All implementation files in this story are new.

### Scope Boundary

This story is a scaffold story. It must create the project structure, package entrypoint, empty module boundaries, and CPU-safe tooling only.

Do not implement:

- Multimodal `open.zip` validation
- CSV parsing
- image loading
- model loading
- Reasoner or Verifier behavior
- arbitration logic
- validation metrics
- compliance manifest generation
- submission generation

Those belong to later stories.

### Architecture Requirements

- Use Python 3.10 for competition code.
- Use `uv init --package --python 3.10 --name multimodal-bias --vcs none .` as the starter command.
- Use `pyproject.toml`, `.python-version`, `uv.lock`, `uv sync`, and `uv run` for reproducible execution.
- Use `src/multimodal_bias/` as the only importable package root.
- Use Typer for repeatable CLI command entrypoints.
- Use pytest for CPU-safe tests and Ruff for lint/format.
- Do not introduce a database, web UI, network API, or interactive labeling product.
- Generated artifacts, model weights, raw data, runs, and submissions must stay outside importable source code.

Required top-level artifact directories:

```text
configs/
data/raw/open/
data/processed/
models/snapshots/
runs/
submissions/
tests/
```

Required package modules to scaffold:

```text
src/multimodal_bias/
├── __init__.py
├── cli.py
├── config.py
├── schemas.py
├── exceptions.py
├── data_loader.py
├── image_io.py
├── parsing.py
├── reasoner.py
├── verifier.py
├── arbitration.py
├── validation.py
├── compliance.py
├── submission.py
├── run_logging.py
├── run_comparison.py
├── prompting/
│   ├── __init__.py
│   ├── templates.py
│   └── guards.py
└── models/
    ├── __init__.py
    ├── adapter.py
    ├── hf_vlm.py
    └── dummy.py
```

`run_comparison.py` is required even though it is a later feature owner; architecture validation specifically recommends adding it during scaffold so `compare-runs` logic does not leak into `validation.py`, `run_logging.py`, or `cli.py`.

### CLI Guidance

Use a minimal Typer app only. The CLI may expose a root help/version path, but should not expose fake completed business commands. If command placeholders are added for discoverability, they must clearly raise `NotImplementedError` or exit with a non-zero code and must not pretend to validate data, run models, or create submissions.

Preferred minimal path for this story:

- `[project.scripts] multimodal-bias = "multimodal_bias.cli:app"`
- `uv run multimodal-bias --help` succeeds.
- No inference/data/submission commands are implemented yet.

### Testing Requirements

Tests must be CPU-safe and must not require:

- GPU/CUDA
- official Multimodal data
- model weights
- Hugging Face network access
- remote model APIs

Minimum tests:

- package import smoke test
- CLI help smoke test using Typer's testing utilities
- optional structure test confirming required module imports if implementations stay minimal

Recommended commands:

```bash
uv sync
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
uv run multimodal-bias --help
```

### Dependency Guidance

Expected dependencies for this story:

- Runtime dependency: `typer`
- Development dependencies: `pytest`, `ruff`

Do not add PyTorch, Transformers, Accelerate, Pillow, Pydantic, YAML libraries, or VLM-specific dependencies in this story unless the generated starter or existing environment already requires them. Model/runtime dependencies belong to later stories after model and config decisions are explicit.

### Latest Technical Notes

- Official uv docs state that `uv init --package` creates a packaged application using a `src` layout and command definition suitable for `uv run`.
- Official Ruff docs support configuration through `pyproject.toml`, `ruff.toml`, or `.ruff.toml`; use `pyproject.toml` here to keep project configuration centralized.
- Official Typer docs support CLI testing through Typer's test utilities; use this for the help smoke test.
- Official pytest docs support configuration in `pyproject.toml`; use this for `testpaths = ["tests"]`.

### Compliance Guardrails

- No remote model API integration is allowed.
- No test-derived prompt/data engineering is allowed.
- Keep code comments and generated text UTF-8.
- Raw official data belongs under `data/raw/open/` and should be treated as read-only when later stories add ingestion.
- The daily Multimodal submission limit and Public LB overfit policy do not affect this scaffold story directly, but the structure must support auditable, reproducible runs later.

### Implementation Order Guidance

Follow the task order exactly:

1. Initialize `uv` package.
2. Add tooling dependencies and config.
3. Create artifact directories.
4. Add source module boundaries.
5. Add minimal CLI and tests.
6. Run validation commands.

Do not mark any task complete until its validation commands pass.

### References

- [Source: docs/history/epics.md#Story-1.1-Set-Up-Initial-Project-From-Starter-Template]
- [Source: docs/history/architecture.md#Selected-Starter-uv-Packaged-Python-CLI-Application]
- [Source: docs/history/architecture.md#Project-Structure-Boundaries]
- [Source: docs/history/architecture.md#Implementation-Handoff]
- [Source: docs/history/implementation-readiness-report-2026-06-18.md#Recommended-Next-Steps]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md#Constraints]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/compliance-references.md#Competition-Rules-That-Bend-Design]
- [Official uv docs: Creating projects](https://docs.astral.sh/uv/concepts/projects/init/)
- [Official Ruff docs: Configuration](https://docs.astral.sh/ruff/configuration/)
- [Official Typer docs: Testing](https://typer.tiangolo.com/tutorial/testing/)
- [Official pytest docs: Configuration](https://docs.pytest.org/en/stable/reference/customize.html)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Red checks: `test -f pyproject.toml` and `test -d src/multimodal_bias` failed before scaffold, as expected.
- Red test: `uv run pytest` failed on missing `multimodal_bias.cli` before source modules were added.
- Green validation: `uv run pytest` passed with 10 tests after review patches.
- Quality validation: `uv run ruff check src tests` passed.
- Format validation: `uv run ruff format --check src tests` passed.
- Runtime validation: `uv sync`, `uv run multimodal-bias --help`, and `uv run multimodal-bias --version` passed.

### Implementation Plan

- Initialized the project with the exact Story 1.1 `uv init` command.
- Added only the Story-approved dependencies: Typer at runtime, pytest and Ruff for development.
- Kept source implementation minimal: package metadata, a Typer app, architecture module boundaries, and explicit project exceptions only.
- Added CPU-only scaffold tests for importability, required directories, and CLI help behavior.
- Preserved planning documents and avoided any Multimodal data loading, model inference, parsing, verification, validation, compliance manifest, or submission behavior.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented the `uv` packaged Python scaffold with Python 3.10 metadata, lockfile, package entrypoint, and central pytest/Ruff configuration.
- Added architecture-required artifact folders and placeholder files while keeping generated competition artifacts out of importable source code.
- Added minimal package boundary modules, including the architecture-recommended `run_comparison.py` owner module.
- Added a minimal Typer CLI and CPU-safe scaffold tests.
- Verified Story 1.1 acceptance criteria with `uv sync`, `uv run pytest`, `uv run ruff check src tests`, `uv run ruff format --check src tests`, and `uv run multimodal-bias --help`.

### File List

- `.python-version`
- `.gitignore`
- `conftest.py`
- `README.md`
- `configs/models/.gitkeep`
- `configs/prompts/.gitkeep`
- `data/processed/.gitkeep`
- `data/raw/open/.gitkeep`
- `models/snapshots/.gitkeep`
- `docs/history/stories/1-1-set-up-initial-project-from-starter-template.md`
- `pyproject.toml`
- `runs/.gitkeep`
- `src/multimodal_bias/__init__.py`
- `src/multimodal_bias/arbitration.py`
- `src/multimodal_bias/cli.py`
- `src/multimodal_bias/compliance.py`
- `src/multimodal_bias/config.py`
- `src/multimodal_bias/data_loader.py`
- `src/multimodal_bias/exceptions.py`
- `src/multimodal_bias/image_io.py`
- `src/multimodal_bias/models/__init__.py`
- `src/multimodal_bias/models/adapter.py`
- `src/multimodal_bias/models/dummy.py`
- `src/multimodal_bias/models/hf_vlm.py`
- `src/multimodal_bias/parsing.py`
- `src/multimodal_bias/prompting/__init__.py`
- `src/multimodal_bias/prompting/guards.py`
- `src/multimodal_bias/prompting/templates.py`
- `src/multimodal_bias/reasoner.py`
- `src/multimodal_bias/run_comparison.py`
- `src/multimodal_bias/run_logging.py`
- `src/multimodal_bias/schemas.py`
- `src/multimodal_bias/submission.py`
- `src/multimodal_bias/validation.py`
- `src/multimodal_bias/verifier.py`
- `submissions/.gitkeep`
- `tests/fixtures/.gitkeep`
- `tests/test_cli.py`
- `tests/test_scaffold.py`
- `uv.lock`

## Change Log

- 2026-06-18: Created Story 1.1 context file with architecture, tooling, structure, testing, and compliance guardrails.
- 2026-06-18: Implemented Story 1.1 scaffold and moved status to review.
- 2026-06-18: Applied code review patches and moved status to done.
