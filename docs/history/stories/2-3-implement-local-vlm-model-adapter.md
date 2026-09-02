---
baseline_commit: NO_VCS
---

# Story 2.3: Implement Local VLM Model Adapter

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a competition developer,
I want model execution hidden behind a local VLM adapter,
so that Reasoner logic does not depend on one model implementation.

## Acceptance Criteria

1. Given a model config that points to a local model snapshot, when `smoke-model` runs, then the command loads the adapter locally or exits with `ModelLoadError` containing actionable context and no traceback.
2. Given a loaded adapter, when one smoke generation is requested, then the adapter returns typed raw generated text plus typed generation metadata without parsing, rewriting, or deciding the final label.
3. Given a local model config, then the load report records model name, adapter type, revision or snapshot hash, snapshot path, local-only load status, and whether remote model access was disabled.
4. Given project compliance rules, then the adapter never calls a remote model API, never downloads model files during smoke execution, and requires local snapshot loading with `local_files_only=True`.
5. Given CPU-only CI, then unit tests validate config loading, adapter contracts, dummy generation, CLI success/failure behavior, and import boundaries without official Multimodal data, model weights, GPU, network, PyTorch, Transformers, Accelerate, or Pillow.

## Tasks / Subtasks

- [x] Define typed model adapter schemas (AC: 1, 2, 3)
  - [x] Add frozen dataclasses and literals to `src/multimodal_bias/schemas.py` for the model boundary.
  - [x] Include a `ModelConfig` or equivalent with `adapter`, `model_name`, `snapshot_path`, `revision`, `snapshot_hash`, `local_files_only`, `trust_remote_code`, `device_map`, `torch_dtype`, `max_new_tokens`, and `do_sample`.
  - [x] Include a typed load metadata/report object with model name, adapter type, snapshot path, revision or snapshot hash, local load status, local-only flag, device/dtype when known, and an optional message.
  - [x] Include a typed generation request/result boundary containing prompt text, optional image bytes/path information, raw generated text, and generation metadata.
  - [x] Do not add parser output, verifier output, final prediction, submission, or compliance manifest schemas in this story.

- [x] Implement model config loading and validation (AC: 1, 3, 4)
  - [x] Add model config loading under `src/multimodal_bias/models/adapter.py` or a narrowly scoped helper in `src/multimodal_bias/models/`.
  - [x] Add `configs/models/example_vlm.yaml` as the documented config shape; remove or account for `configs/models/.gitkeep`.
  - [x] Reject missing config files, non-mapping YAML, non-string keys, unknown keys, missing required fields, invalid adapter values, empty model names, invalid/NUL paths, invalid generation settings, and `local_files_only: false`.
  - [x] Require `snapshot_path` to resolve to a local path for `hf_local` configs; do not allow remote repo IDs as the smoke-load source.
  - [x] Require either `revision` or `snapshot_hash` for `hf_local` configs so the later compliance ledger can identify the exact local artifact without hashing large weight files.
  - [x] Reuse `ConfigurationError` for malformed config files and `ModelLoadError` for load-time failures.

- [x] Add the adapter contract and CPU-safe dummy adapter (AC: 2, 5)
  - [x] Define `VisionLanguageModelAdapter` in `src/multimodal_bias/models/adapter.py` as a small protocol or abstract base with `load()`, `generate(...)`, and load metadata access.
  - [x] Keep the contract model-agnostic: no Reasoner parsing, no final-label selection, no verifier trigger logic, no submission writing, and no Public LB or evaluation-set rules.
  - [x] Implement `src/multimodal_bias/models/dummy.py` for CPU-safe tests and CLI smoke validation using local deterministic text returned as raw model output.
  - [x] Ensure dummy behavior is clearly test-only/integration-only and cannot be mistaken for a production VLM candidate.

- [x] Implement the Hugging Face local VLM adapter boundary (AC: 1, 2, 3, 4)
  - [x] Implement `src/multimodal_bias/models/hf_vlm.py` with lazy imports only inside load/generate paths; importing project modules must not import `torch`, `transformers`, `accelerate`, or image libraries.
  - [x] Use local snapshot paths with `local_files_only=True` when calling Hugging Face `from_pretrained` APIs.
  - [x] Default `trust_remote_code` to `false`; if a config explicitly enables it, surface that value in metadata so a later compliance review can verify the model code was inspected.
  - [x] Resolve the Transformers model class by config, with a VLM-appropriate default such as `AutoModelForImageTextToText`; do not hard-code one model repository or one candidate model.
  - [x] Load the processor and model locally, catch `ImportError`, `OSError`, `ValueError`, and runtime load failures, and re-raise `ModelLoadError` with the config path, snapshot path, adapter type, and dependency/action hint.
  - [x] Return raw decoded generated text and metadata from generation; do not parse the `FINAL_ANSWER_JSON` marker in this story.

- [x] Add the `smoke-model` CLI command (AC: 1, 2, 3, 4)
  - [x] Register `smoke-model` in `src/multimodal_bias/cli.py`.
  - [x] Accept `--model-config`, `--prompt`, and an optional image input suitable for a local smoke run; do not read official Multimodal test data by default.
  - [x] On success, print stable UTF-8 JSON containing load metadata, generation metadata, and raw generated text.
  - [x] On `ConfigurationError`, `ModelLoadError`, or `InferenceError`, print concise actionable text to stderr and exit `1` without traceback.
  - [x] Preserve existing CLI `--help`, `--version`, `validate-data`, and `start-run` behavior.

- [x] Add CPU-safe tests (AC: 1, 2, 3, 4, 5)
  - [x] Add `tests/test_model_adapter.py` covering model config validation, dummy adapter load/generation, load metadata fields, raw text preservation, and malformed config failures.
  - [x] Add CLI tests for `smoke-model` success with a dummy config and failure with an invalid `hf_local` config, asserting no traceback appears.
  - [x] Test that importing `multimodal_bias.models.adapter`, `dummy`, and `hf_vlm` does not require PyTorch, Transformers, Accelerate, Pillow, GPU, model weights, official Multimodal data, or network access.
  - [x] Update `tests/test_scaffold.py` if `configs/models/` now contains `example_vlm.yaml` instead of only `.gitkeep`.
  - [x] Keep tests under `tests/` only; do not create generated artifacts in `src/` or tracked data/model directories.

- [x] Run validation (AC: 5)
  - [x] Run `uv sync`.
  - [x] Run `uv run pytest`.
  - [x] Run `uv run ruff check src tests`.
  - [x] Run `uv run ruff format --check src tests`.
  - [x] Run `uv run multimodal-bias --help`.
  - [x] Run `uv run multimodal-bias --version`.
  - [x] Run `uv run multimodal-bias smoke-model --model-config <dummy test config or documented local smoke config>`.
  - [x] Remove any generated `src/**/__pycache__` or `tests/**/__pycache__`, then rerun scaffold/cache guard checks.

### Review Findings

- [x] [Review][Patch] Record model config source path so load errors can include config path [`src/multimodal_bias/schemas.py`:75]
- [x] [Review][Patch] Wrap all Hugging Face local load failures, including `ImportError`, in `ModelLoadError` with full load context [`src/multimodal_bias/models/hf_vlm.py`:51]
- [x] [Review][Patch] Split processor and model `from_pretrained` kwargs so the processor does not receive model-only options [`src/multimodal_bias/models/hf_vlm.py`:73]
- [x] [Review][Patch] Validate per-request `max_new_tokens` overrides consistently in dummy and Hugging Face adapters [`src/multimodal_bias/models/hf_vlm.py`:115]
- [x] [Review][Patch] Reject ambiguous image inputs and validate local image paths before processor calls [`src/multimodal_bias/models/hf_vlm.py`:198]
- [x] [Review][Patch] Move dict-style processor inputs to the selected model input device when possible [`src/multimodal_bias/models/hf_vlm.py`:194]
- [x] [Review][Patch] Prevent successful Hugging Face smoke results with empty decoded text and avoid unsafe prompt slicing [`src/multimodal_bias/models/hf_vlm.py`:216]
- [x] [Review][Patch] Fix lazy import tests so they are not preloaded and cover adapter, dummy, and Hugging Face modules [`tests/test_model_adapter.py`:162]
- [x] [Review][Patch] Add fake successful Hugging Face load/generate coverage for kwargs, decode behavior, and metadata [`tests/test_model_adapter.py`:174]
- [x] [Review][Patch] Add CLI failure coverage for invalid `hf_local` config/load paths [`tests/test_cli.py`:233]

## Dev Notes

### Current Workspace State

- Story 1.1 through Story 2.2 are complete and marked `done`.
- There is no git repository, `_bmad/bmm/config.yaml`, `project-context.md`, or `sprint-status.yaml` in this workspace.
- `pyproject.toml` currently targets Python `>=3.10,<3.11` and includes only `pyyaml` and `typer` as runtime dependencies.
- `torch`, `transformers`, `accelerate`, and image libraries are not project dependencies yet. Do not make default unit tests require them.
- `src/multimodal_bias/exceptions.py` already defines `ModelLoadError` and `InferenceError`.
- `src/multimodal_bias/models/adapter.py`, `src/multimodal_bias/models/hf_vlm.py`, and `src/multimodal_bias/models/dummy.py` currently contain only module docstrings.
- `src/multimodal_bias/cli.py` currently exposes `--help`, `--version`, `validate-data`, and `start-run`; follow the existing pattern of catching project exceptions and suppressing tracebacks.
- `configs/models/` currently contains only `.gitkeep`; adding `example_vlm.yaml` requires updating the scaffold placeholder guard.
- `schemas.py` uses frozen dataclasses and `Literal` types for shared boundaries. Continue that style unless a stronger local pattern already exists by implementation time.

### Story 2.3 Scope

Implement the local model adapter boundary and a smoke-load/generation command only.

Do not implement:

- full Reasoner inference over `test.csv`
- `raw_reasoner.jsonl`
- generated-output parsing
- verifier triggers, verifier execution, or arbitration
- final prediction or submission writing
- model selection, leaderboard comparison, or validation-set scoring
- compliance manifest writing beyond exposing model metadata needed by later stories
- remote model API calls, Hugging Face Inference API calls, `snapshot_download`, or network downloads during smoke execution
- deterministic label selection, answer scoring, keyword rules, majority voting, or Public LB-tuned rules

### Model Config Contract

Recommended `configs/models/example_vlm.yaml` shape:

```yaml
adapter: hf_local
model_name: example-local-vlm
snapshot_path: models/snapshots/example-local-vlm
revision: ""
snapshot_hash: "replace-with-local-snapshot-hash-or-commit"
local_files_only: true
trust_remote_code: false
device_map: auto
torch_dtype: auto
max_new_tokens: 128
do_sample: false
```

Validation requirements:

- `adapter` should be a stable literal such as `hf_local` or `dummy`.
- `local_files_only` must be `true` for local model execution.
- `snapshot_path` must be local for `hf_local`.
- At least one of `revision` or `snapshot_hash` must be non-empty for `hf_local`.
- Generation settings must be bounded and simple; keep `max_new_tokens` positive and practical for smoke tests.
- Unknown keys must fail to prevent silent config drift.

### Adapter Contract

The adapter boundary should produce raw text and metadata, not parsed answers.

Minimum contract guidance:

- `load()` performs local dependency/model initialization and returns or stores typed load metadata.
- `generate(request)` returns a typed result containing `raw_text` and generation metadata.
- Generation metadata should include at least `max_new_tokens`, `do_sample`, elapsed seconds, and any known input/output token counts.
- Load metadata should include `model_name`, `adapter`, `snapshot_path`, `revision`, `snapshot_hash`, `local_files_only`, `trust_remote_code`, and load status.
- The adapter must not know Multimodal label semantics except that generated text is raw output for later parsing.

### Hugging Face Local Adapter Guidance

- Use lazy imports so CPU-only tests can import the package without optional GPU/model dependencies.
- Prefer local snapshot directories. Do not accept remote repo IDs as a substitute for `snapshot_path` in `smoke-model`.
- Pass `local_files_only=True` to `from_pretrained`.
- Do not call `snapshot_download` in this story; downloading and eligibility review are separate operator/compliance concerns.
- Keep `trust_remote_code` defaulted to `false`. If enabled by config, make that explicit in metadata.
- A VLM-appropriate default model class is `AutoModelForImageTextToText`, but keep this configurable enough for eligible Qwen/LLaVA-class local snapshots.
- When using chat-style VLMs, keep chat template formatting inside the adapter and return only decoded generated text to upstream code.

### Previous Story Intelligence

- Story 1.1 established strict Python 3.10 range, `src/multimodal_bias/` package root, Typer CLI, `.gitignore` generated-artifact rules, scaffold placeholder guards, and CPU-safe `pytest`/`ruff` validation.
- Story 1.2 established concise CLI failure style: catch project exceptions, print actionable text, exit `1`, and avoid traceback output.
- Story 1.3 established `SampleRecord` and row-context-rich validation, but Story 2.3 should not parse official CSV rows.
- Story 1.4 established image load result dataclasses and per-sample status. Story 2.3 may reference image bytes/path in a generation request but should not reimplement image discovery or data validation.
- Story 2.1 established `CompetitionConfig`, `RunManifest`, `ConfigurationError`, strict YAML validation, `configs/base.yaml`, and `start-run`.
- Story 2.2 established Reasoner prompt dataclasses, prompt template validation, `PARSE_MARKER`, and `build_reasoner_prompt`. Story 2.3 should accept prompt text/raw prompt content but must not parse or enforce final labels.

### Architecture and Compliance Guardrails

- Use `src/multimodal_bias/` as the only importable package root.
- Model runtime interface belongs in `src/multimodal_bias/models/adapter.py`.
- Hugging Face-specific implementation belongs in `src/multimodal_bias/models/hf_vlm.py`.
- CPU-safe dummy implementation belongs in `src/multimodal_bias/models/dummy.py`.
- Public execution boundary for this story is `smoke-model` in `cli.py`.
- Model-specific config belongs in `configs/models/`.
- Generated artifacts, raw data, model weights, runs, and submissions must stay outside source code.
- Keep raw data read-only under `data/raw/`.
- Do not use a database, web UI, network API, remote model API, or interactive labeling product.
- `test.csv` and images are inference-only inputs and must not be inspected to create rules, examples, prompt tuning, or answer mappings.
- Public leaderboard score remains a sanity signal only, not a model adapter requirement.
- Final label decisions in future stories must come from generated LLM text and downstream parsing/arbitration, not from adapter heuristics.

### Testing Requirements

Minimum tests:

- valid dummy model config loads into a typed config object
- malformed model configs fail with `ConfigurationError`
- `hf_local` config with missing snapshot path or missing revision/snapshot hash fails clearly
- `local_files_only: false` is rejected
- dummy adapter load returns model metadata including local load status
- dummy adapter generation returns raw text and generation metadata without parsing labels
- `hf_vlm` import is lazy and does not require optional model dependencies at import time
- `smoke-model` succeeds with a dummy config and prints stable JSON
- `smoke-model` fails cleanly for invalid config/load paths with no traceback
- existing scaffold, CLI help/version, data loader, image IO, config, run logging, and prompt tests stay green

Recommended commands:

```bash
uv sync
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
uv run multimodal-bias --help
uv run multimodal-bias --version
uv run multimodal-bias smoke-model --model-config <dummy test config or local model config>
```

### Latest Technical Notes

- Hugging Face Transformers offline guidance says local or cached files must exist before offline execution; `HF_HUB_OFFLINE=1` and `local_files_only=True` prevent Hub calls during load.
- Transformers `AutoProcessor.from_pretrained` and model `from_pretrained` accept local directories, `revision`, `local_files_only`, and `trust_remote_code`; `trust_remote_code` executes custom model code and must be explicitly reviewed before use.
- Transformers image-text-to-text examples use `AutoProcessor`, `AutoModelForImageTextToText`, chat templates, `generate`, and `batch_decode` for VLM inference.
- `GenerationConfig` and `generate(..., return_dict_in_generate=True)` can expose richer generation outputs, but Story 2.3 only needs raw generated text plus stable metadata and should not require score tensors in CPU tests.
- As of 2026-06-18, do not pin a new heavy VLM stack in `pyproject.toml` unless implementation confirms the target environment and model choice. Keep optional model dependencies lazy so CPU CI remains stable.

### References

- [Source: docs/history/epics.md#Story-2.3-Implement-Local-VLM-Model-Adapter]
- [Source: docs/history/epics.md#Epic-2-Offline-Evidence-Grounded-Submission-Pipeline]
- [Source: docs/history/architecture.md#Runtime-&-Model-Architecture]
- [Source: docs/history/architecture.md#Reasoner-+-Conditional-Verifier]
- [Source: docs/history/architecture.md#Implementation-Patterns-&-Consistency-Rules]
- [Source: docs/history/architecture.md#Project-Structure-&-Boundaries]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md#Constraints]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/strategy.md#Model-Selection]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/compliance-references.md#Competition-Rules-That-Bend-Design]
- [Source: docs/history/stories/2-2-build-evidence-grounded-reasoner-prompts.md#Previous-Story-Intelligence]
- [Source: https://huggingface.co/docs/transformers/main/en/installation#offline-mode]
- [Source: https://huggingface.co/docs/transformers/main/en/model_doc/auto#transformers.AutoProcessor.from_pretrained]
- [Source: https://huggingface.co/docs/transformers/main/en/tasks/image_text_to_text]
- [Source: https://huggingface.co/docs/transformers/main/en/main_classes/text_generation]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-06-18: RED `uv run pytest tests/test_model_adapter.py tests/test_cli.py -q` failed because model adapter schemas, loader, factory, and CLI smoke command were not implemented yet.
- 2026-06-18: Targeted model/CLI/scaffold tests passed: `uv run pytest tests/test_model_adapter.py tests/test_cli.py tests/test_scaffold.py -q` (34 passed).
- 2026-06-18: Full regression passed: `uv run pytest` (110 passed).
- 2026-06-18: Quality checks passed: `uv run ruff check src tests` and `uv run ruff format --check src tests`.
- 2026-06-18: CLI checks passed: `uv run multimodal-bias --help`, `uv run multimodal-bias --version`, and dummy `smoke-model` JSON output.
- 2026-06-18: Removed generated `src/multimodal_bias/__pycache__` and `src/multimodal_bias/models/__pycache__`; final scaffold guard passed: `uv run pytest tests/test_scaffold.py` (6 passed), and source/test cache guard was clean.
- 2026-06-18: Code review produced 10 patch findings, 0 deferred findings, and 6 dismissed findings.
- 2026-06-18: Applied all Story 2.3 review patches; targeted tests passed: `uv run pytest tests/test_model_adapter.py tests/test_cli.py -q` (35 passed).
- 2026-06-18: Review validation passed: `uv sync`, `uv run pytest` (117 passed), `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run multimodal-bias --help`, `uv run multimodal-bias --version`, and dummy `smoke-model`.
- 2026-06-18: Removed generated `src/multimodal_bias/__pycache__` and `src/multimodal_bias/models/__pycache__`; final scaffold guard passed: `uv run pytest tests/test_scaffold.py` (6 passed), and source/test cache guard was clean.

### Implementation Plan

- Add typed model config, load metadata, and generation result dataclasses to `schemas.py`.
- Implement strict local model config loading and a small adapter contract.
- Add a dummy adapter for CPU-safe tests and a lazy Hugging Face local adapter for real smoke runs.
- Add `smoke-model` CLI with JSON output and concise failure behavior.
- Add CPU-safe model adapter and CLI tests, then run full validation.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented typed local model adapter schemas for config, load metadata, generation requests, generation metadata, and raw generation results.
- Implemented strict local model config loading with duplicate-key rejection, unknown-key rejection, local snapshot path validation, `local_files_only` enforcement, and revision/snapshot hash requirements for `hf_local`.
- Added CPU-safe dummy adapter and lazy Hugging Face local VLM adapter boundary without importing optional model dependencies at module import time.
- Added `smoke-model` CLI with stable JSON output and concise no-traceback handling for config, load, and inference failures.
- Added `configs/models/example_vlm.yaml` and updated scaffold guards because `configs/models/` now contains a real config artifact.
- Added CPU-safe adapter and CLI tests without official Multimodal data, model weights, GPU, network, PyTorch, Transformers, Accelerate, or Pillow.
- Applied review hardening for HF load error wrapping, config-path context, processor/model kwargs separation, request token guards, image input guards, dict input device moves, safe decode behavior, and stronger lazy-import/HF fake-path/CLI failure tests.

### File List

- `docs/history/stories/2-3-implement-local-vlm-model-adapter.md`
- `configs/models/example_vlm.yaml`
- `configs/models/.gitkeep` (deleted)
- `src/multimodal_bias/cli.py`
- `src/multimodal_bias/models/adapter.py`
- `src/multimodal_bias/models/dummy.py`
- `src/multimodal_bias/models/hf_vlm.py`
- `src/multimodal_bias/schemas.py`
- `tests/test_cli.py`
- `tests/test_model_adapter.py`
- `tests/test_scaffold.py`

## Change Log

- 2026-06-18: Created Story 2.3 context file and moved status to ready-for-dev.
- 2026-06-18: Implemented Story 2.3 local VLM adapter contract, model config validation, dummy/HF adapters, smoke-model CLI, tests, and moved status to review.
- 2026-06-18: Applied all code review patch findings and moved status to done.
