---
baseline_commit: NO_VCS
---

# Story 2.5: Parse Reasoner Outputs Into Structured Predictions

Status: done

> **Supersession Notice (2026-06-20):** This story records the completed Reasoner v2 parser baseline. Its parsed fields and historical tasks are retained only for A/B reproduction. Story 2.7 exclusively owns migration to and acceptance of the active Reasoner v3 contract; v2 artifacts remain immutable.

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a competition developer,
I want generated Reasoner text parsed into validated structured outputs,
so that downstream submission code consumes only checked labels and parse states.

## Acceptance Criteria

1. Given a completed `raw_reasoner.jsonl`, when the Reasoner parser runs, then it writes UTF-8 `parsed_reasoner.csv` under the same run directory with one row per raw row in the same order.
2. Given a generated row whose final non-empty line starts with `FINAL_ANSWER_JSON:`, when the suffix is a strict JSON object matching the approved Reasoner output contract, then the parsed row contains `sample_id`, `parsed_label`, `evidence_summary`, `evidence_type`, `uncertainty_signal`, `risk_flags`, and `parse_status="valid"`.
3. Given a generated row with a missing final marker, malformed JSON, missing or extra fields, invalid field types, an empty evidence string, an unsupported evidence type, or a label outside string values `"0"`, `"1"`, and `"2"`, when parsing runs, then it emits an invalid parse row with no parsed label, a stable `parse_status`, `risk_flags` containing `invalid_parse`, and actionable error context without guessing, coercing, or selecting a fallback label.
4. Given a raw Reasoner row with `status` other than `generated` or without `raw_output`, when parsing runs, then it preserves the sample as a source-failure parse row and does not manufacture a label; malformed JSONL structure, duplicate sample IDs, or unreadable source artifacts raise `ParseError` as fatal artifact errors.
5. Given the `infer` CLI command completes Reasoner generation, when post-inference parsing succeeds, then its run directory contains both `raw_reasoner.jsonl` and atomically written `parsed_reasoner.csv`, and its success output reports parsed valid/invalid counts; parser failures exit cleanly without traceback and never create `final_predictions.csv` or `submission.csv`.
6. CPU-safe unit and CLI tests cover valid output, each invalid parse category, source failures, Unicode/CSV escaping, ordering, atomic artifact behavior, CLI integration, and all existing regressions without official Multimodal data, model weights, GPU, network, PyTorch, Transformers, Accelerate, or Pillow.

## Tasks / Subtasks

- [x] Define structured Reasoner parse schemas (AC: 1, 2, 3, 4)
  - [x] Add the architecture-required `ReasonerOutput` schema and a typed parse result/summary boundary to `src/multimodal_bias/schemas.py`.
  - [x] Use stable parse statuses such as `valid`, `source_failed`, `missing_marker`, `invalid_json`, `invalid_schema`, and `invalid_label`; every non-`valid` status must be recognizable as an invalid parse by later trigger logic.
  - [x] Preserve typed values for `parsed_label`, `evidence_summary`, `evidence_type`, `uncertainty_signal`, `risk_flags`, `parse_status`, and `parse_error`; do not pass anonymous dictionaries between parser and later pipeline stages.
  - [x] Represent CSV `risk_flags` as a deterministic JSON array string. Include `invalid_parse` for invalid rows and `protected_attribute_risk` for valid model outputs whose corresponding boolean is true.

- [x] Implement strict generated-output parsing in `src/multimodal_bias/parsing.py` (AC: 2, 3, 4)
  - [x] Parse only the final non-empty output line and require it to start with the exact approved marker `FINAL_ANSWER_JSON:`; this avoids accepting marker text echoed earlier from the prompt.
  - [x] Decode the marker suffix with `json.loads()` plus a duplicate-key rejecting `object_pairs_hook`, and require exactly one JSON object with exactly `label`, `evidence`, `evidence_type`, `uncertainty_signal`, and `protected_attribute_risk`.
  - [x] Accept labels only as strings `"0"`, `"1"`, or `"2"`; reject integers, booleans, whitespace-padded values, and all other values rather than coercing them.
  - [x] Require non-empty string evidence, an evidence type from the existing `EvidenceType` contract, and actual JSON booleans for uncertainty/protected-attribute fields.
  - [x] Preserve schema-valid semantic signals even when they are suspicious. Do not rewrite labels based on evidence type or uncertainty consistency; those become inputs to Story 3 verification triggers.
  - [x] Convert generated-text failures to typed invalid parse results and reserve `ParseError` for fatal source/artifact corruption that prevents trustworthy row identity or complete processing.

- [x] Read raw JSONL and write `parsed_reasoner.csv` safely (AC: 1, 3, 4, 5)
  - [x] Add `PARSED_REASONER_FILENAME = "parsed_reasoner.csv"` and one public orchestration function that accepts a raw artifact path plus destination/run context.
  - [x] Validate every JSONL line with duplicate-key rejection as a JSON object containing a non-empty string `run_id`, unique non-empty string `sample_id`, valid raw `status`, and compatible `raw_output` state.
  - [x] Reject an empty source file, blank JSONL lines, or mixed `run_id` values as fatal artifact corruption; require all source rows to belong to the same run.
  - [x] Preserve raw row order and emit exactly one parsed CSV row per validly structured raw row, including source and generated-text failures.
  - [x] Write a fixed header: `run_id`, `sample_id`, `parsed_label`, `evidence_summary`, `evidence_type`, `uncertainty_signal`, `risk_flags`, `parse_status`, `parse_error`.
  - [x] Serialize valid booleans as lowercase `true`/`false`, leave unavailable structured fields empty for invalid rows, and let `csv.DictWriter` handle commas, quotes, newlines, and Unicode evidence safely.
  - [x] Write to a sibling temporary file and replace `parsed_reasoner.csv` only after all rows succeed; clean the temporary file on failure and do not overwrite an existing completed artifact silently.

- [x] Integrate parsing with the existing `infer` CLI path (AC: 1, 5)
  - [x] Keep `reasoner.py` responsible only for raw inference and keep parsing logic in `parsing.py`.
  - [x] After `run_reasoner_inference()` succeeds, call the parser from `cli.py`; report `parsed_reasoner_path`, valid count, and invalid count with the existing run summary.
  - [x] Catch `ParseError` and parser artifact `OSError` with concise stderr text and exit `1` without traceback while preserving the already-auditable raw artifact.
  - [x] Update the CPU-only dummy adapter output only as needed to end with one contract-valid marker JSON object while preserving its existing diagnostic raw text behavior.
  - [x] Do not add a model-specific parser, remote service, parser CLI outside the architecture command surface, verifier execution, arbitration, fallback label, `final_predictions.csv`, or `submission.csv`.

- [x] Add CPU-safe parser and integration tests (AC: 1, 2, 3, 4, 5, 6)
  - [x] Add `tests/test_parsing.py` with table-driven cases for valid labels, all evidence types, protected-risk flagging, Unicode/CSV escaping, and stable row ordering.
  - [x] Cover missing/non-final marker, empty suffix, malformed JSON, non-object JSON, duplicate/missing/extra fields, wrong field types, blank evidence, unsupported evidence type, and string/integer/out-of-range label failures.
  - [x] Cover raw `image_failed`, `prompt_failed`, and `inference_failed` rows as `source_failed` without fallback labels.
  - [x] Cover unreadable/malformed JSONL, missing row identity, duplicate sample IDs, existing output collisions, and an injected mid-write failure proving no complete-looking CSV or temporary file remains.
  - [x] Update `tests/test_cli.py` so the dummy `infer` path produces `parsed_reasoner.csv`, reports counts, and still does not produce verification/final/submission artifacts.
  - [x] Preserve direct `run_reasoner_inference()` tests that assert raw inference alone does not create downstream artifacts.

- [x] Run validation (AC: 6)
  - [x] Run `uv sync`.
  - [x] Run `uv run pytest`.
  - [x] Run `uv run ruff check src tests`.
  - [x] Run `uv run ruff format --check src tests`.
  - [x] Run `uv run multimodal-bias --help`.
  - [x] Run `uv run multimodal-bias --version`.
  - [x] Run a CPU-safe `uv run multimodal-bias infer --config <tmp config> --model-config <tmp dummy model config>` smoke path and inspect both raw and parsed artifacts.
  - [x] Remove any generated `src/**/__pycache__` or `tests/**/__pycache__`, then rerun scaffold/cache guard checks.

### Review Findings

- [x] [Review][Patch] Convert generated rows without string `raw_output` into auditable `source_failed` rows instead of aborting the artifact [src/multimodal_bias/parsing.py:261]
- [x] [Review][Patch] Validate raw `status` type before set membership so malformed arrays/objects raise `ParseError` without a CLI traceback [src/multimodal_bias/parsing.py:255]
- [x] [Review][Patch] Use unique exclusive temporary files and atomic no-clobber publication for concurrent parser safety [src/multimodal_bias/parsing.py:168]
- [x] [Review][Patch] Validate parsed lineage against the active run ID and exact ordered inference sample set [src/multimodal_bias/cli.py:166]
- [x] [Review][Patch] Convert JSON recursion, oversized-number, and invalid-Unicode edge cases into typed invalid states or `ParseError` [src/multimodal_bias/parsing.py:70]
- [x] [Review][Patch] Add missing malformed-source, unreadable-source, parser-write, and concurrent-publication failure-path tests [tests/test_parsing.py:275]
- [x] [Review][Defer] Installed console-script test may resolve a stale/global executable [tests/test_cli.py:537] — deferred, pre-existing
- [x] [Review][Defer] Lazy-import test removes shared modules from `sys.modules` without restoring them [tests/test_model_adapter.py:181] — deferred, pre-existing

## Dev Notes

### Current Workspace State

- Stories 1.1 through 2.4 are complete and marked `done`; Story 2.4's full validation passed with 128 tests.
- There is no git repository, `_bmad/bmm/config.yaml`, `project-context.md`, or `sprint-status.yaml`; this story therefore uses `baseline_commit: NO_VCS` and status is tracked in the story file itself.
- `src/multimodal_bias/parsing.py` currently contains only a module docstring and is the primary implementation target.
- `ParseError` already exists in `exceptions.py`; reuse it rather than adding another parser exception hierarchy.
- `schemas.py` already owns `EvidenceType`, raw Reasoner row schemas, and run/result boundaries. Add structured parser contracts there.
- `reasoner.py` writes `raw_reasoner.jsonl` atomically and includes one ordered row per source sample, including recoverable failure rows. Treat that file as immutable parser input.
- `cli.py` currently calls `prepare_reasoner_inference()`, creates the run, and calls `run_reasoner_inference()`. Add post-inference parsing there while leaving raw orchestration unchanged.
- The dummy adapter currently echoes diagnostic prompt text without a final contract JSON line. It may be extended with a deterministic, schema-valid test response so CLI integration exercises the valid parser path.

### Parser Contract

Approved final line example:

```text
FINAL_ANSWER_JSON: {"label":"2","evidence":"The provided evidence does not identify either person.","evidence_type":"insufficient_evidence","uncertainty_signal":true,"protected_attribute_risk":false}
```

Parsing rules:

- Ignore leading/trailing blank output lines, but inspect only the final non-empty line.
- The final line must begin with exact marker text `FINAL_ANSWER_JSON:` after normal line splitting; do not search arbitrary prose, Markdown fences, or earlier echoed prompt text.
- The marker suffix must be one complete JSON object with unique keys. `json.loads()` may accept surrounding JSON whitespace, but no prose may follow the object.
- Require exact keys and exact JSON types. In particular, Python `bool` must not be accepted as an integer label, and numeric labels must not be coerced to strings.
- A valid structured output may still contain uncertainty/evidence inconsistencies. Preserve them for conditional verification instead of implementing deterministic label correction in the parser.
- Never infer a label from answer text, model-specific prose, regular-expression keywords, sample ID, test question patterns, or Public leaderboard behavior.

Recommended invalid-row behavior:

- `parsed_label`, `evidence_summary`, `evidence_type`, and `uncertainty_signal` are empty.
- `risk_flags` is JSON text `["invalid_parse"]`.
- `parse_status` identifies the stable failure class.
- `parse_error` contains concise sample-aware context but no traceback.
- Raw inference failures use `source_failed`; no label `2` is assigned here. Future arbitration is the only layer allowed to convert recoverable failures to label `2`.

### Existing Files To Update

- `src/multimodal_bias/parsing.py`: currently no implementation; add marker/schema validation plus atomic JSONL-to-CSV orchestration.
- `src/multimodal_bias/schemas.py`: preserve all existing frozen dataclasses and literals; add `ReasonerOutput`, parse status/record/result contracts.
- `src/multimodal_bias/cli.py`: preserve all current commands and no-traceback behavior; add only post-inference parse orchestration and summary/error reporting.
- `src/multimodal_bias/models/dummy.py`: preserve load/generation validation and existing diagnostic content; append one valid final marker line if using it for CLI parser success.
- `tests/test_cli.py`: update only Story 2.5 expectations around parsed output while preserving earlier command coverage.
- `tests/test_reasoner.py`: preserve the direct raw-only boundary and existing atomic/raw failure coverage.
- `tests/test_parsing.py`: new focused CPU-safe parser suite.

### Architecture and Compliance Guardrails

- Keep all importable code under `src/multimodal_bias/`; generated CSV belongs only under `runs/{run_id}/`.
- Use typed schemas across Reasoner, parser, future Verifier, arbitration, and submission boundaries.
- The parser may validate generated model text but must not become a rule-based answer engine. Final label candidates must originate in generated LLM JSON.
- Keep raw text and raw failure metadata intact for audit. Parsing must not mutate or rewrite `raw_reasoner.jsonl`.
- `parsed_reasoner.csv` is not a Multimodal submission and must not be written under `submissions/`.
- Do not write `final_predictions.csv` or `submission.csv`; those belong to later arbitration/submission stories.
- Preserve local/offline operation and optional model dependency laziness. Parsing requires only Python 3.10 standard-library `json` and `csv`.
- Do not add examples, heuristics, or mappings derived from evaluation-set wording, choices, images, inferred answers, or Public LB movement.

### Previous Story Intelligence

- Story 2.4 established preflight ordering: prompt/data/model failures occur before run directory creation.
- Raw output rows now include model load metadata for both success and failure paths; the parser does not need to duplicate this metadata into the tabular artifact.
- HF requests intentionally pass image bytes/format without also passing image paths; Story 2.5 must not disturb model adapter behavior.
- Raw JSONL writing uses a sibling temporary file and atomic replacement. Match that safety pattern for parsed CSV.
- Missing/corrupt images and per-sample inference errors are preserved as raw rows. Parsing must preserve one-to-one row lineage and must not drop those samples.
- A pre-existing installed console-script test concern remains deferred in `docs/history/deferred-work.md`; do not broaden this story to resolve unrelated environment behavior.

### Testing Requirements

Minimum assertions:

- valid marker JSON produces exact typed values and `parse_status="valid"`
- all invalid generated outputs remain rows but have no parsed label
- labels `3`, `-1`, `" 0 "`, `0`, `true`, and `null` are invalid
- evidence types outside the existing four-value contract are invalid
- non-boolean uncertainty/risk fields are invalid
- protected risk yields deterministic JSON risk flags
- raw source failures yield `source_failed` and `invalid_parse`
- duplicate IDs, duplicate JSON keys, blank lines, empty files, mixed run IDs, and structurally malformed JSONL fail with `ParseError`
- CSV headers, Unicode, commas, quotes, and line breaks round-trip through `csv.DictReader`
- parsed CSV replacement is atomic and leaves no temp file on failure
- CLI infer reports raw and parsed paths/counts without creating final/submission artifacts
- all 128 prior tests remain green, adjusted only where Story 2.5 intentionally evolves CLI output artifacts

### Latest Technical Notes

- No new external package is needed. Python 3.10 standard-library `json.loads()` and `csv.DictWriter` are sufficient and keep parser tests CPU-safe.
- The target runtime remains Python `>=3.10,<3.11`; do not use syntax or APIs introduced after Python 3.10.
- Strictness here means contract validation after JSON decoding. Python's decoder behavior alone does not enforce exact keys, field types, supported labels, or non-empty evidence; implement those checks explicitly.

### References

- [Source: docs/history/epics.md#Story-2.5-Parse-Reasoner-Outputs-Into-Structured-Predictions]
- [Source: docs/history/epics.md#Epic-2-Offline-Evidence-Grounded-Submission-Pipeline]
- [Source: docs/history/architecture.md#Reasoner-+-Conditional-Verifier]
- [Source: docs/history/architecture.md#Format-Patterns]
- [Source: docs/history/architecture.md#Communication-Patterns]
- [Source: docs/history/architecture.md#Process-Patterns]
- [Source: docs/history/architecture.md#Architectural-Boundaries]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md#Constraints]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/strategy.md#Inference-Strategy]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/strategy.md#Conditional-Verification]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/strategy.md#Runtime-and-Logging-Contract]
- [Source: configs/prompts/reasoner_v1.yaml]
- [Source: docs/history/stories/2-4-run-reasoner-inference-and-preserve-raw-outputs.md#Previous-Story-Intelligence]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-06-18: RED confirmed with `uv run pytest tests/test_parsing.py -q`; collection failed because the Story 2.5 parser API did not exist.
- 2026-06-18: Parser GREEN confirmed with 41 focused tests covering strict JSON/schema validation, source corruption, failure rows, CSV encoding, ordering, and atomic writes.
- 2026-06-18: CLI integration RED confirmed for missing parsed artifact reporting and non-contract dummy output; targeted tests passed after implementation.
- 2026-06-18: Full validation passed with 170 tests, ruff lint/format, CLI help/version, CPU-safe infer smoke, and scaffold/cache guards.
- 2026-06-18: Code review patch cycle passed with 180 tests, ruff lint/format, CLI help/version, CPU-safe infer smoke, and cache guards.

### Implementation Plan

- Add typed valid/invalid Reasoner parse contracts in `schemas.py`.
- Implement exact final-marker parsing, duplicate/non-standard JSON rejection, raw lineage validation, and atomic CSV writing in `parsing.py`.
- Extend the dummy adapter with a contract-valid final line and invoke parsing after raw inference from `cli.py`.
- Add focused parser tests plus CLI/model adapter integration coverage, then run the full Story validation matrix.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Added typed `ReasonerOutput`, parsed row/status/risk contracts, and parse summaries for downstream module boundaries.
- Implemented strict final-line `FINAL_ANSWER_JSON:` parsing without label coercion or fallback selection, including duplicate-key and non-standard JSON constant rejection.
- Added ordered one-to-one raw JSONL lineage validation and atomic UTF-8 `parsed_reasoner.csv` output with stable invalid/source-failure states.
- Integrated post-inference parsing into `infer`, preserved raw artifacts on parse failure, and kept final/submission artifacts out of Story 2.5 scope.
- Added 41 focused parser tests and expanded CLI/dummy adapter coverage; all 170 tests and required validation commands passed.
- Resolved all Story 2.5 review patches: source-failure recovery, malformed status handling, expected run/sample lineage, atomic no-clobber publication, JSON/Unicode resource guards, and failure-path coverage.

### File List

- docs/history/deferred-work.md
- docs/history/stories/2-5-parse-reasoner-outputs-into-structured-predictions.md
- src/multimodal_bias/cli.py
- src/multimodal_bias/models/dummy.py
- src/multimodal_bias/parsing.py
- src/multimodal_bias/schemas.py
- tests/test_cli.py
- tests/test_model_adapter.py
- tests/test_parsing.py

## Change Log

- 2026-06-18: Created Story 2.5 context file and moved status to ready-for-dev.
- 2026-06-18: Implemented strict Reasoner output parsing, atomic parsed CSV artifacts, CLI integration, and CPU-safe coverage; moved status to review.
- 2026-06-18: Addressed all code review patches, completed validation, and moved status to done.
