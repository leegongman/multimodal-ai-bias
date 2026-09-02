---
baseline_commit: NO_VCS
---

# Story 2.1: Configure Runtime CLI and Run Artifact Contract

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a competition developer,
I want a CLI-driven runtime configuration and run directory contract,
so that every inference attempt creates reproducible and auditable artifacts.

## Acceptance Criteria

1. Given a runtime config file, when the CLI starts a run, then it creates a unique `runs/{run_id}/` directory without overwriting an existing run.
2. Given a started run, then `config.resolved.yaml` is written under the run directory with the resolved runtime config, run id, run directory, and source config path.
3. Given a started run, then `environment.json` is written under the run directory with reproducibility metadata including timestamp, Python version, platform, executable, package version, and command context.
4. Given repeated run starts in the same second with the same run name, then run ids remain timestamped, deterministic, filesystem-safe, and unique by adding a stable numeric suffix.
5. Given malformed or unsupported config contents, then the CLI fails clearly without a traceback and without creating a partial run directory.
6. Given existing `validate-data`, help, and version behavior, then Story 2.1 preserves those CLI behaviors while registering new CLI command wiring through `src/multimodal_bias/cli.py`.
7. CPU-safe tests cover config loading, config validation failures, run id uniqueness, artifact file contents, CLI success/failure paths, and existing CLI regression behavior without official Multimodal data, model weights, GPU, or network access.

## Tasks / Subtasks

- [x] Define runtime config and run manifest schemas (AC: 1, 2, 3, 4)
  - [x] Add `CompetitionConfig` as a frozen dataclass in `src/multimodal_bias/schemas.py`.
  - [x] Include at minimum `data_root: Path`, `runs_root: Path`, and `run_name: str` in `CompetitionConfig`.
  - [x] Add `RunManifest` as a frozen dataclass in `schemas.py` with `run_id`, `run_dir`, `config_path`, `resolved_config_path`, `environment_path`, and `created_at_utc`.
  - [x] Keep schemas plain dataclasses for this story. Do not introduce Pydantic yet.

- [x] Implement config loading in `config.py` (AC: 2, 5)
  - [x] Add a default config path constant for `configs/base.yaml`.
  - [x] Add `load_config(config_path: Path | str = DEFAULT_CONFIG_PATH) -> CompetitionConfig`.
  - [x] Add `ConfigurationError` to `exceptions.py` for config parse, validation, and unsupported-key failures.
  - [x] Use `PyYAML` as the YAML parser/writer dependency for this story; add it through `uv add pyyaml` during implementation rather than hand-editing dependency files.
  - [x] Use only `yaml.safe_load` and `yaml.safe_dump`; do not use unsafe loaders.
  - [x] Require the config file to be a mapping and reject unknown keys to catch typos.
  - [x] Resolve relative paths against the project working directory, not against `src/`.
  - [x] Reject an empty or non-filesystem-safe `run_name`.
  - [x] Do not validate official Multimodal data layout here; `validate-data` remains the owner of layout checks.

- [x] Add default runtime config file (AC: 2, 6)
  - [x] Add `configs/base.yaml`.
  - [x] Include only Story 2.1 fields: `data_root`, `runs_root`, and `run_name`.
  - [x] Do not add model snapshot, prompt, verifier, validation, or submission settings in this story.
  - [x] Keep existing scaffold placeholder directories unchanged; artifact placeholder dirs must still contain only `.gitkeep`.

- [x] Implement run artifact creation in `run_logging.py` (AC: 1, 2, 3, 4, 5)
  - [x] Add `start_run(config: CompetitionConfig, config_path: Path | str, *, now: datetime | None = None, argv: Sequence[str] | None = None) -> RunManifest`.
  - [x] Generate run ids as `YYYYMMDD_HHMMSS_<safe_run_name>`.
  - [x] If the base run id already exists, append `_001`, `_002`, and so on until a new directory can be created.
  - [x] Create the run directory with `exist_ok=False`; never overwrite an existing run.
  - [x] Write `config.resolved.yaml` only after a run directory has been successfully created.
  - [x] Write `environment.json` as UTF-8 JSON with stable indentation and sorted keys.
  - [x] If artifact writing fails after directory creation, raise a clear exception; do not silently create incomplete success states.
  - [x] Keep this story limited to config and run metadata. Do not write `raw_reasoner.jsonl`, `parsed_reasoner.csv`, `verification.jsonl`, `final_predictions.csv`, `submission.csv`, `metrics.json`, or `compliance_manifest.json`.

- [x] Wire CLI command through `cli.py` (AC: 1, 2, 3, 5, 6)
  - [x] Add a `start-run` command that loads `--config` and creates one run directory.
  - [x] Print a concise success line containing `run_id` and `run_dir`.
  - [x] Catch `ConfigurationError` and run-start failures, print actionable errors, and exit with code `1` without a traceback.
  - [x] Keep `validate-data` behavior unchanged.
  - [x] Keep `--help`, no-args help, `--version`, and installed console script behavior unchanged.
  - [x] Do not add `infer`, `smoke-model`, `make-submission`, `verify-risky`, `audit-run`, or `compare-runs` behavior in this story.

- [x] Add CPU-safe tests (AC: 1, 2, 3, 4, 5, 6, 7)
  - [x] Add `tests/test_config.py` for valid config load, missing config file, non-mapping YAML, unknown keys, and invalid `run_name`.
  - [x] Add `tests/test_run_logging.py` for deterministic run id generation, collision suffixes, `config.resolved.yaml`, `environment.json`, and no overwrite behavior.
  - [x] Update `tests/test_cli.py` for `start-run --config <tmp config>` success and malformed config failure.
  - [x] Use `tmp_path` for all run artifact tests; do not write test run directories under the workspace `runs/`.
  - [x] Do not use official Multimodal data, model weights, GPU, Pillow, torch, or network access.
  - [x] Ensure tests do not leave `__pycache__`, `.pytest_cache`, `.ruff_cache`, or generated run artifacts under `src`, `tests`, or top-level artifact placeholder directories.

- [x] Run validation (AC: 6, 7)
  - [x] Run `uv sync`.
  - [x] Run `uv run pytest`.
  - [x] Run `uv run ruff check src tests`.
  - [x] Run `uv run ruff format --check src tests`.
  - [x] Run `uv run multimodal-bias --help`.
  - [x] Run `uv run multimodal-bias --version`.
  - [x] Run `uv run multimodal-bias validate-data --data-root data/raw/open` and confirm it still fails clearly until official extracted data is present.
  - [x] Run `uv run multimodal-bias start-run --config <tmp config>` in a temporary directory or with a config whose `runs_root` is under `tmp_path`; do not leave generated run directories under the workspace `runs/`.
  - [x] Remove generated `src/multimodal_bias/__pycache__` after direct CLI validation if it appears, then rerun final `uv run pytest` and cache/artifact guard checks.

### Review Findings

- [x] [Review][Patch] Reject non-string YAML config keys before unknown-key checks [`src/multimodal_bias/config.py`:34]
- [x] [Review][Patch] Wrap invalid config path resolution errors as `ConfigurationError` [`src/multimodal_bias/config.py`:45]
- [x] [Review][Patch] Re-validate filesystem-safe run names in direct `start_run` inputs [`src/multimodal_bias/run_logging.py`:28]
- [x] [Review][Patch] Retry run directory creation on `FileExistsError` races and skip broken symlink run IDs [`src/multimodal_bias/run_logging.py`:29]
- [x] [Review][Patch] Remove partial run directories when artifact writes fail [`src/multimodal_bias/run_logging.py`:31]
- [x] [Review][Patch] Preserve explicit empty `argv` sequences in `environment.json` [`src/multimodal_bias/run_logging.py`:44]
- [x] [Review][Patch] Add a CLI run-start failure test for valid config with run creation failure [`tests/test_cli.py`:123]

## Dev Notes

### Current Workspace State

- Story 1.1, Story 1.2, Story 1.3, and Story 1.4 are complete and marked `done`.
- There is no git repository, `_bmad/bmm/config.yaml`, or `sprint-status.yaml` in this workspace.
- `pyproject.toml` targets Python `>=3.10,<3.11`; `.python-version` is `3.10`.
- The package currently depends on Typer only at runtime. Story 2.1 is the first story where YAML config parsing is explicit; add `pyyaml` via `uv add pyyaml` rather than implementing an ad hoc YAML parser.
- `configs/models`, `configs/prompts`, `data/raw/open`, `data/processed`, `models/snapshots`, `runs`, `submissions`, and `tests/fixtures` are scaffold placeholder directories guarded by tests to contain only `.gitkeep`.
- `src/multimodal_bias/config.py` and `src/multimodal_bias/run_logging.py` currently contain only module docstrings.
- `src/multimodal_bias/cli.py` currently exposes the root app, `--version`, no-args help, and `validate-data`.
- `src/multimodal_bias/schemas.py` currently contains `DataLayoutReport`, `SampleRecord`, `ImageLoadStatus`, `ImageFormat`, `ImageLoadResult`, and `ImageLoadReport`.

### Story 2.1 Scope

Implement the reusable runtime config and run artifact contract only.

Do not implement:

- model loading or model smoke tests
- prompt templates or prompt construction
- image decoding, resizing, tensors, or model processors
- Reasoner inference, verifier execution, parsing, arbitration, final prediction writing, or submission writing
- validation metrics, compliance manifest generation, audit reports, or run comparison
- any prompt rule, training example, validation example, or answer mapping derived from evaluation-set images or inferred labels

### Runtime Config Contract

Use `configs/base.yaml` as the default config path. For this story, support only:

```yaml
data_root: data/raw/open
runs_root: runs
run_name: default
```

Rules:

- `data_root` and `runs_root` are path-like strings.
- Relative paths resolve from the current project working directory.
- `run_name` must be filesystem-safe after normalization: lowercase letters, digits, and underscores are acceptable. Convert spaces and dashes to underscores or reject them consistently; tests must lock the chosen behavior.
- Unknown keys fail with `ConfigurationError`; this prevents silent drift when later stories add model/prompt fields.
- An empty YAML file, YAML list, scalar, or malformed YAML fails with `ConfigurationError`.
- Config loading must not check that official Multimodal data exists. That remains `validate_data_layout` in `data_loader.py`.

### Run Directory Contract

`start_run` owns run directory creation. Its output directory must be:

```text
{runs_root}/{YYYYMMDD_HHMMSS}_{safe_run_name}/
```

If the directory exists, create:

```text
{runs_root}/{YYYYMMDD_HHMMSS}_{safe_run_name}_001/
{runs_root}/{YYYYMMDD_HHMMSS}_{safe_run_name}_002/
```

Required files for this story:

```text
runs/{run_id}/config.resolved.yaml
runs/{run_id}/environment.json
```

`config.resolved.yaml` should include at minimum:

- `run_id`
- `run_dir`
- `config_path`
- `data_root`
- `runs_root`
- `run_name`

`environment.json` should include at minimum:

- `run_id`
- `created_at_utc`
- `python_version`
- `platform`
- `executable`
- `package_version`
- `cwd`
- `argv`

Keep files UTF-8. Use deterministic formatting so tests can inspect contents without brittle parsing.

### CLI Contract

Add:

```bash
uv run multimodal-bias start-run --config configs/base.yaml
```

Expected success output should include:

```text
Run started: run_id=<id> run_dir=<path>
```

Expected failure behavior:

- config errors exit with code `1`
- error text is actionable and includes the config path or offending key/value when applicable
- no Python traceback is shown
- `validate-data`, root `--help`, no-args help, and `--version` behavior remains unchanged

`start-run` is a run-contract command for this story. Later `infer`, `verify-risky`, `make-submission`, and audit commands should reuse `config.py` and `run_logging.py`; do not duplicate run id or environment-record logic in future command handlers.

### Previous Story Intelligence

- Story 1.1 established the `src/multimodal_bias/` package root, Typer CLI, strict Python 3.10 runtime range, scaffold placeholder guards, `.gitignore` rules for generated artifacts, and CPU-safe `pytest`/`ruff` validation.
- Story 1.1 review added tests that fail if source/test cache artifacts exist or if artifact placeholder directories contain anything other than `.gitkeep`.
- Story 1.2 established clear CLI failure style for `validate-data`: catch a project exception, print a concise error, exit `1`, and avoid traceback output.
- Story 1.3 established typed data exchange through frozen dataclasses in `schemas.py` and row-context-rich error messages in data-loading boundaries.
- Story 1.4 established per-sample result/report dataclasses, stdlib-first implementation style, and `tmp_path`-only tests for file artifacts.
- Direct CLI execution can create `src/multimodal_bias/__pycache__`; remove it before final scaffold guard tests if needed.

### Architecture and Compliance Guardrails

- Use `src/multimodal_bias/` as the only importable package root.
- Runtime configuration belongs in `configs/base.yaml`; model-specific configuration belongs in `configs/models/`; prompt templates belong in `configs/prompts/`.
- CLI commands are public execution boundaries. Keep business logic in `config.py` and `run_logging.py`; keep `cli.py` as orchestration glue.
- All major modules must exchange typed models from `schemas.py`, not anonymous dictionaries.
- Every run must write under immutable `runs/{run_id}/`.
- `config.resolved.yaml` and `environment.json` are required run artifacts from this story onward.
- Generated artifacts, raw data, model weights, runs, and submissions must stay outside importable source code.
- Keep raw data read-only under `data/raw/`.
- Do not use a database, web UI, network API, remote model API, or interactive labeling product.
- `test.csv` and images are inference-only inputs. This story must not inspect evaluation data to create prompt rules, validation examples, training data, answer mappings, or heuristics.
- Public leaderboard score remains a sanity signal only, not a config or run-selection optimizer.
- All code, config, JSON, YAML, CSV, and generated submission artifacts must remain UTF-8.

### Testing Requirements

Minimum tests:

- valid `configs/base.yaml`-style config loads into `CompetitionConfig`
- relative `data_root` and `runs_root` resolve correctly
- missing config file fails with `ConfigurationError`
- non-mapping or malformed YAML fails with `ConfigurationError`
- unknown config keys fail with `ConfigurationError`
- invalid or empty `run_name` fails
- `start_run` creates a unique timestamped run directory
- repeated starts in the same second add deterministic numeric suffixes
- `config.resolved.yaml` contains resolved config and run id
- `environment.json` contains required reproducibility metadata
- existing run directories are never overwritten
- CLI `start-run --config <tmp config>` succeeds and writes both artifacts
- CLI malformed config failure exits `1` without traceback
- existing `validate-data`, root help/no-args help, `--version`, and installed console-script tests stay green

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

### Latest Technical Notes

- No external web/API integration is required for Story 2.1.
- Use the locally locked Typer CLI pattern already present in `cli.py`.
- Add `pyyaml` only for local YAML file parsing/writing; use safe APIs only and rely on `uv.lock` for reproducibility.
- Do not add PyTorch, Transformers, Accelerate, Pillow, Pydantic, model-runtime, or GPU dependencies in this story.

### References

- [Source: docs/history/epics.md#Story-2.1-Configure-Runtime-CLI-and-Run-Artifact-Contract]
- [Source: docs/history/epics.md#Functional-Requirements]
- [Source: docs/history/architecture.md#Data-Architecture]
- [Source: docs/history/architecture.md#Run-Artifact-Formats]
- [Source: docs/history/architecture.md#API-&-Communication-Patterns]
- [Source: docs/history/architecture.md#Process-Patterns]
- [Source: docs/history/architecture.md#Project-Structure-&-Boundaries]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md#Constraints]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/strategy.md#Runtime-and-Logging-Contract]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/compliance-references.md#Second-Round-Readiness]
- [Source: docs/history/stories/1-4-load-images-with-per-sample-status.md#Previous-Story-Intelligence]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-06-18: RED `uv run pytest tests/test_config.py tests/test_run_logging.py tests/test_cli.py` failed because `load_config` and `yaml` were not available yet.
- 2026-06-18: Added PyYAML with `uv add pyyaml`.
- 2026-06-18: Story-specific tests passed: `uv run pytest tests/test_config.py tests/test_run_logging.py tests/test_cli.py` (17 passed).
- 2026-06-18: Full regression passed: `uv run pytest` (58 passed).
- 2026-06-18: Quality checks passed: `uv run ruff check src tests` and `uv run ruff format --check src tests`.
- 2026-06-18: CLI checks passed: `uv run multimodal-bias --help`, `uv run multimodal-bias --version`, and temporary `start-run --config <tmp config>`.
- 2026-06-18: `uv run multimodal-bias validate-data --data-root data/raw/open` failed clearly as expected because official extracted Multimodal data is not present.
- 2026-06-18: Removed generated `src/multimodal_bias/__pycache__`; final source/test cache and placeholder artifact guards passed.
- 2026-06-18: Code review produced 7 patch findings, 0 deferred findings, and 8 dismissed findings.
- 2026-06-18: Applied all Story 2.1 review patches; targeted tests passed: `uv run pytest tests/test_config.py tests/test_run_logging.py tests/test_cli.py` (28 passed).
- 2026-06-18: Review validation passed: `uv sync`, `uv run pytest` (69 passed), `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run multimodal-bias --help`, and `uv run multimodal-bias --version`.
- 2026-06-18: Removed generated `src/multimodal_bias/__pycache__`; final scaffold guard passed: `uv run pytest tests/test_scaffold.py` (6 passed), and source/test cache guard was clean.

### Implementation Plan

- Add frozen dataclasses for `CompetitionConfig` and `RunManifest`.
- Load strict safe YAML runtime config through `config.py` and reject unsupported shapes or keys.
- Create timestamped run directories through `run_logging.py` with resolved config and environment artifacts.
- Register a minimal `start-run` CLI command while preserving existing CLI behavior.
- Keep generated run artifacts out of workspace placeholder directories during tests and validation.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented Story 2.1 runtime config loading and run artifact contract.
- Added `configs/base.yaml` with Story 2.1 fields only.
- Added `start-run` CLI command that writes `config.resolved.yaml` and `environment.json`.
- Added CPU-safe config, run logging, and CLI tests using `tmp_path`.
- Applied code review hardening for strict config keys, safe run-name reuse, race-safe run directory creation, partial artifact cleanup, and CLI failure coverage.
- Preserved existing `validate-data`, help, version, scaffold, data loader, and image IO behavior.

### File List

- `docs/history/stories/2-1-configure-runtime-cli-and-run-artifact-contract.md`
- `configs/base.yaml`
- `pyproject.toml`
- `uv.lock`
- `src/multimodal_bias/cli.py`
- `src/multimodal_bias/config.py`
- `src/multimodal_bias/exceptions.py`
- `src/multimodal_bias/run_names.py`
- `src/multimodal_bias/run_logging.py`
- `src/multimodal_bias/schemas.py`
- `tests/test_cli.py`
- `tests/test_config.py`
- `tests/test_run_logging.py`

## Change Log

- 2026-06-18: Created Story 2.1 context file and moved status to ready-for-dev.
- 2026-06-18: Implemented Story 2.1 runtime config, run artifact contract, CLI command, tests, and moved status to review.
- 2026-06-18: Applied all code review patch findings and moved status to done.
