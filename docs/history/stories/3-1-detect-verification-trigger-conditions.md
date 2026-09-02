---
baseline_commit: NO_VCS
---

# Story 3.1: Detect Verification Trigger Conditions

Status: backlog

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a competition developer,
I want risky Reasoner outputs to be classified into stable verification trigger categories,
so that only predictions needing review are sent to the Verifier.

## Acceptance Criteria

1. Given one or more Reasoner v3 parsed rows, when trigger detection runs, then it preserves `run_id`, `sample_id`, selected-label lineage, generated `uncertainty_option_index`, schema version, and parser status without mutating artifacts.
2. Given parser state and semantic fields, when a row is classified, then every pre-Verifier trigger uses the stable six-name vocabulary and no numeric label is treated as inherently person-specific or uncertain.
3. Given a non-valid/source-failure row, when trigger detection runs, then it emits `invalid_parse` without inventing a fallback candidate.
4. Given a valid row, semantic consistency is evaluated from `label`, `uncertainty_option_index`, `uncertainty_signal`, and `evidence_type`; `uncertainty_signal == (label == str(uncertainty_option_index))` must hold.
5. Given uncertainty positions 0, 1, and 2 with otherwise equivalent semantics, when trigger detection runs, then results are position-independent.
6. Given protected-attribute, appearance-only, vague visual grounding, or unsupported-evidence signals, when trigger detection runs, then appropriate triggers are emitted without test-derived answer mappings.
7. CPU-safe tests cover all six pre-Verifier trigger names, all three uncertainty positions, semantic mismatches, invalid rows, deterministic ordering, duplicate suppression, unsupported values, absence of fixed-label/fallback behavior, and exclusion of the post-Verifier conflict event.

## Corrective Work Required (2026-06-20)

- [ ] Depend on Story 2.7 `reasoner_output_v3` fields and reject incompatible schema versions.
- [ ] Remove `PERSON_LABELS={"0","1"}`, `parsed_label == "2"`, and equivalent numeric-semantic branches.
- [ ] Preserve generated uncertainty-index lineage in trigger decisions/reports.
- [ ] Split the six-name pre-Verifier trigger type/order from the post-Verifier `reasoner_verifier_conflict` event type.
- [ ] Add position 0/1/2 parameterized regression tests and rerun the full CPU suite.
- [ ] Re-review this reopened story before returning it to `done`.

## Historical Tasks / Subtasks (pre-correction implementation)

- [x] Define typed trigger contracts in `src/multimodal_bias/schemas.py` (AC: 1, 2)
  - [x] Historical implementation used one seven-name `VerificationTrigger` Literal; corrective work splits six pre-Verifier triggers from the post-Verifier conflict event.
  - [x] Add a frozen `VerificationTriggerDecision` dataclass with `run_id`, `sample_id`, `parsed_label`, `parse_status`, `triggers`, and `requires_verification`.
  - [x] Add a frozen `VerificationTriggerReport` dataclass with ordered decisions, total samples, triggered sample count, and per-trigger counts.
  - [x] Reuse existing `ReasonerLabel` and `ReasonerParseStatus`; do not introduce integer labels or anonymous dictionaries.

- [x] Implement Reasoner-output trigger detection in `src/multimodal_bias/verifier.py` (AC: 1, 2, 3, 4, 5)
  - [x] Historical implementation placed `reasoner_verifier_conflict` in `VERIFICATION_TRIGGER_NAMES`; corrective work removes it from initial routing and gives it a post-Verifier event contract.
  - [x] Add public functions such as `detect_verification_triggers(record: ParsedReasonerRecord) -> VerificationTriggerDecision` and `detect_verification_trigger_report(records: Sequence[ParsedReasonerRecord]) -> VerificationTriggerReport`.
  - [x] Preserve input order exactly in report output and keep trigger order deterministic by using `VERIFICATION_TRIGGER_NAMES` order.
  - [x] Emit `invalid_parse` for any `parse_status != "valid"` or any row carrying `invalid_parse`; valid rows must never carry `invalid_parse`.
  - [x] Historical behavior classified confidence and evidence consistency using the pre-v3 contract; Story 2.7 and the corrective work above supersede numeric-label assumptions.
  - [x] Historical `unsupported_evidence` behavior is retained only where it agrees with generated option-index semantics.
  - [x] Emit `protected_attribute_risk` when parser risk flags contain `protected_attribute_risk`.
  - [x] Emit `appearance_only_reasoning` only from a small, project-owned public cue list derived from `FORBIDDEN_SOLE_SUPPORT_CUES` and strategy terms such as appearance, expression, posture, clothing, attractiveness, social background, perceived gender, race, age, body type, or stereotype assumptions.
  - [x] Emit `ambiguous_visual_grounding` when a person label relies on objective visual evidence but the evidence summary lacks concrete object/action/text/location/role grounding and instead uses vague visual claims such as looks/appears/seems.
  - [x] Historical implementation reserved `reasoner_verifier_conflict` in the shared order; corrective work removes it from the Story 3.1 trigger type entirely because no Verifier output exists yet.
  - [x] Validate malformed `ParsedReasonerRecord` values defensively and raise `ParseError` or a clear project exception for unsupported parse statuses, unsupported risk flags, missing required valid-row fields, or non-UTF-8 evidence text.
  - [x] Keep `verifier.py` free of model execution, verifier prompting, raw verifier parsing, arbitration, submission generation, Public LB logic, and any answer-mapping rule.

- [x] Add focused CPU-safe coverage in `tests/test_verifier.py` (AC: 1, 2, 3, 4, 5, 6)
  - [x] Historical tests asserted the conflict name was reserved but not emitted; corrective tests assert it is absent from pre-Verifier trigger names and present only in the post-Verifier event vocabulary.
  - [x] Cover one no-trigger row for each supported decisive evidence type where the label/evidence/uncertainty fields are internally consistent.
  - [x] Cover invalid parse statuses from Story 2.5: `source_failed`, `missing_marker`, `invalid_json`, `invalid_schema`, and `invalid_label`.
  - [x] Cover `protected_attribute_risk`, uncertainty/label/evidence mismatches, appearance/protected-cue-only evidence summaries, and ambiguous visual grounding.
  - [x] Cover trigger ordering, duplicate suppression, report counts, input order preservation, frozen dataclass behavior, and no mutation of `ParsedReasonerRecord` inputs.
  - [x] Cover malformed rows with unsupported status, unsupported risk flag, missing valid-row label/evidence/evidence type/uncertainty fields, and invalid Unicode evidence.

- [x] Preserve existing pipeline behavior and boundaries (AC: 1, 5, 6)
  - [x] Do not change `parse_reasoner_output`, `parse_reasoner_artifact`, or `parsed_reasoner.csv` format.
  - [x] Do not change `make-submission`; Story 2.6 remains a Reasoner-only safe baseline until Story 3.3 arbitration integrates trigger/verifier output.
  - [x] Do not add a CLI command in this story; `verify-risky` belongs to Story 3.2.
  - [x] Keep all new tests CPU-only and construct records directly in tests.

- [x] Run validation (AC: 6)
  - [x] Run `uv sync`.
  - [x] Run `uv run pytest`.
  - [x] Run `uv run ruff check src tests`.
  - [x] Run `uv run ruff format --check src tests`.
  - [x] Run `uv run multimodal-bias --help`.
  - [x] Run `uv run multimodal-bias --version`.
  - [x] Remove generated `src/**/__pycache__` and `tests/**/__pycache__`, then rerun `uv run python -B -m pytest tests/test_scaffold.py -q`.

### Review Findings

- [x] [Review][Patch] Rows carrying `invalid_parse` must emit `invalid_parse` without falling into valid-row field validation [src/multimodal_bias/verifier.py:123]
- [x] [Review][Patch] `appearance_only_reasoning` must require sole-support semantics instead of firing on any cue word [src/multimodal_bias/verifier.py:224]
- [x] [Review][Patch] Visual cue matching must be punctuation-safe and normalize trigger phrases consistently [src/multimodal_bias/verifier.py:260]
- [x] [Review][Patch] `ambiguous_visual_grounding` must detect unsupported generic visual evidence and avoid generic or negated concrete-word masking [src/multimodal_bias/verifier.py:237]
- [x] [Review][Patch] `VerificationTriggerReport` must not expose mutable trigger counts from a frozen report contract [src/multimodal_bias/schemas.py:148]
- [x] [Review][Patch] Report detection must reject non-sequence inputs with `ParseError` instead of leaking Python `TypeError` [src/multimodal_bias/verifier.py:156]

## Dev Notes

### Current Workspace State

- Stories 1.1 through 2.6 are complete and marked `done`; Story 2.6 completed review patches with 254 full CPU-safe tests passing.
- There is no git repository, `_bmad/bmm/config.yaml`, `project-context.md`, or `sprint-status.yaml`; this story uses `baseline_commit: NO_VCS` and status is tracked in this story file.
- `src/multimodal_bias/verifier.py` currently contains only `"""Conditional verifier boundary."""`; this story should add trigger detection there before Story 3.2 adds model-backed verifier execution.
- `src/multimodal_bias/schemas.py` already defines `ParsedReasonerRecord`, `ReasonerLabel`, `ReasonerRiskFlag`, `ReasonerParseStatus`, and final/submission dataclasses. Add trigger contracts there rather than passing dictionaries.
- `src/multimodal_bias/parsing.py` owns the parser and fixed `PARSED_REASONER_FIELDNAMES`; do not modify parser behavior for this story unless a shared constant extraction is strictly necessary.
- Existing tests are CPU-only and avoid optional model dependencies. Follow the direct dataclass fixture style used in `tests/test_parsing.py` and `tests/test_submission.py`.

### Story 3.1 Scope and Pipeline Position

This story starts Epic 3 and adds a pure classification boundary:

```text
parsed Reasoner records
  -> detect verification trigger categories
  -> typed trigger decisions/report
  -> Story 3.2 uses triggered decisions to run verifier only where needed
```

The detector must not generate labels, change labels, run models, parse raw verifier text, or write submissions. Invalid rows remain invalid; downstream arbitration may use only valid generated candidates and otherwise returns `unresolved`.

### Trigger Semantics

Use these exact trigger names and deterministic order:

```text
invalid_parse
low_confidence
unsupported_evidence
protected_attribute_risk
appearance_only_reasoning
ambiguous_visual_grounding
```

Reasoner-only Story 3.1 should emit:

- `invalid_parse`: non-`valid` parser status or `invalid_parse` risk flag.
- `low_confidence`: generated semantic fields indicate uncertainty/confidence tension; numeric label alone is never a cause.
- `unsupported_evidence`: `label`, generated uncertainty index, uncertainty signal, and evidence type are inconsistent.
- `protected_attribute_risk`: parser risk flag contains `protected_attribute_risk`.
- `appearance_only_reasoning`: evidence summary contains only forbidden/subjective support cues from project-owned safety terms, not Multimodal evaluation-set-derived patterns.
- `ambiguous_visual_grounding`: a person label claims objective visible evidence but evidence is vague visual grounding rather than concrete object/action/text/location/role evidence.

`reasoner_verifier_conflict` is not a Story 3.1 trigger. It belongs to the post-Verifier comparison event vocabulary owned by Story 3.2 and must never cause an otherwise untriggered Verifier pass.

### Architecture and Compliance Guardrails

- Stable verifier trigger names are explicitly required by the architecture and epics. Do not rename, pluralize, or localize them.
- Trigger rules may use project safety guardrails and public bias-control cue lists, but must not inspect official evaluation question wording, answer positions, Public LB movement, hidden labels, or any hand-built answer mapping.
- `test.csv` and images remain inference-only. Trigger detection may inspect parsed Reasoner evidence text and parser metadata, not raw official answer semantics for deterministic label selection.
- Keep the detector deterministic and auditable. Same parsed record must always produce the same ordered trigger tuple.
- Keep implementation Python 3.10-compatible (`pyproject.toml` requires `>=3.10,<3.11`) and use standard-library/dataclass patterns already present in this repo.

### Existing Files To Update

- `src/multimodal_bias/schemas.py`: add trigger Literal and frozen decision/report dataclasses.
- `src/multimodal_bias/verifier.py`: implement pure trigger detection and report aggregation.
- `tests/test_verifier.py`: new focused CPU-safe suite.
- `docs/history/stories/3-1-detect-verification-trigger-conditions.md`: update task status and Dev Agent Record during implementation.

Do not update:

- `src/multimodal_bias/cli.py`: no new command until Story 3.2.
- `src/multimodal_bias/submission.py`: keep Story 2.6 Reasoner-only baseline intact.
- `src/multimodal_bias/arbitration.py`: arbitration starts in Story 3.3.
- `src/multimodal_bias/parsing.py`: keep parser format stable.

### Previous Story Intelligence

- Story 2.6 hardened staged artifact identity/equality checks, no-follow CSV reads, rollback cleanup, and API context validation. Preserve those safety patterns when later stories read artifacts, but Story 3.1 should not write artifacts.
- Story 2.6 established that invalid parse/source-failure rows must not become fallback labels at submission time. Story 3.1 should classify them as `invalid_parse` and leave recovery to verifier/arbitration stories.
- Story 2.5 established invalid rows use `parsed_label=None`, empty evidence fields, risk flag `invalid_parse`, stable parse statuses, and actionable `parse_error` text.
- Story 2.2 established forbidden sole-support cues in `prompting/guards.py`; reuse the same safety vocabulary rather than creating test-set-derived trigger rules.
- Existing validation commands can create `__pycache__` directories; remove generated caches before final scaffold/cache guard validation.

### Testing Requirements

Minimum assertions:

- all six pre-Verifier trigger names are present exactly once in stable order
- no-trigger valid rows return `triggers == ()` and `requires_verification is False`
- every non-valid parse status emits `invalid_parse` and `requires_verification is True`
- `protected_attribute_risk` flag emits only the corresponding trigger unless other independent risks are present
- valid label/evidence/uncertainty inconsistencies emit `unsupported_evidence`
- equivalent uncertainty semantics at positions 0/1/2 produce equivalent trigger results
- appearance/protected cue evidence emits `appearance_only_reasoning`
- vague visual grounding for person labels emits `ambiguous_visual_grounding`
- `reasoner_verifier_conflict` is absent from Reasoner-only trigger types/results and exists only as a post-Verifier event
- duplicate causes do not duplicate trigger names
- report counts are deterministic and input order is preserved
- malformed records fail with a clear project exception
- trigger detection does not mutate input dataclasses or parsed artifacts

### Latest Technical Notes

- No new external API or package is needed for Story 3.1. The trigger detector should use Python standard-library string handling and existing project constants only.
- This story should not add pandas, regex-heavy external dependencies, ML libraries, model calls, or network calls.

### References

- [Source: docs/history/epics.md#Story-3.1-Detect-Verification-Trigger-Conditions]
- [Source: docs/history/epics.md#Epic-3-Bias-Safe-Conditional-Verification-and-Arbitration]
- [Source: docs/history/epics.md#Requirements-Inventory]
- [Source: docs/history/architecture.md#Reasoner-+-Conditional-Verifier]
- [Source: docs/history/architecture.md#Verification-Event-Patterns]
- [Source: docs/history/architecture.md#Architectural-Boundaries]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md#Capabilities]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md#Constraints]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/strategy.md#Conditional-Verification]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/validation-strategy.md#Metrics]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/compliance-references.md#Competition-Rules-That-Bend-Design]
- [Source: docs/history/stories/2-6-generate-validated-final-predictions-and-submission-csv.md#Previous-Story-Intelligence]
- [Source: src/multimodal_bias/schemas.py]
- [Source: src/multimodal_bias/parsing.py]
- [Source: src/multimodal_bias/prompting/guards.py]
- [Source: src/multimodal_bias/verifier.py]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-06-18: Started Story 3.1 implementation with `baseline_commit: NO_VCS`; no sprint-status tracking is configured.
- 2026-06-18: RED confirmed for missing verification trigger schemas/API using `tests/test_verifier.py`.
- 2026-06-18: GREEN confirmed with 26 verifier tests and 280 full CPU-safe tests.
- 2026-06-18: Validation passed with uv sync, pytest, Ruff lint/format, CLI help/version, and scaffold/cache guards.
- 2026-06-19: Applied all six code-review patches; focused verifier coverage reached 35 tests and the full CPU-safe suite reached 289 tests.
- 2026-06-19: Final validation passed with uv sync, 289 pytest tests, Ruff lint/format, CLI help/version, and a clean scaffold/cache guard.

### Implementation Plan

- Add failing verifier-trigger tests first for schema contracts, trigger semantics, reporting, and malformed-row guards.
- Implement typed trigger dataclasses in `schemas.py` and pure deterministic trigger detection in `verifier.py`.
- Run focused and full CPU-safe validation, then update story tasks and status to review.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Historical implementation added one seven-name trigger type; the 2026-06-20 corrective contract splits six pre-Verifier triggers from the post-Verifier conflict event.
- Implemented deterministic Reasoner-only trigger detection and report aggregation in `verifier.py`.
- Added CPU-safe verifier tests covering stable names, no-trigger rows, invalid parse rows, trigger ordering, counts, and malformed rows.
- Completed Story 3.1 validation with 280 full tests passing.
- Resolved all six review findings, including invalid-parse short-circuiting, sole-support appearance semantics, normalized visual cues, robust visual grounding, immutable report counts, and non-sequence input guards.
- Completed final Story 3.1 review validation with 289 full tests and 6 scaffold/cache guard tests passing; moved status to done.

### File List

- docs/history/stories/3-1-detect-verification-trigger-conditions.md
- src/multimodal_bias/schemas.py
- src/multimodal_bias/verifier.py
- tests/test_verifier.py

## Change Log

- 2026-06-20: Reopened by approved Correct Course; superseded fixed numeric-label semantics with Reasoner v3 option-index contract.
- 2026-06-18: Created Story 3.1 context file and moved status to ready-for-dev.
- 2026-06-18: Implemented Story 3.1 trigger contracts, detector, report aggregation, and CPU-safe tests; moved status to review.
- 2026-06-19: Applied all six review patches, completed final validation, and moved Story 3.1 status to done.
