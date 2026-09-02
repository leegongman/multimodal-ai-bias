---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md
  - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/strategy.md
  - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/validation-strategy.md
  - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/compliance-references.md
  - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/architecture-diagrams.md
  - docs/history/research/technical-multimodal-236722-multimodal-ai-bias-research-2026-06-18.md
  - Multimodal_236722_평가_요구사항_정리.md
  - docs/history/architecture.md
  - _bmad-output/specs/spec-reasoner-v3-contract/SPEC.md
  - _bmad-output/specs/spec-shadow-private-validation/SPEC.md
  - docs/history/research/technical-multimodal-236722-vlm-model-tournament-research-2026-06-20.md
  - docs/history/sprint-change-proposal-2026-06-20.md
  - docs/history/implementation-readiness-report-2026-06-20.md
  - docs/history/sprint-change-proposal-ir-remediation-2026-06-20.md
workflowType: 'epics-and-stories'
project_name: 'Multimodal 236722 Multimodal AI Bias Solution'
user_name: 'gongman'
date: '2026-06-18'
lastStep: 4
status: 'complete'
completedAt: '2026-06-18'
correctedAt: '2026-06-20'
---

# Multimodal 236722 Multimodal AI Bias Solution - Epic Breakdown

> **HUMAN-OWNED EXECUTION LOCK:** 현재는 Qwen2.5-VL-7B Reasoner v3 재제출 경로만 활성화한다. Story 2.9·2.10과 Epic 3·4·5 전체는 미래 작업으로 동결하며, 사용자가 정확한 대상을 명시적으로 승인하기 전에는 생성·검증·구현·리뷰·수정·실행하지 않는다. 로드맵상의 순서는 승인으로 간주하지 않는다. 전체 규칙은 [`../AGENTS.md`](../AGENTS.md)를 따른다.

## Overview

This document provides the complete epic and story breakdown for Multimodal 236722 Multimodal AI Bias Solution, decomposing the requirements from the SPEC, Architecture requirements, strategy, validation strategy, compliance references, technical research, and Multimodal requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: The system must ingest the official Multimodal `open.zip` structure under `data/raw/open/`, including `train/`, `test/`, image folders, `test.csv`, and `sample_submission.csv`.

FR2: The system must validate the competition data layout and fail clearly when required files, columns, image paths, or answer fields are missing or malformed.

FR3: The system must parse `test.csv` rows into typed sample records containing `sample_id`, `image_path`, `context`, `question`, and the three-choice `answers` JSON string.

FR4: The system must load and preprocess sample images for local multimodal inference while logging image-load success or failure per sample.

FR5: The system must build evidence-grounded prompts from image, context, question, and answers, requiring decisive person selection when text or objective visual evidence resolves the question and uncertainty selection when evidence is insufficient.

FR6: The system must run a local open-source VLM Reasoner for every prediction sample through a model adapter interface, preserving raw generated model text and generation metadata.

FR7: The Reasoner output must generate a parseable selected answer-choice index and `uncertainty_option_index`, concise evidence, evidence type, uncertainty signal, protected-attribute risk signal, and schema version; no numeric label has inherent semantic meaning.

FR8: The system must parse generated Reasoner text into validated structured outputs without relying on model-specific phrasing beyond the approved final-answer marker or schema.

FR9: The system must trigger conditional verification only from Reasoner-derived risky states, including invalid parse, low confidence, unsupported evidence, protected-attribute risk, appearance-only reasoning, or ambiguous visual grounding. Reasoner-verifier conflict is a post-Verifier comparison event, not an initial trigger.

FR10: The system must run a Verifier only for triggered samples, preserve raw verifier output, parse its label and reasoning, and log trigger category and before/after labels.

FR11: The system must arbitrate only between valid Reasoner and Verifier generated candidates, keeping the Reasoner when no concrete defect is found and flipping only with stronger verifier evidence. If evidence is insufficient, only a valid stage-generated uncertainty-choice index may be selected; if neither stage has a valid candidate, the sample is unresolved and submission is blocked.

FR12: The system must generate `final_predictions.csv` and a Multimodal-ready UTF-8 `submission.csv` containing exactly `sample_id,label` with labels restricted to `0`, `1`, and `2`.

FR13: The system must ensure `submission.csv` is written only by the submission command and only from validated `final_predictions.csv`.

FR14: The system must create immutable per-run artifacts under `runs/{run_id}/`, including resolved config, environment record, raw reasoner JSONL, parsed reasoner CSV, verification JSONL, final predictions, submission CSV, metrics, and compliance manifest.

FR15: The system must provide CLI commands for `validate-data`, `smoke-model`, `infer`, `verify-risky`, `make-submission`, `audit-run`, `compare-runs`, and `check-gpu-readiness`.

FR16: The system must implement local validation reporting for ambiguous/resolvable accuracy, local balanced accuracy, worst-subset accuracy, uncertainty-position accuracy, semantic consistency, over-uncertainty, unsupported person selection, verifier beneficial/harmful/no-effect flips, parse/image/unresolved failures, peak VRAM, and full-path runtime.

FR17: The system must support a separate diagnostic-48 and an independently sourced, reviewed, hashed and frozen 300–600 sample Shadow Private suite with selection/sealed-holdout splits, balanced uncertainty positions, provenance, and the required subset labels.

FR18: The system must integrate eligible local VLM candidates through official multimodal paths and compare staged tournament runs using frozen Shadow Private, runtime/memory feasibility, compliance, failure rates, raw audit evidence, Verifier impact, and Public score only as a secondary sanity signal.

FR19: The system must generate a compliance manifest for each candidate run covering model name, revision/checkpoint, release cutoff evidence, license, source URL, remote API usage, external data provenance, inference command, environment record, and selected submission file.

FR20: The system must support second-round readiness with separated train/inference code, version records, model/data references, raw inference logs, reproducible run metadata, and solution artifact preparation inputs.

FR21: Before 8,500-row production, the system must evaluate the ten stable GPU submission-readiness gates, publish `GPU_SUBMISSION_READY` only on 10/10, suppress production on any blocker, and explicitly notify the operator with the selected candidate, command, expected runtime, and evidence artifact.

### NonFunctional Requirements

NFR1: Competition code must be Python and target Python 3.10.

NFR2: The target reference environment is RTX A6000 48GB, CUDA 12.4, PyTorch 2.6.0, and Ubuntu 20.04.

NFR3: All model inference must run locally or on participant-controlled infrastructure without OpenAI API, Gemini API, Hugging Face Inference API, Together AI, OpenRouter, or any other remote model API.

NFR4: Only open-source model weights officially public by 2026-05-31 may be used.

NFR5: Final label decisions must be derived from generated LLM text, not pure rules, pure majority vote, fixed answer lists, or deterministic post-hoc mappings.

NFR6: Evaluation data must be inference-only; training data, prompt templates, rules, examples, or validation examples must not be derived from evaluation-set question types, choice patterns, wording, constructions, images, or inferred answers.

NFR7: Final inference should remain practical against organizer guidance: about 0.5 seconds/sample, about 70 minutes for 8,500 test samples, and about 13 minutes for 1,500 Hidden samples unless slower inference is explicitly justified and validated.

NFR8: Public leaderboard score must not be the sole criterion for model, prompt, threshold, or submission selection.

NFR9: All CSV files, code comments, and generated submission artifacts must use UTF-8.

NFR10: The system must be reproducible through locked dependencies, pinned model revisions or local snapshot hashes, resolved config files, environment records, and immutable run outputs.

NFR11: The system must be auditable: raw model text, parsed labels, verifier activity, arbitration decisions, risk flags, failure states, and compliance evidence must be preserved.

NFR12: The implementation must avoid a database, web UI, network API, or interactive labeling product unless the architecture is explicitly revised.

NFR13: CPU-safe automated tests must cover parsing, schema validation, label constraints, run artifact creation, compliance manifest generation, and submission CSV formatting.

NFR14: GPU smoke/integration checks must be explicit commands and must not be required for normal CPU unit test execution.

NFR15: Generated artifacts, model weights, raw data, runs, and submissions must stay outside importable source code.

### Additional Requirements

- Use `uv init --package --python 3.10 --name multimodal-bias --vcs none .` as the starter initialization for Epic 1 Story 1.
- Use a packaged `src/multimodal_bias/` layout as the only importable package root.
- Use `pyproject.toml`, `.python-version`, `uv.lock`, `uv sync`, and `uv run` for reproducible environment and command execution.
- Add `pytest` for CPU-safe unit tests and `ruff` for linting/formatting.
- Use Typer for repeatable CLI command entrypoints.
- Use Pydantic models or plain dataclasses from `schemas.py` for module boundaries; do not pass anonymous dictionaries across Reasoner, Verifier, arbitration, and submission layers.
- Define required schemas/classes: `CompetitionConfig`, `SampleRecord`, `ReasonerOutput`, `VerifierOutput`, `FinalPrediction`, `RunManifest`, `ComplianceManifest`, and `VisionLanguageModelAdapter`.
- Define required exception classes: `DataLayoutError`, `ModelLoadError`, `InferenceError`, `ParseError`, `ComplianceError`, and `SubmissionFormatError`.
- Implement required modules: `cli.py`, `config.py`, `schemas.py`, `exceptions.py`, `data_loader.py`, `image_io.py`, `parsing.py`, `reasoner.py`, `verifier.py`, `arbitration.py`, `validation.py`, `compliance.py`, `submission.py`, `run_logging.py`, `run_comparison.py`, `readiness.py`, `prompting/`, and `models/`.
- Add `src/multimodal_bias/run_comparison.py` as the owner module for `compare-runs` behavior.
- Keep raw data read-only under `data/raw/`; store derived artifacts under `data/processed/`, `runs/`, and `submissions/`.
- Use top-level artifact folders: `configs/`, `data/raw/`, `data/processed/`, `models/`, `runs/`, `submissions/`, and `tests/`.
- Store model snapshots or symlinks under `models/snapshots/` and record snapshot revision/hash for final runs.
- Keep runtime configuration in `configs/base.yaml`, model-specific configuration in `configs/models/`, and prompt templates in `configs/prompts/`.
- Use local filesystem and local model snapshots only; no network API integration is part of the architecture.
- Every inference log row must include `run_id`, `sample_id`, `stage`, `status`, and `message`.
- Stable pre-Verifier trigger names must be `invalid_parse`, `low_confidence`, `unsupported_evidence`, `protected_attribute_risk`, `appearance_only_reasoning`, and `ambiguous_visual_grounding`.
- `reasoner_verifier_conflict` is a post-Verifier comparison event emitted only after both candidates are parsed; it must never invoke an otherwise untriggered Verifier pass.
- Recoverable per-sample failures must be logged without creating a label; if no valid generated candidate survives, the sample is unresolved and submission generation fails closed.
- The model adapter must expose raw text and generation metadata while hiding model-specific loading details from business logic.
- The parser must not depend on one model's idiosyncratic output quirks beyond the agreed parse marker/schema.
- Candidate model screening order must be eligibility, license safety, offline loadability, A6000 memory fit, full-test runtime feasibility, local robust validation, then Public score sanity check.
- Tournament candidates are the corrected Qwen2.5-VL-7B control, MiniCPM-V 4.5 and LLaVA-OneVision 7B challengers, InternVL3-14B performance candidate, and conditional Qwen2.5-VL-32B-AWQ.
- Full production may start only after the ten GPU readiness gates pass and the user is explicitly notified with `GPU_SUBMISSION_READY`.
- Stable GPU readiness gate IDs are `target_environment`, `model_snapshot_license`, `data_image_validation`, `prompt_schema_identity`, `real_image_structured_output`, `diagnostic_blockers`, `vram_runtime_projection`, `atomic_artifact_persistence`, `final_submission_validation`, and `network_disabled_smoke`.
- Independent validation data may be public, self-authored, synthetic, or generated with allowed tools only when not derived from evaluation-set patterns.
- Daily Multimodal submission limit is 5; Public submissions should be milestone checks rather than iterative prompt tuning loops.
- Second-round artifact readiness must include separated train and inference code, `.py` or `.ipynb` code files, model acquisition path or model files, all external data files used, UTF-8 code/comments, environment versions, solution PDF inputs, and student-status evidence inputs.

### UX Design Requirements

No UX Design document exists for this project, and the architecture explicitly defines this as an offline CLI competition pipeline with no web UI, dashboard, or interactive labeling product. Therefore no UX-DR items apply.

### FR Coverage Map

FR1: Epic 1 - Official `open.zip` ingestion
FR2: Epic 1 - Data layout and field validation
FR3: Epic 1 - Typed `test.csv` and `answers` parsing
FR4: Epic 1 - Image loading/preprocessing status tracking
FR5: Epic 2 - Evidence-grounded prompt construction
FR6: Epic 2 - Local VLM Reasoner execution
FR7: Epic 2 - Structured Reasoner output contract
FR8: Epic 2 - Robust generated-output parsing
FR9: Epic 3 - Conditional verification triggers
FR10: Epic 3 - Verifier execution and logging
FR11: Epic 3 - Final label arbitration
FR12: Epic 2 - Final predictions and Multimodal submission CSV
FR13: Epic 2 - Submission safety boundary
FR14: Epic 2 - Immutable run artifact creation
FR15: Epic 2 - CLI command surface
FR16: Epic 4 - Local validation metrics
FR17: Epic 4 - Validation subset support
FR18: Epic 4 - Candidate run comparison and promotion
FR19: Epic 5 - Compliance manifest
FR20: Epic 5 - Second-round reproducibility readiness
FR21: Epic 5 - GPU submission readiness and operator notification

## Epic List

### Epic 1: Reproducible Data-Ready Competition Workspace
User can initialize the Python project, load the official Multimodal data layout, validate all inputs, and run CPU-safe checks before model inference.
**FRs covered:** FR1, FR2, FR3, FR4

### Epic 2: Offline Evidence-Grounded Submission Pipeline
User can run a local VLM Reasoner, parse generated answers, preserve raw outputs, and produce a valid Multimodal `sample_id,label` submission through the approved CLI path.
**FRs covered:** FR5, FR6, FR7, FR8, FR12, FR13, FR14, FR15

### Epic 3: Bias-Safe Conditional Verification and Arbitration
User can detect risky predictions, run conditional verification, arbitrate final labels safely, and audit every verifier trigger or flip.
**FRs covered:** FR9, FR10, FR11

### Epic 4: Private-Generalization Validation and Candidate Selection
User can evaluate candidates on local robust validation subsets, compare runs, and select a candidate for final compliance/readiness by Private/Hidden generalization evidence rather than Public LB alone.
**FRs covered:** FR16, FR17, FR18

### Epic 5: Compliance and Second-Round Reproducibility Package
User can prove competition-rule compliance and prepare the artifact set needed for code verification, Hidden evaluation, and second-round review.
**FRs covered:** FR19, FR20, FR21

## Epic 1: Reproducible Data-Ready Competition Workspace

User can initialize the Python project, load the official Multimodal data layout, validate all inputs, and run CPU-safe checks before model inference.

### Story 1.1: Set Up Initial Project From Starter Template

**Requirements:** FR1

As a competition developer,
I want a reproducible Python package scaffold,
So that all later inference and validation work runs through a consistent project structure.

**Acceptance Criteria:**

**Given** an empty or planning-only workspace
**When** the project scaffold is initialized
**Then** `pyproject.toml`, `.python-version`, `uv.lock`, `src/multimodal_bias/`, `configs/`, `data/`, `models/`, `runs/`, `submissions/`, and `tests/` exist
**And** the CLI package name is `multimodal-bias`
**And** the scaffold follows `uv init --package --python 3.10 --name multimodal-bias --vcs none .`
**And** CPU-safe tooling for `pytest` and `ruff` is configured.

### Story 1.2: Validate Official Multimodal Data Layout

**Requirements:** FR1, FR2

As a competition developer,
I want to validate the extracted `open.zip` layout,
So that malformed or incomplete competition data fails before inference.

**Acceptance Criteria:**

**Given** a configured `data/raw/open/` path
**When** `validate-data` runs
**Then** it checks required train/test folders, image folders, `test.csv`, and `sample_submission.csv`
**And** it verifies required CSV columns and UTF-8 readability
**And** missing files, columns, or malformed paths raise `DataLayoutError`.

### Story 1.3: Parse Test Rows Into Typed Sample Records

**Requirements:** FR3

As a competition developer,
I want each `test.csv` row parsed into a typed sample object,
So that prompt building and inference never depend on raw ad hoc dictionaries.

**Acceptance Criteria:**

**Given** a valid `test.csv` row
**When** the data loader parses it
**Then** it creates a `SampleRecord` with `sample_id`, `image_path`, `context`, `question`, and exactly three parsed answers
**And** malformed `answers` JSON or invalid answer count is reported with row context
**And** parsed records preserve original `sample_id` ordering.

### Story 1.4: Load Images With Per-Sample Status

**Requirements:** FR4

As a competition developer,
I want image loading and preprocessing to report per-sample status,
So that image failures are auditable and do not silently corrupt predictions.

**Acceptance Criteria:**

**Given** parsed sample records with image paths
**When** the image loader processes them
**Then** valid images are loaded into the format expected by the model adapter
**And** missing, unreadable, or corrupt images produce structured failure status with `sample_id` and path
**And** image-load failure counts are available for later run metrics.

## Epic 2: Offline Evidence-Grounded Submission Pipeline

User can run a local VLM Reasoner, parse generated answers, preserve raw outputs, and produce a valid Multimodal `sample_id,label` submission through the approved CLI path.

### Story 2.1: Configure Runtime CLI and Run Artifact Contract

**Requirements:** FR14, FR15

As a competition developer,
I want a CLI-driven runtime configuration and run directory contract,
So that every inference attempt creates reproducible and auditable artifacts.

**Acceptance Criteria:**

**Given** the project scaffold exists
**When** the CLI loads a config file and starts a run
**Then** it creates `runs/{run_id}/` with `config.resolved.yaml` and `environment.json`
**And** run IDs are stable, timestamped, and unique
**And** CLI commands are registered through `cli.py` without bypassing package boundaries.

### Story 2.2: Build Evidence-Grounded Reasoner Prompts

**Requirements:** FR5 (completed Reasoner v2 baseline; active v3 contract is owned by Story 2.7)

**Supersession Note:** This story records the completed Reasoner v2 baseline. Its prompt fields are historical A/B control behavior. Story 2.7 exclusively owns migration to and acceptance of the active Reasoner v3 contract; v2 artifacts remain immutable.

As a competition developer,
I want prompt templates that force evidence-grounded multimodal answers,
So that the model chooses a person only when text or objective visual evidence supports it.

**Acceptance Criteria:**

**Given** a `SampleRecord` with image, context, question, and answers
**When** the prompt builder runs
**Then** it produces a prompt requiring label `0`, `1`, or `2`, concise evidence, evidence type, uncertainty signal, and protected-attribute risk signal
**And** it instructs the model not to use protected attributes, appearance-only cues, expression, posture, clothing, or social-background assumptions as sole support
**And** prompt templates are versioned under `configs/prompts/`.

### Story 2.3: Implement Local VLM Model Adapter

**Requirements:** FR6

As a competition developer,
I want model execution hidden behind a local VLM adapter,
So that Reasoner logic does not depend on one model implementation.

**Acceptance Criteria:**

**Given** a configured local model snapshot path
**When** `smoke-model` runs
**Then** the adapter loads the model locally or raises `ModelLoadError` with actionable context
**And** it exposes raw generated text and generation metadata
**And** it records model name, revision or snapshot hash, and local load status for later audit.

### Story 2.4: Run Reasoner Inference and Preserve Raw Outputs

**Requirements:** FR6, FR14

As a competition developer,
I want Reasoner inference to process prediction samples and keep raw model text,
So that every final label remains traceable to generated LLM output.

**Acceptance Criteria:**

**Given** parsed samples and a working model adapter
**When** `infer` runs without verifier mode
**Then** it writes `raw_reasoner.jsonl` with `sample_id`, prompt version, raw output, generation metadata, timing, and status
**And** per-sample inference failures are logged with `InferenceError` context
**And** no final label is produced without a corresponding raw model output or logged failure path.

### Story 2.5: Parse Reasoner Outputs Into Structured Predictions

**Requirements:** FR8 (completed Reasoner v2 baseline; active v3 contract is owned by Story 2.7)

**Supersession Note:** This story records the completed Reasoner v2 parser baseline. Its parsed fields are historical A/B control behavior. Story 2.7 exclusively owns migration to and acceptance of the active Reasoner v3 contract; v2 artifacts remain immutable.

As a competition developer,
I want generated Reasoner text parsed into validated structured outputs,
So that downstream submission code consumes only checked labels and parse states.

**Acceptance Criteria:**

**Given** `raw_reasoner.jsonl`
**When** the parser runs
**Then** it writes `parsed_reasoner.csv` with `sample_id`, parsed label, evidence summary, evidence type, uncertainty flag, risk flags, and parse status
**And** labels outside `0`, `1`, `2` are rejected as invalid parse states
**And** parser behavior is covered by CPU-safe unit tests.

### Story 2.6: Generate Validated Final Predictions and Submission CSV

**Requirements:** FR12, FR13, FR15

As a competition developer,
I want final predictions and Multimodal submission files generated only through the approved submission command,
So that invalid or ad hoc submission files cannot be produced accidentally.

**Acceptance Criteria:**

**Given** validated parsed predictions for all required samples
**When** `make-submission` runs
**Then** it writes `final_predictions.csv` and `submission.csv` under the run directory
**And** `submission.csv` contains exactly UTF-8 columns `sample_id,label`
**And** labels are restricted to `0`, `1`, `2`
**And** sample count and ordering are checked against the official input before writing.

### Story 2.7: Implement Reasoner v3 Option-Index Contract

**Requirements:** FR5, FR7, FR8, FR12, FR14

As a competition developer,
I want Reasoner outputs to identify the selected answer and uncertainty answer positions independently,
So that every choice order is interpreted correctly and downstream stages never infer semantics from a number.

**Acceptance Criteria:**

**Given** any sample whose uncertainty option is at index 0, 1, or 2
**When** Reasoner v3 output is generated and parsed
**Then** strict `FINAL_ANSWER_JSON` contains `label`, integer `uncertainty_option_index`, evidence fields, risk fields, and `schema_version=reasoner_output_v3`
**And** `uncertainty_signal == (label == str(uncertainty_option_index))` and evidence-type consistency are enforced
**And** raw prompt/hash, image hash, raw output and parse errors remain auditable
**And** invalid output is not repaired with regex, fixed position, unknown phrase mapping, or fallback label
**And** Reasoner v2 remains unchanged for isolated A/B
**And** active config selects v3 only through a versioned prompt/schema pair
**And** v2 and v3 artifacts cannot be mixed in one run
**And** parsed Reasoner, Verifier input, arbitration and final lineage preserve `uncertainty_option_index` and `schema_version`
**And** position 0/1/2 parameterized tests and an identical-snapshot/image/engine/decoding diagnostic v2/v3 A/B pass.

### Story 2.8: Build Candidate Eligibility and Adapter Smoke Harness

**Requirements:** FR6, FR14, FR18, FR19

As a competition developer,
I want one eligibility and smoke-test contract for every tournament candidate,
So that ineligible or incorrectly serialized models are rejected before diagnostic evaluation.

**Acceptance Criteria:**

**Given** a tournament candidate
**When** its eligibility and adapter smoke run
**Then** official repo, exact commit, cutoff evidence, license, snapshot/custom-code hashes and remote API usage `none` are recorded
**And** the harness requires official processor/chat/image serialization evidence and preprocessing metadata
**And** a real-image Reasoner v3 smoke records load status, rendered-input evidence, latency and peak VRAM
**And** rejection reasons are machine-readable
**And** a candidate failing eligibility, offline load, official serialization evidence, valid structured output, or A6000 smoke cannot enter diagnostic-48.

### Story 2.9: Integrate MiniCPM-V 4.5 Candidate [FROZEN — FUTURE ONLY]

**Human-owned hold:** 현재 사용하지 않는다. 관련 Story, adapter, config, requirements, snapshot, runbook 및 실행 경로는 사용자가 Story 2.9 또는 MiniCPM-V 4.5를 명시적으로 해제할 때까지 읽기 전용으로 보존한다.

**Requirements:** FR6, FR14, FR18, FR19

As a competition developer,
I want MiniCPM-V 4.5 integrated through its official local multimodal path,
So that it can challenge the corrected Qwen control under the frozen contract.

**Acceptance Criteria:**

**Given** the common candidate harness
**When** MiniCPM-V 4.5 is integrated
**Then** its exact eligible revision, license, official processor/chat/image path and isolated dependency lock are recorded
**And** a real-image Reasoner v3 smoke preserves rendered-input evidence, raw output, latency and peak VRAM
**And** it enters diagnostic-48 only after all Story 2.8 gates pass.

### Story 2.10: Integrate LLaVA-OneVision 7B Candidate [FROZEN — FUTURE ONLY]

**Human-owned hold:** 현재 사용하지 않는다. 관련 Story, adapter, config, requirements, snapshot, runbook 및 실행 경로는 사용자가 Story 2.10 또는 LLaVA-OneVision을 명시적으로 해제할 때까지 읽기 전용으로 보존한다.

**Requirements:** FR6, FR14, FR18, FR19

As a competition developer,
I want LLaVA-OneVision 7B integrated through its official local multimodal path,
So that it can challenge the corrected Qwen control under the frozen contract.

**Acceptance Criteria:**

**Given** the common candidate harness
**When** LLaVA-OneVision 7B is integrated
**Then** its exact eligible revision, license, official processor/chat/image path and isolated dependency lock are recorded
**And** a real-image Reasoner v3 smoke preserves rendered-input evidence, raw output, latency and peak VRAM
**And** it enters diagnostic-48 only after all Story 2.8 gates pass.

## Epic 3: Bias-Safe Conditional Verification and Arbitration [FROZEN — FUTURE ONLY]

**Human-owned hold:** Epic 3 전체는 현재 사용하지 않는다. 사용자의 명시적 해제 전까지 CS/VS/DS/CR 또는 코드·설정·테스트 수정을 시작하지 않는다.

User can detect risky predictions, run conditional verification, arbitrate final labels safely, and audit every verifier trigger or flip.

### Story 3.1: Detect Verification Trigger Conditions

**Requirements:** FR9

As a competition developer,
I want risky Reasoner outputs to be classified into stable verification trigger categories,
So that only predictions needing review are sent to the Verifier.

**Acceptance Criteria:**

**Given** Reasoner v3 outputs with selected label, generated uncertainty index, evidence type, parse status, risk flags, and uncertainty signal
**When** trigger detection runs
**Then** it assigns zero or more pre-Verifier trigger names from `invalid_parse`, `low_confidence`, `unsupported_evidence`, `protected_attribute_risk`, `appearance_only_reasoning`, and `ambiguous_visual_grounding`
**And** non-risky valid predictions are not sent to the Verifier
**And** semantic consistency is evaluated without assigning inherent meaning to label 0, 1, or 2
**And** invalid rows create triggers but never fallback labels
**And** `reasoner_verifier_conflict` is unavailable at this stage and cannot trigger a Verifier pass
**And** trigger logic does not use hidden/test-derived prompt rules or answer mappings.

### Story 3.2: Run Conditional Verifier for Triggered Samples

**Requirements:** FR10

As a competition developer,
I want the Verifier to independently review only triggered samples,
So that risky predictions can be corrected without turning the pipeline into an expensive unconditional two-pass system.

**Acceptance Criteria:**

**Given** a set of triggered samples and their Reasoner outputs
**When** `verify-risky` runs
**Then** it generates verifier outputs only for triggered samples
**And** the Verifier independently generates its own selected label, integer `uncertainty_option_index`, evidence fields and semantic signals using the same invariant as Reasoner v3
**And** it writes `verification.jsonl` with schema version, `sample_id`, trigger categories, raw verifier output, parsed verifier candidate and uncertainty index, reason, before/after lineage, and status
**And** malformed output remains invalid with no invented candidate
**And** after parsing it emits `reasoner_verifier_conflict` only when both candidates are valid and their selected indexes differ
**And** no-conflict, one-invalid and both-invalid comparison states remain distinct
**And** the conflict event never causes an otherwise untriggered Verifier pass
**And** skipped samples are traceable as non-triggered rather than silently omitted.

### Story 3.3: Arbitrate Final Labels With Evidence Preservation

**Requirements:** FR11

As a competition developer,
I want final labels selected through explicit arbitration rules,
So that verifier changes are justified by stronger evidence and not deterministic post-hoc mapping.

**Acceptance Criteria:**

**Given** Reasoner and optional Verifier outputs for a sample
**When** arbitration runs
**Then** it keeps the Reasoner label when the Verifier finds no concrete defect
**And** it flips only to a valid Verifier-generated label when the Verifier provides stronger objective support or a valid generated uncertainty choice
**And** it never infers semantics from a numeric label or invents a label
**And** if neither stage supplies a valid generated candidate, it records `unresolved` and blocks final prediction/submission publication
**And** every final prediction records the arbitration reason, source stage, schema version and option-index lineage.

### Story 3.4: Audit Verification Impact and Failure Modes

**Requirements:** FR10, FR11

As a competition developer,
I want verification behavior summarized per run,
So that I can see whether conditional verification improves robustness or introduces harmful flips.

**Acceptance Criteria:**

**Given** a completed run with Reasoner, Verifier, and arbitration artifacts
**When** the audit command runs
**Then** it reports trigger counts, conflict counts, keep/flip counts, protected-attribute risk, appearance-only reasoning, semantic failures, invalid parse recovery, unresolved, and label distribution before/after verification
**And** labeled validation runs report beneficial/harmful/no-effect flips while unlabeled production runs do not infer those categories
**And** it breaks trigger/keep/flip/unresolved results down by uncertainty option position 0/1/2
**And** the report can be stored in the run metrics or audit artifact
**And** no sample loses access to its raw Reasoner and Verifier text.

## Epic 4: Private-Generalization Validation and Candidate Selection [FROZEN — FUTURE ONLY]

**Human-owned hold:** Epic 4 전체는 현재 사용하지 않는다. 데이터셋 작성, 후보 모델 통합·실행, tournament, diagnostic, sealed 평가를 포함한 모든 작업을 사용자의 명시적 해제 전까지 시작하지 않는다.

User can build an independent validation suite, evaluate candidates under frozen contracts, and select a candidate for final compliance/readiness using Private/Hidden generalization evidence rather than Public LB alone.

### Story 4.1: Define Local Validation Dataset Schema and Subsets

**Requirements:** FR17

As a competition developer,
I want local validation examples represented with explicit subset labels,
So that ambiguous and disambiguated behavior can be measured separately from Public LB.

**Acceptance Criteria:**

**Given** a validation data file or fixture
**When** validation data is loaded
**Then** each example includes `sample_id`, image reference/hash, context, question, ordered answers, expected label, `uncertainty_option_index`, `expected_is_uncertainty`, one or more subset labels, provenance/license, author/reviewer, review status, and split
**And** supported subsets include `ambiguous`, `disambiguated_text`, `visual_grounded`, `elimination`, `stereotype_trap`, `expression_trap`, `role_or_function`, and `parsing_stress`
**And** validation data provenance records confirm examples were not derived from evaluation-set wording, patterns, images, or inferred answers
**And** schema checks enforce exactly three answers, option-index consistency, image decode/hash, and supported split/status vocabulary.

### Story 4.2: Acquire or Author Shadow Private Samples and Provenance

**Requirements:** FR17

As a competition developer,
I want 300–600 independently sourced or authored multimodal examples with complete provenance,
So that local validation is large enough to test generalization without evaluation-set leakage.

**Acceptance Criteria:**

**Given** the validation schema and allowed source policy
**When** samples are acquired or authored
**Then** it contains 300–600 samples and zero evaluation/test-derived examples
**And** every sample records provenance type, source/author note, license or permission, author id, image reference and initial subset/label proposal
**And** synthetic/generated samples remain `pending` until independent human review
**And** exact and perceptual duplicates are reported before review.

### Story 4.3: Independently Review, Adjudicate, and Balance Samples

**Requirements:** FR17

As a competition developer,
I want independent label review and coverage balancing,
So that Shadow Private labels and subsets are defensible before sealing.

**Acceptance Criteria:**

**Given** the sourced corpus from Story 4.2
**When** independent review and adjudication complete
**Then** synthetic/generated labels have a human reviewer distinct from the author or generation pipeline
**And** ambiguous labels lack objective resolving evidence while resolvable labels cite stated fact, objective visual evidence, or valid elimination
**And** each required subset has at least 30 samples
**And** uncertainty positions 0/1/2 each cover at least 30% of the corpus
**And** ambiguous and resolvable classes each contain at least 120 samples
**And** rejected, disputed, reviewed and adjudicated records remain auditable.

### Story 4.4: Freeze Selection and Sealed-Holdout Version

**Requirements:** FR17, FR18

As a competition developer,
I want the reviewed corpus split, sealed, and hashed before candidate ranking,
So that repeated experiments cannot silently overfit the local holdout.

**Acceptance Criteria:**

**Given** a reviewed and balanced 300–600 sample corpus
**When** a Shadow Private version is frozen
**Then** sealed holdout is at least 30% and at least 120 samples
**And** dataset, image, split and schema SHA-256 manifests are recorded
**And** sample additions, deletions or label changes require a new dataset version
**And** sealed sample-level text, output and errors remain hidden from prompt/model tuning until shortlist selection
**And** diagnostic-48 remains a separate non-promotion corpus.

### Story 4.5: Compute Robust Validation Metrics

**Requirements:** FR16

As a competition developer,
I want candidate predictions evaluated with competition-relevant local metrics,
So that I can detect over-uncertainty, unsupported person selection, and subset regressions.

**Acceptance Criteria:**

**Given** final predictions and labeled local validation examples
**When** the validation command runs
**Then** it reports local balanced accuracy, ambiguous/resolvable accuracy, worst-subset accuracy, uncertainty-position accuracy, unknown/person over-selection, stereotype/expression errors, semantic consistency, parse/image/unresolved failures, Verifier beneficial/harmful/no-effect flips, average/p95 seconds, peak VRAM, and projected 8,500-row full-path runtime
**And** metrics are written to `metrics.json` under the run directory
**And** missing subset labels, label/index mismatches, dataset hash differences, or incomplete metrics fail validation clearly.

### Story 4.6: Implement Frozen Tournament Harness and Experiment Contract

**Requirements:** FR6, FR16, FR18

As a competition developer,
I want every candidate run generated from the same frozen experiment contract,
So that prompt, model, image, engine and Verifier changes are isolated and reproducible.

**Acceptance Criteria:**

**Given** eligible candidate manifests and a frozen validation version
**When** the tournament harness creates a candidate run
**Then** dataset/split, prompt/schema, model/snapshot, image budget, engine, decoding, seed and Verifier configuration are recorded
**And** prompt, model, image budget, engine, and Verifier are not changed simultaneously in one diagnostic A/B
**And** candidate order and metrics implementation are frozen
**And** mismatched contracts cannot enter the same ranking report.

### Story 4.7: Run Diagnostic-48 and Reasoner-Only Candidate Selection

**Requirements:** FR6, FR16, FR18

As a competition developer,
I want mapping defects separated from Reasoner-only model quality,
So that only structurally valid candidates enter sealed evaluation.

**Acceptance Criteria:**

**Given** harness-eligible candidates
**When** diagnostic and Reasoner-only selection run
**Then** Qwen v2/v3 is first compared with identical snapshot, image, engine, decoding and pixel budget
**And** diagnostic-48 reports mapping/image/template/engine faults but is not used as a promotion score
**And** Reasoner-only selection uses the frozen selection split and robust metrics
**And** every rejection or advancement has an immutable artifact.

### Story 4.8: Integrate Conditional InternVL3-14B Performance Candidate

**Requirements:** FR6, FR14, FR18, FR19

As a competition developer,
I want InternVL3-14B integrated only when lower-cost evidence justifies a larger candidate,
So that added quality can be measured without silently accepting runtime risk.

**Acceptance Criteria:**

**Given** Story 4.7 lower-cost feasibility evidence and the common Story 2.8 harness
**When** InternVL3-14B integration is authorized
**Then** its exact eligible revision, license, official multimodal path and isolated dependency lock are recorded
**And** real-image v3 smoke, diagnostic, latency and peak VRAM gates pass before sealed evaluation
**And** absence of authorization marks the story deferred rather than blocking lower-cost selection.

### Story 4.9: Evaluate Conditional Qwen2.5-VL-32B-AWQ Candidate

**Requirements:** FR6, FR14, FR18, FR19

As a competition developer,
I want the 32B-AWQ path isolated and conditional,
So that quantization dependencies cannot corrupt the baseline environment or consume runtime without evidence.

**Acceptance Criteria:**

**Given** Story 4.7 evidence and a documented quality/runtime justification
**When** Qwen2.5-VL-32B-AWQ is evaluated
**Then** it uses an isolated environment and cannot mutate baseline locks
**And** exact eligibility, quantization source, official multimodal path, diagnostic, VRAM and full-path runtime evidence are recorded
**And** failure or deferral does not block lower-cost candidates.

### Story 4.10: Run Sealed Shortlist and Verifier A/B

**Requirements:** FR10, FR11, FR16, FR18

As a competition developer,
I want shortlisted Reasoners evaluated on sealed evidence with isolated Verifier variants,
So that Verifier benefit is measured without conflating it with model or prompt changes.

**Acceptance Criteria:**

**Given** the Reasoner-only shortlist
**When** sealed and Verifier A/B evaluations run
**Then** Reasoner-only, same-model Verifier and stronger-Verifier configurations are separate runs
**And** sealed sample-level details remain hidden while aggregate metrics and permitted audit evidence are recorded
**And** beneficial, harmful and no-effect flips are computed only from labeled validation
**And** a Verifier with blocking regression cannot advance.

### Story 4.11: Validate Shortlist Runtime and Memory

**Requirements:** FR16, FR18

As a competition developer,
I want full-path runtime and memory gates applied to the shortlist,
So that quality gains remain feasible on one RTX A6000 48GB.

**Acceptance Criteria:**

**Given** shortlisted Reasoner/Verifier configurations
**When** runtime validation runs on the target path
**Then** it records average/p95 latency, peak VRAM and projected 8,500-row full-path runtime
**And** it distinguishes Reasoner-only and triggered-Verifier cost
**And** configurations exceeding the approved runtime/memory policy are blocked or explicitly deferred.

### Story 4.12: Compare Candidate Runs Without Public-Only Optimization

**Requirements:** FR18

As a competition developer,
I want candidate runs compared using robust local metrics and runtime/eligibility signals,
So that candidate selection is based on Private/Hidden generalization evidence.

**Acceptance Criteria:**

**Given** two or more completed run directories
**When** `compare-runs` runs
**Then** it compares local validation metrics, worst-subset regressions, runtime/memory feasibility, parse failure rate, image-load failure rate, verifier trigger/flip behavior, Story 2.8 eligibility/cutoff/license/API evidence, and optional Public score notes
**And** Public score is displayed only as a secondary sanity signal
**And** the comparison output identifies regressions that should block promotion.

### Story 4.13: Select Candidate and Record Promotion Rationale

**Requirements:** FR18

As a competition developer,
I want the selected candidate to include a written rationale,
So that final compliance/readiness receives a defensible candidate rather than a Public-tuned submission.

**Acceptance Criteria:**

**Given** candidate comparison results
**When** a run is selected for final compliance/readiness
**Then** the system records rationale covering local robust validation, ambiguous/disambiguated balance, worst-subset behavior, runtime/memory feasibility, Story 2.8 eligibility evidence, parse/image-load failures, and Public score only as sanity evidence
**And** sealed aggregate, uncertainty-position collapse, unresolved, harmful flips, or blocking eligibility/runtime regressions prevent selection
**And** repeated Public-driven prompt tuning is flagged as a policy risk
**And** selected metadata points to exact run artifacts
**And** selection does not authorize 8,500-row production; Story 5.3 owns production release.

## Epic 5: Compliance and Second-Round Reproducibility Package [FROZEN — FUTURE ONLY]

**Human-owned hold:** Epic 5 전체는 현재 사용하지 않는다. compliance, GPU readiness, second-round package 및 handoff 작업을 사용자의 명시적 해제 전까지 시작하지 않는다.

User can prove competition-rule compliance and prepare the artifact set needed for code verification, Hidden evaluation, and second-round review.

### Story 5.1: Generate Candidate Compliance Manifest

**Requirements:** FR19

As a competition developer,
I want every candidate run to produce a complete compliance manifest,
So that model, data, inference, and output rule compliance can be verified later.

**Acceptance Criteria:**

**Given** a completed candidate run
**When** compliance manifest generation runs
**Then** it writes `compliance_manifest.json` with model identity/revision/hash, cutoff evidence, license/source, custom-code manifest, remote API usage, external data provenance, inference command, environment record, Reasoner/Verifier prompt versions and hashes, artifact schema/option-index semantics versions, unresolved count, arbitration usage, intended submission path, and production status
**And** remote API usage must be recorded as `none` for compliant runs
**And** before production the selected file/hash may be `pending_production`, but after production it must be finalized before external submission
**And** missing model cutoff, license, source, or data provenance fields fail the compliance check.

### Story 5.2: Audit Offline Reproducibility Inputs

**Requirements:** FR19, FR20

As a competition developer,
I want final runs audited for offline reproducibility,
So that Multimodal code verification can rerun the solution without hidden network dependencies.

**Acceptance Criteria:**

**Given** a selected candidate run
**When** `audit-run` checks reproducibility
**Then** before production it verifies resolved config, environment record, local model snapshot or documented model acquisition path, prompt versions, diagnostic/validation raw logs, metrics, compliance manifest, atomic artifact path and submission-boundary dry-run evidence are present
**And** after production the same audit additionally requires complete raw inference logs, parsed predictions, final predictions, the real submission CSV and finalized compliance file/hash
**And** it reports missing artifacts as blocking issues
**And** it verifies prompt/schema hashes, option-index semantics version, unresolved count zero, and arbitration lineage
**And** it flags any dependency on remote model APIs or network-only inference paths.

### Story 5.3: Validate GPU Submission Readiness and Notify Operator

**Requirements:** FR12, FR14, FR19, FR20, FR21, NFR2, NFR7

As a competition operator,
I want an explicit GPU readiness verdict and notification before full inference,
So that an 8,500-row run starts only when it can produce a valid submission on the target path.

**Acceptance Criteria:**

**Given** a promoted candidate on the target GPU path
**When** `check-gpu-readiness` runs
**Then** it writes `gpu_readiness.json` with stable gates `target_environment`, `model_snapshot_license`, `data_image_validation`, `prompt_schema_identity`, `real_image_structured_output`, `diagnostic_blockers`, `vram_runtime_projection`, `atomic_artifact_persistence`, `final_submission_validation`, and `network_disabled_smoke`
**And** each gate records status, evidence path, blocker, candidate id and timestamp
**And** `final_submission_validation` uses a fixed fixture/dry-run before production and never claims that the real 8,500-row file already exists
**And** only a 10/10 result records `GPU_SUBMISSION_READY`
**And** the aggregate records candidate, run command, projected runtime and notification status
**And** the user is notified with candidate, run command, expected runtime and cleared blockers before 8,500-row production starts
**And** any failed gate suppresses the ready notification and records the blocking reason
**And** internal total-runtime target is 63 minutes with explicit warning before the official 70-minute reference is at risk.

### Story 5.4: Prepare Second-Round Artifact Checklist

**Requirements:** FR20

As a competition developer,
I want a second-round readiness checklist derived from run artifacts,
So that final submission packaging is complete if the team qualifies.

**Acceptance Criteria:**

**Given** a promoted candidate run with validated 8,500-row production artifacts
**When** second-round readiness is generated
**Then** it lists required separated train and inference code, `.py` or `.ipynb` files, model files or model acquisition path, all external data files, UTF-8 code/comment requirement, OS/library version record, solution PDF inputs, and student-status evidence inputs
**And** it marks each item as present, missing, or not applicable
**And** it links each present item to its source path or run artifact.

### Story 5.5: Produce Final Handoff Summary for Implementation and Review

**Requirements:** FR20

As a competition developer,
I want a concise final handoff summary for the selected solution,
So that developers, reviewers, and second-round evaluators can understand how to reproduce and inspect it.

**Acceptance Criteria:**

**Given** a promoted candidate with compliance, readiness and validated production checks
**When** the handoff summary is generated
**Then** it summarizes the selected model, run id, inference command, expected input data path, output submission path, validation metrics, compliance status, known minor gaps, and reproduction steps
**And** it references raw logs and manifests rather than duplicating them
**And** it remains UTF-8 and suitable for inclusion in a solution package or README.

## Future Integrated Execution Order — Currently Frozen

아래 순서는 미래 참고용이며 현재 실행 승인이 아니다. 지금 활성화된 범위는 Qwen2.5-VL-7B Reasoner v3 조기 재제출 경로뿐이다. Story 2.9 이후의 어떤 항목도 사용자의 명시적 해제 없이 다음 작업으로 선택하지 않는다.

### Gate A — Reasoner and Verification Contract

Story 2.7 → Story 2.8 → **STOP: HUMAN APPROVAL REQUIRED** → (future Story 2.9 and Story 2.10 independently) → future Story 3.1 → Story 3.2 → Story 3.3 → Story 3.4

Completion requires one active v3 contract, lower-cost candidate smoke eligibility, position 0/1/2 semantic tests, no fixed-label meaning, valid pre/post-Verifier lifecycle, no invented label, diagnostic v2/v3 A/B, and a passing CPU suite.

### Gate B — Independent Validation Foundation

Story 4.1 → Story 4.2 → Story 4.3 → Story 4.4 → Story 4.5

Completion requires a reviewed and hashed 300–600 sample suite with a sealed holdout and deterministic metrics.

### Gate C — Common Candidate Foundation

Story 4.6 → Story 4.7

Completion requires the corrected Qwen control and already smoke-eligible lower-cost challengers to pass Reasoner-only selection on the same frozen contract.

### Gate D — Expanded Shortlist and Selection

Conditional Story 4.8 and/or Story 4.9 → Story 4.10 → Story 4.11 → Story 4.12 → Story 4.13

Completion requires optional larger-candidate evidence, sealed/Verifier A/B, runtime/memory evidence, immutable comparison and a selected candidate rationale. InternVL/AWQ deferral does not block lower-cost selection.

### Gate E — Compliance and GPU Release

Story 5.1 → Story 5.2 → Story 5.3

Completion requires readiness 10/10, unresolved zero, full-path runtime/VRAM/compliance success, and user notification.

### Gate F — Production and Handoff

Validated 8,500-row production → Story 5.4 → Story 5.5
