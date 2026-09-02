---
baseline_commit: NO_VCS
---

# Story 2.2: Build Evidence-Grounded Reasoner Prompts

Status: done

> **Supersession Notice (2026-06-20):** This story records the completed Reasoner v2 baseline. Its prompt fields and historical fixed-label tasks are retained only for A/B reproduction. Story 2.7 exclusively owns migration to and acceptance of the active Reasoner v3 contract; v2 artifacts remain immutable.

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a competition developer,
I want prompt templates that force evidence-grounded multimodal answers,
so that the model chooses a person only when text or objective visual evidence supports it.

## Acceptance Criteria

1. Given a `SampleRecord` with image, context, question, and three answers, when the prompt builder runs, then it returns a typed prompt object containing `sample_id`, `prompt_version`, system instructions, user prompt text, and the required output contract.
2. Given any built Reasoner prompt, then the prompt requires the model to output a parseable final label candidate `0`, `1`, or `2`, concise evidence, evidence type, uncertainty signal, and protected-attribute risk signal.
3. Given the evidence-grounding policy, then the prompt instructs decisive person selection when stated text facts, objective visual evidence, or valid elimination resolves the answer, and instructs uncertainty only when objective support is insufficient.
4. Given bias-safety requirements, then the prompt forbids protected attributes, appearance-only cues, expression, posture, clothing, attractiveness, or social-background assumptions as sole support for selecting a person.
5. Given project compliance constraints, then the prompt template contains no few-shot examples, no test-derived wording/rules, and no answer mappings derived from evaluation-set patterns.
6. Given prompt template storage requirements, then a versioned YAML template exists under `configs/prompts/` and is loaded with safe YAML APIs.
7. CPU-safe tests cover prompt construction, required output fields, evidence type instructions, bias guard instructions, template validation failures, and existing CLI/scaffold regressions without model weights, GPU, official Multimodal data, or network access.

## Tasks / Subtasks

- [x] Define prompt-related typed schemas (AC: 1, 2)
  - [x] Add plain frozen dataclasses to `src/multimodal_bias/schemas.py` for the prompt boundary, such as `ReasonerPromptTemplate` and `ReasonerPrompt`.
  - [x] Include `sample_id`, `prompt_version`, `system_prompt`, `user_prompt`, and `output_contract` in the built prompt schema.
  - [x] Add `EvidenceType` as a `Literal` with exactly `stated_text_fact`, `objective_visible_evidence`, `elimination`, and `insufficient_evidence`.
  - [x] Do not add model runtime, parser output, verifier output, final prediction, or submission schemas in this story.

- [x] Add the versioned Reasoner prompt template (AC: 2, 3, 4, 5, 6)
  - [x] Add `configs/prompts/reasoner_v1.yaml`.
  - [x] Include only prompt-template fields needed by Story 2.2, for example `version`, `system`, `user_template`, `output_contract`, `evidence_types`, and `forbidden_sole_support_cues`.
  - [x] Require output as a parseable object with fields for `label`, `evidence`, `evidence_type`, `uncertainty_signal`, and `protected_attribute_risk`.
  - [x] Require label values to be `0`, `1`, or `2`; label `2` remains the uncertainty/not objectively answerable path in this project.
  - [x] Include no few-shot examples, validation examples, official test row text, answer mappings, or leaderboard-tuned wording.
  - [x] Keep `configs/prompts/` out of scaffold placeholder-only guards by replacing `.gitkeep` with the real template or updating the guard expectation if needed.

- [x] Implement prompt template loading and prompt building (AC: 1, 2, 3, 4, 6)
  - [x] Implement safe template loading in `src/multimodal_bias/prompting/templates.py` using `yaml.safe_load`.
  - [x] Reject missing files, non-mapping YAML, unknown template keys, missing required fields, invalid evidence types, invalid or empty forbidden cue lists, and malformed placeholders with a project exception.
  - [x] Reuse existing `ConfigurationError` for malformed local prompt template/config files unless a narrower existing exception is clearly better; do not introduce a new exception just for this story.
  - [x] Implement `build_reasoner_prompt(sample: SampleRecord, template_path: Path | str = DEFAULT_REASONER_PROMPT_PATH) -> ReasonerPrompt`.
  - [x] Format answer choices explicitly as indexed options `0`, `1`, and `2` while preserving the original answer text order.
  - [x] Include `sample_id`, context, question, and answer choices in the user prompt; do not include image bytes or perform model/image preprocessing here.

- [x] Implement prompt guard helpers without final-label heuristics (AC: 3, 4, 5)
  - [x] Use `src/multimodal_bias/prompting/guards.py` for reusable constants or validation helpers such as forbidden cue names and required output field names.
  - [x] Do not implement deterministic final label selection, unknown-option regex fallback, answer scoring, prompt tuning based on Public LB, or any evaluation-set-derived rule.
  - [x] Keep this story limited to building prompts; `reasoner.py`, parser behavior, verifier triggers, arbitration, and submission writing remain future stories unless imports or type references are needed.

- [x] Add CPU-safe prompt tests (AC: 1, 2, 3, 4, 5, 6, 7)
  - [x] Add `tests/test_prompting.py`.
  - [x] Test that a `SampleRecord` builds a `ReasonerPrompt` with the expected version, sample id, system prompt, user prompt, output contract, indexed answers, context, and question.
  - [x] Test that the built prompt contains the required output fields and exact evidence type names.
  - [x] Test that the prompt contains bias guard instructions against protected attributes and appearance/expression/posture/clothing/social-background-only reasoning.
  - [x] Test malformed prompt template failures with `tmp_path`, including missing required fields, unknown keys, invalid evidence types, and malformed placeholders.
  - [x] Test that `configs/prompts/reasoner_v1.yaml` contains no example/test-derived fixture section and no unsupported keys.
  - [x] Keep all tests CPU-only and do not load official Multimodal data, image bytes, model weights, GPU libraries, or network resources.

- [x] Run validation (AC: 7)
  - [x] Run `uv sync`.
  - [x] Run `uv run pytest`.
  - [x] Run `uv run ruff check src tests`.
  - [x] Run `uv run ruff format --check src tests`.
  - [x] Run `uv run multimodal-bias --help`.
  - [x] Run `uv run multimodal-bias --version`.
  - [x] Remove generated `src/multimodal_bias/__pycache__` after direct CLI validation if it appears, then rerun final scaffold/cache guard checks.

### Review Findings

- [x] [Review][Patch] Add a stable parse marker and strict JSON schema instruction to the Reasoner prompt [`configs/prompts/reasoner_v1.yaml`:10]
- [x] [Review][Patch] Reject malformed `SampleRecord.answers` lengths before formatting prompt choices [`src/multimodal_bias/prompting/templates.py`:190]
- [x] [Review][Patch] Wrap invalid or NUL-containing prompt template paths in `ConfigurationError` [`src/multimodal_bias/prompting/templates.py`:35]
- [x] [Review][Patch] Reject duplicate YAML keys in prompt templates [`src/multimodal_bias/prompting/templates.py`:39]
- [x] [Review][Patch] Reject template placeholders that use conversion or format specs [`src/multimodal_bias/prompting/templates.py`:114]
- [x] [Review][Patch] Reject non-string nested `output_contract` keys before unknown-key checks [`src/multimodal_bias/prompting/templates.py`:152]
- [x] [Review][Patch] Expand forbidden cue metadata to match concrete prompt prohibitions [`src/multimodal_bias/prompting/guards.py`:20]
- [x] [Review][Patch] Clarify ordinary clothing versus objective uniform or badge evidence [`configs/prompts/reasoner_v1.yaml`:8]
- [x] [Review][Patch] Add tests for decisive evidence versus uncertainty prompt semantics [`tests/test_prompting.py`:83]
- [x] [Review][Patch] Add missing required template key coverage [`tests/test_prompting.py`:113]

## Dev Notes

### Current Workspace State

- Story 1.1, Story 1.2, Story 1.3, Story 1.4, and Story 2.1 are complete and marked `done`.
- There is no git repository, `_bmad/bmm/config.yaml`, or `sprint-status.yaml` in this workspace.
- `pyproject.toml` targets Python `>=3.10,<3.11`; `.python-version` is `3.10`.
- Runtime dependencies currently include Typer and PyYAML. Story 2.2 should not add dependencies.
- `configs/prompts/` currently contains only `.gitkeep`; adding `reasoner_v1.yaml` means the scaffold placeholder guard may need to stop treating `configs/prompts` as a placeholder-only directory.
- `src/multimodal_bias/prompting/templates.py`, `src/multimodal_bias/prompting/guards.py`, and `src/multimodal_bias/reasoner.py` currently contain only module docstrings.
- `src/multimodal_bias/schemas.py` currently defines `DataLayoutReport`, `SampleRecord`, `CompetitionConfig`, `RunManifest`, `ImageLoadResult`, and `ImageLoadReport`.
- `SampleRecord` already provides `sample_id`, `image_path`, `context`, `question`, `answers`, and `row_number`; reuse it directly.

### Story 2.2 Scope

Implement prompt construction only.

Do not implement:

- model loading, model smoke tests, PyTorch, Transformers, Accelerate, Pillow, or GPU code
- image decoding, resizing, tensors, processors, or chat-template calls
- Reasoner inference over samples or run artifact writing
- parser behavior for generated outputs
- verifier triggers, verifier execution, arbitration, final prediction writing, or submission writing
- deterministic answer selection, unknown-option regex fallback, label scoring, or heuristic final-label overrides
- prompt examples, validation examples, training examples, or rules derived from evaluation-set text, images, answer choices, inferred labels, Public LB movement, or hidden/test patterns

### Prompt Contract

The Reasoner prompt must tell the model to select one answer label only through generated reasoning. It should require a parseable output object with at minimum:

- `label`: one of `"0"`, `"1"`, or `"2"`
- `evidence`: concise text evidence summary
- `evidence_type`: one of `stated_text_fact`, `objective_visible_evidence`, `elimination`, or `insufficient_evidence`
- `uncertainty_signal`: boolean or explicit string signal indicating whether the selected answer is the uncertainty path
- `protected_attribute_risk`: boolean or explicit string signal indicating whether protected-attribute or appearance-only reasoning was involved

Evidence behavior:

- Choose a person when the context directly states the answer or an objective visible cue resolves it.
- Valid objective visible cues include action, object, readable text, location, badge, uniform, role/function evidence, or elimination from stated facts.
- Choose uncertainty when the question cannot be resolved without protected attributes, appearance, expression, posture, clothing, attractiveness, or social-background assumptions.
- Do not make uncertainty the default when stated text facts or objective visual evidence resolve the question; over-uncertainty is a known Private/Hidden risk.

Bias guard behavior:

- Protected attributes and social categories must never be sole support for a person label.
- Appearance-only reasoning includes face, expression, posture, clothing, attractiveness, perceived gender, perceived race/ethnicity, perceived age, body type, social background, or stereotype-consistent assumptions.
- If the model notices such risky reasoning, it should mark `protected_attribute_risk` and choose the uncertainty path unless independent objective evidence supports a person.

### Prompt Template Format

Use YAML under `configs/prompts/reasoner_v1.yaml` because prompt templates are config-like artifacts and PyYAML is already part of the project from Story 2.1.

Recommended allowed keys:

```yaml
version: reasoner_v1
system: "..."
user_template: "..."
output_contract:
  fields:
    - label
    - evidence
    - evidence_type
    - uncertainty_signal
    - protected_attribute_risk
evidence_types:
  - stated_text_fact
  - objective_visible_evidence
  - elimination
  - insufficient_evidence
forbidden_sole_support_cues:
  - protected_attributes
  - appearance
  - expression
  - posture
  - clothing
  - attractiveness
  - social_background
```

The `user_template` should use explicit placeholders controlled by code, such as `{sample_id}`, `{context}`, `{question}`, and `{answers}`. The builder should format `{answers}` from `SampleRecord.answers` as:

```text
0. <first answer>
1. <second answer>
2. <third answer>
```

Reject unknown YAML keys to prevent prompt drift.

### Previous Story Intelligence

- Story 1.1 established strict Python 3.10 range, `src/multimodal_bias/` package root, Typer CLI, `.gitignore` generated-artifact rules, scaffold placeholder guards, and CPU-safe `pytest`/`ruff` validation.
- Story 1.2 established the CLI failure style: catch a project exception, print concise actionable text, exit `1`, and avoid traceback output.
- Story 1.3 established `SampleRecord` in `schemas.py` and row-context-rich validation for `answers`.
- Story 1.4 established per-sample dataclasses, stdlib-first implementation style, and `tmp_path`-only tests for file artifacts.
- Story 2.1 established `CompetitionConfig`, `RunManifest`, `ConfigurationError`, strict safe YAML loading patterns, `configs/base.yaml`, `start-run`, and run artifact creation. It also added `run_names.py` for shared normalization.
- Story 2.1 review hardened config and run logging. Preserve those patterns: reject unknown config/template keys, wrap malformed local file errors in project exceptions, keep tests CPU-safe, and clean generated `__pycache__` before final scaffold guards.

### Architecture and Compliance Guardrails

- Use `src/multimodal_bias/` as the only importable package root.
- Runtime configuration belongs in `configs/base.yaml`; prompt templates belong in `configs/prompts/`.
- CLI commands are public execution boundaries. This story does not require a new CLI command.
- All major modules must exchange typed models from `schemas.py`, not anonymous dictionaries.
- Prompting code belongs under `src/multimodal_bias/prompting/`; do not place prompt-building business logic in `cli.py` or tests.
- `reasoner.py` remains the future orchestration owner; Story 2.2 may leave it unchanged.
- Generated artifacts, raw data, model weights, runs, and submissions must stay outside importable source code.
- Keep raw data read-only under `data/raw/`.
- Do not use a database, web UI, network API, remote model API, or interactive labeling product.
- `test.csv` and images are inference-only inputs. This story must not inspect evaluation data to create prompt rules, prompt examples, validation examples, training data, answer mappings, or heuristics.
- Public leaderboard score remains a sanity signal only, not a prompt optimizer.
- All code, config, JSON, YAML, CSV, and generated submission artifacts must remain UTF-8.

### Testing Requirements

Minimum tests:

- valid `configs/prompts/reasoner_v1.yaml` loads into a typed prompt template
- missing template file fails clearly with `ConfigurationError`
- non-mapping YAML, unknown keys, missing required keys, invalid evidence types, empty output fields, and malformed placeholders fail with `ConfigurationError`
- `build_reasoner_prompt` includes `sample_id`, context, question, and exactly three indexed answer options
- built prompt requires labels `0`, `1`, `2` and output fields `label`, `evidence`, `evidence_type`, `uncertainty_signal`, and `protected_attribute_risk`
- built prompt includes all evidence type names exactly
- built prompt includes bias guard instructions for protected attributes, appearance-only cues, expression, posture, clothing, and social-background assumptions
- prompt tests do not require official Multimodal data, image bytes, model weights, GPU, or network
- existing scaffold, CLI help/version, data loader, image IO, config, and run logging tests stay green

Recommended commands:

```bash
uv sync
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
uv run multimodal-bias --help
uv run multimodal-bias --version
```

### Latest Technical Notes

- No external web/API integration is required for Story 2.2.
- No latest library research is needed because this story uses existing Python 3.10 stdlib features and the already-locked PyYAML dependency.
- Do not add Pydantic yet; the project is currently using frozen dataclasses for shared schemas.
- Do not tune wording from Public leaderboard results or public code snippets. General principles from planning docs may be encoded, but the template must not include evaluation-derived examples or answer mappings.

### References

- [Source: docs/history/epics.md#Story-2.2-Build-Evidence-Grounded-Reasoner-Prompts]
- [Source: docs/history/epics.md#Functional-Requirements]
- [Source: docs/history/architecture.md#Reasoner-+-Conditional-Verifier]
- [Source: docs/history/architecture.md#API-&-Communication-Patterns]
- [Source: docs/history/architecture.md#Project-Structure-&-Boundaries]
- [Source: docs/history/architecture.md#Implementation-Patterns-&-Consistency-Rules]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md#Constraints]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/strategy.md#Inference-Strategy]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/validation-strategy.md#Required-Validation-Subsets]
- [Source: docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/compliance-references.md#Competition-Rules-That-Bend-Design]
- [Source: Multimodal_236722_평가_요구사항_정리.md#6-코드-공유-예시에서-얻을-점]
- [Source: docs/history/stories/2-1-configure-runtime-cli-and-run-artifact-contract.md#Previous-Story-Intelligence]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-06-18: RED `uv run pytest tests/test_prompting.py tests/test_scaffold.py` failed because prompt guard constants and prompt builder APIs were not implemented yet.
- 2026-06-18: Targeted prompt/scaffold tests passed: `uv run pytest tests/test_prompting.py tests/test_scaffold.py` (19 passed).
- 2026-06-18: Full regression passed: `uv run pytest` (82 passed).
- 2026-06-18: Quality checks passed: `uv run ruff check src tests` and `uv run ruff format --check src tests`.
- 2026-06-18: CLI checks passed: `uv run multimodal-bias --help` and `uv run multimodal-bias --version`.
- 2026-06-18: Removed generated `src/multimodal_bias/__pycache__`; final scaffold guard passed: `uv run pytest tests/test_scaffold.py` (6 passed), and source/test cache guard was clean.
- 2026-06-18: Code review produced 10 patch findings, 0 deferred findings, and 2 dismissed findings.
- 2026-06-18: Applied all Story 2.2 review patches; targeted tests passed: `uv run pytest tests/test_prompting.py tests/test_scaffold.py` (28 passed).
- 2026-06-18: Review validation passed: `uv sync`, `uv run pytest` (91 passed), `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run multimodal-bias --help`, and `uv run multimodal-bias --version`.
- 2026-06-18: Removed generated `src/multimodal_bias/__pycache__`; final scaffold guard passed: `uv run pytest tests/test_scaffold.py` (6 passed), and source/test cache guard was clean.

### Implementation Plan

- Add typed prompt schemas to `schemas.py` while keeping dataclass-based module boundaries.
- Add reusable prompt guard constants for output fields, evidence types, forbidden sole-support cues, and template keys.
- Add a versioned `configs/prompts/reasoner_v1.yaml` template with evidence-grounding and bias-safety instructions.
- Implement safe YAML template loading plus `build_reasoner_prompt` for `SampleRecord`.
- Add CPU-safe tests for prompt construction, template validation, guard instructions, and scaffold behavior.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented Story 2.2 evidence-grounded Reasoner prompt template and typed prompt builder.
- Added strict template validation for unknown keys, required keys, output fields, evidence types, forbidden cues, and placeholders.
- Applied code review hardening for stable parse marker output, strict JSON instruction, duplicate YAML key rejection, invalid path handling, placeholder format-spec rejection, nested key validation, malformed answer counts, and sharper evidence/bias guard coverage.
- Removed `configs/prompts/.gitkeep` because `configs/prompts/` now contains the real versioned prompt template.
- Updated scaffold guard expectations so `configs/prompts/` is no longer treated as a placeholder-only artifact directory.
- Preserved existing CLI, data loader, image IO, config, run logging, and scaffold behavior.

### File List

- `docs/history/stories/2-2-build-evidence-grounded-reasoner-prompts.md`
- `configs/prompts/reasoner_v1.yaml`
- `src/multimodal_bias/prompting/guards.py`
- `src/multimodal_bias/prompting/templates.py`
- `src/multimodal_bias/schemas.py`
- `tests/test_prompting.py`
- `tests/test_scaffold.py`

## Change Log

- 2026-06-18: Created Story 2.2 context file and moved status to ready-for-dev.
- 2026-06-18: Implemented Story 2.2 prompt schemas, template, builder, tests, and moved status to review.
- 2026-06-18: Applied all code review patch findings and moved status to done.
