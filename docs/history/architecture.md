---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md
  - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/strategy.md
  - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/validation-strategy.md
  - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/compliance-references.md
  - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/architecture-diagrams.md
  - docs/history/research/technical-multimodal-236722-multimodal-ai-bias-research-2026-06-18.md
  - Multimodal_236722_평가_요구사항_정리.md
  - _bmad-output/specs/spec-reasoner-v3-contract/SPEC.md
  - _bmad-output/specs/spec-shadow-private-validation/SPEC.md
  - docs/history/research/technical-multimodal-236722-vlm-model-tournament-research-2026-06-20.md
  - docs/history/sprint-change-proposal-2026-06-20.md
  - docs/history/implementation-readiness-report-2026-06-20.md
  - docs/history/sprint-change-proposal-ir-remediation-2026-06-20.md
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2026-06-18'
correctedAt: '2026-06-20'
project_name: 'Multimodal 236722 Multimodal AI Bias Solution'
user_name: 'gongman'
date: '2026-06-18'
---

# Architecture Decision Document

_This document builds through step-by-step architectural decisions for the Multimodal 236722 multimodal AI bias challenge solution._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
The system must ingest the official Multimodal `open.zip` layout, parse `test.csv` rows and image paths, run multimodal inference for all 8,500 test samples, and emit a UTF-8 `sample_id,label` CSV with labels restricted to `0`, `1`, `2`. It must preserve raw model reasoning, parsed labels, verification activity, and run metadata so candidate submissions can be audited and reproduced.

The core answer behavior is evidence-grounded multimodal QA: choose a person when text or objective visual evidence resolves the question, choose uncertainty when evidence is insufficient, and avoid protected-attribute or appearance-only reasoning. The architecture must support a primary Reasoner and a conditional Verifier, not an unconditional 2-pass design.

**Non-Functional Requirements:**
The dominant NFRs are compliance, reproducibility, Private/Hidden generalization, runtime feasibility, and auditability. The design must run offline without remote model APIs, use only eligible open-source weights public by 2026-05-31, target RTX A6000 48GB/Python 3.10/CUDA 12.4/PyTorch 2.6.0, and keep inference practical against the organizer guidance.

**Scale & Complexity:**
This is a medium-high ML inference pipeline, not a product app. Complexity comes from model eligibility, multimodal batch inference, ambiguity handling, leakage avoidance, conditional verification, logging, local validation, and second-round reproducibility.

- Primary domain: offline multimodal ML inference / competition pipeline
- Complexity level: medium-high
- Estimated architectural components: data loader, validator, image preprocessor, prompt builder, model runtime adapter, Reasoner, verification trigger, Verifier, parser, logger, validation runner, compliance ledger, submission writer

### Technical Constraints & Dependencies

The architecture is constrained to Python competition code, local/offline model execution, UTF-8 CSV outputs, and no test-derived prompt/data engineering. It depends on the official data layout, a selected eligible VLM, image processing, structured generation/parsing, robust logging, and a validation harness that reports ambiguous/disambiguated-oriented metrics without relying on hidden labels.

### Cross-Cutting Concerns Identified

- Compliance: model cutoff, license/source, API ban, external data provenance, LLM-generated final answer.
- Robustness: avoid Public overfit and preserve Private/Hidden generalization.
- Bias control: block protected-attribute and appearance-only subjective judgments.
- Reproducibility: run ids, model revision, prompt version, raw outputs, environment records.
- Observability: parse failures, image-load failures, verification flips, runtime metrics.
- Performance: fit A6000 48GB and remain near practical inference limits.
- Data safety: no evaluation-set pattern mining for training data, prompt rules, or examples.

## Starter Template Evaluation

### Primary Technology Domain

Offline multimodal ML inference / competition CLI pipeline.

This is not a web, mobile, API, or full-stack product. The implementation should start as a packaged Python application with reproducible CLI commands for ingestion, validation, inference, verification, audit logging, and submission generation.

### Starter Options Considered

1. **uv packaged Python application - selected**
   - Uses `pyproject.toml`, `.python-version`, `uv.lock`, `uv run`, and `src/` layout.
   - Fits offline reproducibility, CUDA/PyTorch environment control, CLI-first workflows, and second-round audit requirements.
   - Supports explicit PyTorch index configuration for CUDA builds.

2. **Hatch**
   - Strong Python project scaffolding with `src/` and tests.
   - Good packaging tool, but less direct for this competition's lockfile + PyTorch accelerator workflow than `uv`.

3. **Poetry**
   - Mature dependency management and lockfile workflow.
   - Heavier for GPU research pipelines, and Python interpreter management remains external.

4. **Manual scaffold**
   - Maximum control, but repeats environment and packaging decisions and increases reproducibility risk.

### Selected Starter: uv Packaged Python CLI Application

**Rationale for Selection:**

Use `uv` because the project needs reproducible local execution, exact dependency locking, Python-version pinning, simple CLI commands, and clean package boundaries. A packaged `src/` layout reduces accidental imports from the repository root and makes tests closer to real execution.

**Initialization Command:**

```bash
uv init --package --python 3.10 --name multimodal-bias --vcs none .
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
Python 3.10, matching the target competition environment. CUDA, PyTorch, Transformers, and VLM runtime dependencies are added explicitly after model selection.

**Styling Solution:**
Not applicable. Configuration should use TOML/YAML files, not UI styling.

**Build Tooling:**
`pyproject.toml` plus `uv.lock`. Use `uv sync` for environment sync and `uv run` for all project commands.

**Testing Framework:**
Add `pytest` for parser, data loading, validation, compliance guard, and submission writer tests. GPU model tests should be separate smoke/integration commands.

**Code Organization:**
Use `src/multimodal_bias/` with modules for data loading, image preprocessing, prompt construction, model runtime adapters, Reasoner, conditional Verifier, output parsing, validation, compliance ledger, run logging, and submission writing.

**Development Experience:**
Expose CLI entrypoints such as `validate-data`, `infer`, `verify-risky`, `make-submission`, `audit-run`, `compare-runs`, and `check-gpu-readiness`. Use `ruff` for lint/format and keep data, model weights, run outputs, and submissions outside tracked package code.

**Note:** Project initialization using this command should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions:**
- Use file-based competition artifacts, not a database.
- Use Python 3.10 + PyTorch 2.6.0 CUDA 12.4 as the target runtime.
- Use local Hugging Face model snapshots only; no remote model API inference.
- Implement a Reasoner + conditional Verifier pipeline.
- Select submissions by private-generalization evidence, not Public LB alone.

**Important Decisions:**
- Use Pydantic schemas for input/config/output validation.
- Use Typer CLI for repeatable commands.
- Store every run under immutable `runs/{run_id}/`.
- Keep validation, compliance, and submission generation as separate commands.

**Deferred Decisions:**
- Exact eligible VLM/revision.
- Whether a 27B model is used only as an oracle or included in final inference.
- Optional Docker image after the first working GPU path is stable.

### Data Architecture

No database. The official `open.zip` contents remain read-only under `data/raw/`. Derived artifacts go to `data/processed/`, `runs/`, and `submissions/`.

Each run writes:
- `config.resolved.yaml`
- `environment.json`
- `raw_reasoner.jsonl`
- `parsed_reasoner.csv`
- `verification.jsonl`
- `final_predictions.csv`
- `submission.csv`
- `metrics.json`
- `compliance_manifest.json`

### Runtime & Model Architecture

Primary runtime: Python 3.10, PyTorch 2.6.0 CUDA 12.4, Transformers/Accelerate-compatible local model loading.

Model access is abstracted behind `VisionLanguageModelAdapter`, so candidate models can be swapped without rewriting Reasoner, Verifier, parser, or submission code.

The selected model must have:
- public weight release by 2026-05-31
- compatible license/source record
- pinned repository revision or local snapshot hash
- offline-load test
- A6000 48GB smoke test

Candidate integration follows this order: corrected Qwen2.5-VL-7B control; MiniCPM-V 4.5 and LLaVA-OneVision 7B challengers; InternVL3-14B performance candidate; conditional Qwen2.5-VL-32B-AWQ. Each model uses its official processor/chat/image path behind a typed adapter and a candidate-specific dependency lock.

Tournament promotion follows `eligibility → real-image structured smoke → diagnostic-48 → Reasoner-only selection → sealed shortlist → Verifier A/B → runtime/compliance`. Model, prompt contract, image budget, engine, and Verifier are not changed simultaneously in a diagnostic A/B.

### Reasoner + Conditional Verifier

The Reasoner produces structured text containing:
- final answer-choice index: `0`, `1`, or `2`
- `uncertainty_option_index`: integer `0`, `1`, or `2`, generated for every sample
- concise evidence
- uncertainty signal
- protected-attribute risk flag
- schema version
- parseable final answer marker

The Verifier runs only when triggered by risk rules:
- low confidence or uncertainty conflict
- parser failure or invalid label
- evidence does not support selected person
- reasoning mentions protected attributes or appearance-only judgment
- ambiguous question/image relationship
- known boundary patterns from validation, not from hidden/test mining

Reasoner raw text is parsed and semantically validated before pre-Verifier trigger detection. The pre-Verifier trigger stage may use only Reasoner-derived fields. `reasoner_verifier_conflict` is not a pre-Verifier trigger; it is a post-Verifier comparison event emitted only after both generated candidates have been parsed. It must never cause an otherwise untriggered Verifier pass.

Arbitration rule:
- keep Reasoner if Verifier finds no concrete defect
- flip only to a valid Verifier-generated candidate when the Verifier gives stronger evidence
- use a valid stage-generated uncertainty-choice index when evidence is insufficient
- if neither stage has a valid generated candidate, mark the sample `unresolved` and block final artifact publication
- never infer semantic meaning from the numeric label or invent a fallback label
- log every verifier trigger and flip

### Validation Strategy

Use two independent validation tiers: `diagnostic-48` for mapping/image/template/engine faults and a frozen 300–600 sample Shadow Private suite for promotion. The latter has selection and sealed-holdout splits; diagnostic results never rank tournament candidates.

The validation harness measures:
- parse failure rate
- invalid label rate
- protected-attribute violation rate
- verifier trigger/flip rate
- ambiguous-case handling
- public-score sensitivity, without optimizing only for Public LB
- uncertainty-position accuracy, semantic consistency and unresolved rate
- beneficial/harmful/no-effect Verifier flips
- peak VRAM and projected 8,500-row full-path runtime

Validation examples must be independently created or legally sourced, not mined from hidden/test leakage patterns.

### Compliance & Security

No authentication/frontend/API layer is needed. Security focus is competition compliance:
- no remote LLM/API inference
- no hidden/test-derived prompt engineering
- model/source/license cutoff ledger
- external data provenance ledger
- reproducible run manifest
- UTF-8 submission output
- final labels generated by LLM output parsing, not hand-coded rule labels

### API & Communication Patterns

No network API. Internal communication is module-level Python calls plus typed dataclasses/Pydantic models.

CLI commands:
- `validate-data`
- `smoke-model`
- `infer`
- `verify-risky`
- `make-submission`
- `audit-run`
- `compare-runs`
- `check-gpu-readiness`

### Infrastructure & Deployment

Primary target is one local/server GPU machine matching A6000 48GB class.

CI should run CPU-only tests for parsing, validation, compliance guards, and submission formatting. GPU tests are explicit smoke/integration commands.

Use offline mode for final reproducibility:
- pre-download model snapshot
- set cache directories explicitly
- record snapshot revision/hash
- block accidental network dependency during final run

### Decision Impact Analysis

Implementation sequence:
1. Scaffold `uv` package and CLI.
2. Implement schemas and artifact layout.
3. Implement data loader and submission writer.
4. Implement model adapter.
5. Implement Reasoner prompt/parser.
6. Implement Reasoner v3 semantic contract and fail-closed downstream lineage.
7. Correct verifier triggers, Verifier output, post-Verifier comparison and arbitration.
8. Build and freeze diagnostic-48 plus the 300–600 sample Shadow Private suite.
9. Integrate eligible model candidates and execute the staged tournament.
10. Implement compliance, GPU readiness notification and final handoff.

Cross-component dependencies:
- Model adapter must expose raw text and generation metadata.
- Parser must not depend on model-specific phrasing except the final answer marker.
- Verifier must be optional and fully logged.
- Submission writer only consumes validated final predictions.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**
AI agents could diverge on package structure, CLI names, config schemas, JSONL fields, prediction label parsing, run directory layout, verification trigger names, compliance logs, and error handling.

### Naming Patterns

**Database Naming Conventions:**
No database is used. Do not introduce SQLite, DuckDB, Postgres, or vector DB storage unless the architecture is revised.

**API Naming Conventions:**
No network API is used. Public interfaces are CLI commands and Python module interfaces.

**Code Naming Conventions:**
Use snake_case for Python files, functions, variables, config keys, and JSON fields. Use PascalCase for classes and Pydantic models.

Required class names:
- `CompetitionConfig`
- `SampleRecord`
- `ReasonerOutput`
- `VerifierOutput`
- `FinalPrediction`
- `RunManifest`
- `ComplianceManifest`
- `VisionLanguageModelAdapter`

Required label names:
- `0`, `1`, and `2` are only zero-based answer-choice indexes.
- No numeric index has inherent person or uncertainty meaning.
- Every valid generated candidate records its own `uncertainty_option_index`.

### Structure Patterns

**Project Organization:**
Use `src/multimodal_bias/` as the only importable package root.

Required modules:
- `cli.py`
- `config.py`
- `schemas.py`
- `data_loader.py`
- `image_io.py`
- `prompting/`
- `models/`
- `reasoner.py`
- `verifier.py`
- `arbitration.py`
- `parsing.py`
- `validation.py`
- `compliance.py`
- `submission.py`
- `run_logging.py`
- `run_comparison.py`
- `readiness.py`

**File Structure Patterns:**
Keep raw data read-only under `data/raw/`. Keep generated artifacts out of source code.

Required top-level artifact folders:
- `configs/`
- `data/raw/`
- `data/processed/`
- `models/`
- `runs/`
- `submissions/`
- `tests/`

### Format Patterns

**Run Artifact Formats:**
Every run must write to `runs/{run_id}/`.

Required files:
- `config.resolved.yaml`
- `environment.json`
- `raw_reasoner.jsonl`
- `parsed_reasoner.csv`
- `verification.jsonl`
- `final_predictions.csv`
- `submission.csv`
- `metrics.json`
- `compliance_manifest.json`

**Data Exchange Formats:**
Use UTF-8 for all CSV/JSON/YAML files. Use JSONL for per-sample model outputs. Use CSV only for tabular predictions and Multimodal submissions.

All per-sample records must include:
- `sample_id`
- `image_path`
- `question`
- `raw_output`
- `parsed_label`
- `uncertainty_option_index`
- `schema_version`
- `parse_status`
- `risk_flags`
- `created_at`

### Communication Patterns

**Internal Module Contracts:**
Modules communicate through typed Pydantic models or plain dataclasses imported from `schemas.py`. Do not pass anonymous dictionaries across Reasoner, Verifier, arbitration, and submission layers.

**Verification Event Patterns:**
Pre-Verifier trigger names must be stable snake_case values:
- `invalid_parse`
- `low_confidence`
- `unsupported_evidence`
- `protected_attribute_risk`
- `appearance_only_reasoning`
- `ambiguous_visual_grounding`

The post-Verifier comparison event is:
- `reasoner_verifier_conflict`

It is emitted only after Reasoner and Verifier parsing when both valid selected indexes differ. It is never input to initial Verifier routing.

### Process Patterns

**Error Handling Patterns:**
Recoverable per-sample failures must be logged without creating a label. Arbitration may keep or flip only between valid generated candidates. If no valid candidate survives, the sample is `unresolved`; `final_predictions.csv` and `submission.csv` publication fails closed. Fatal run-level failures raise explicit exceptions before submission generation.

Required exception classes:
- `DataLayoutError`
- `ModelLoadError`
- `InferenceError`
- `ParseError`
- `ComplianceError`
- `SubmissionFormatError`

**Logging Patterns:**
Use structured JSON-compatible logs. Every log row for inference must include `run_id`, `sample_id`, `stage`, `status`, and `message`.

**Submission Safety Pattern:**
`submission.csv` can only be written by `make-submission`, and only from validated `final_predictions.csv`. No module may write Multimodal submission format directly.

### Enforcement Guidelines

**All AI Agents MUST:**
- Add new shared schemas to `schemas.py`.
- Add new CLI commands through `cli.py`.
- Keep raw model text before parsing.
- Preserve verifier trigger and flip logs.
- Run submission validation before writing `submission.csv`.
- Record model source, revision/hash, and license in `compliance_manifest.json`.
- Avoid hidden/test-derived prompt examples or rules.

**Pattern Enforcement:**
Unit tests must cover schema validation, parser behavior, label constraints, run artifact creation, compliance manifest generation, and submission CSV format.

### Pattern Examples

**Good Examples:**
- `runs/20260618_153012_qwen2_5_vl_7b/raw_reasoner.jsonl`
- `risk_flags=["protected_attribute_risk", "unsupported_evidence"]`
- `parse_status="valid"`
- `final_label` equals a valid generated uncertainty-choice index when evidence is insufficient
- `status="unresolved"` when no valid generated candidate exists; no submission is written

**Anti-Patterns:**
- Writing `submission.csv` inside `reasoner.py`
- Inferring labels with hard-coded keyword rules
- Re-parsing raw outputs differently in multiple modules
- Using Public LB movement as the only model selection criterion
- Storing final predictions without raw model output and verifier history

## Project Structure & Boundaries

### Complete Project Directory Structure

```text
multimodal-bias/
├── README.md
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── configs/
│   ├── base.yaml
│   ├── models/
│   │   └── example_vlm.yaml
│   └── prompts/
│       ├── reasoner_v1.yaml
│       ├── reasoner_v2.yaml
│       ├── reasoner_v3.yaml
│       ├── verifier_v1.yaml
│       └── verifier_v2.yaml
├── data/
│   ├── raw/
│   │   └── open/                 # official open.zip extracted here, read-only
│   └── processed/
│       └── validation/           # diagnostic and frozen Shadow Private manifests
├── models/
│   └── snapshots/                # local HF snapshots or symlinks
├── runs/
├── submissions/
├── notebooks/
│   └── exploration_only.md
├── src/
│   └── multimodal_bias/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── schemas.py
│       ├── exceptions.py
│       ├── data_loader.py
│       ├── image_io.py
│       ├── parsing.py
│       ├── reasoner.py
│       ├── verifier.py
│       ├── arbitration.py
│       ├── validation.py
│       ├── compliance.py
│       ├── submission.py
│       ├── run_logging.py
│       ├── run_comparison.py
│       ├── readiness.py
│       ├── prompting/
│       │   ├── __init__.py
│       │   ├── templates.py
│       │   └── guards.py
│       └── models/
│           ├── __init__.py
│           ├── adapter.py
│           ├── hf_vlm.py
│           └── dummy.py
└── tests/
    ├── fixtures/
    ├── test_data_loader.py
    ├── test_parsing.py
    ├── test_arbitration.py
    ├── test_submission.py
    ├── test_compliance.py
    └── test_run_logging.py
```

### Architectural Boundaries

**API Boundaries:**
No network API. CLI commands are the public execution boundary.

**Component Boundaries:**
`reasoner.py` produces raw/parsed outputs. `verifier.py` only evaluates risky cases. `arbitration.py` is the only place allowed to choose final labels after verifier input.

**Service Boundaries:**
`models/adapter.py` defines model runtime interface. Model-specific loading belongs in `models/hf_vlm.py`; business logic must not depend on one model's output quirks.

**Data Boundaries:**
`data/raw/` is read-only. `runs/{run_id}/` is immutable after completion. `submission.py` can only consume validated final predictions.

### Requirements to Structure Mapping

**CAP-1 Ingest and Predict:**
`data_loader.py`, `image_io.py`, `models/`, `reasoner.py`, `submission.py`

**CAP-2 Evidence-Grounded Answers:**
`prompting/templates.py`, `reasoner.py`, `parsing.py`

**CAP-3 Bias/Protected-Attribute Control:**
`prompting/guards.py`, `verifier.py`, `arbitration.py`, `compliance.py`

**CAP-4 Conditional Verifier:**
`verifier.py`, `arbitration.py`, `run_logging.py`

**CAP-5 Private-Generalization Selection:**
`validation.py`, `run_logging.py`, `runs/`, `submissions/`

**CAP-6 Compliance:**
`compliance.py`, `config.py`, `models/snapshots/`, `runs/{run_id}/compliance_manifest.json`

**CAP-7 Second-Round Artifacts:**
`runs/`, `README.md`, `compliance.py`, `submission.py`

### Integration Points

**Internal Communication:**
All major modules exchange `schemas.py` models, not raw dictionaries.

**External Integrations:**
Only local filesystem, official Multimodal data, and local model snapshots. No remote model API.

**Data Flow:**
`test.csv + images -> SampleRecord -> generated Reasoner candidate + uncertainty index -> risk flags -> optional generated Verifier candidate + uncertainty index -> arbitration or unresolved -> validated FinalPrediction -> submission.csv`

### File Organization Patterns

**Configuration Files:**
Runtime configuration lives in `configs/base.yaml`, model-specific configuration in `configs/models/`, and prompt templates in `configs/prompts/`.

**Source Organization:**
Importable application code lives only under `src/multimodal_bias/`.

**Test Organization:**
CPU-safe unit tests live in `tests/`. GPU smoke tests should be explicit CLI checks rather than default unit tests.

**Asset Organization:**
Official data lives under `data/raw/open/`; generated outputs live under `runs/` and `submissions/`.

### Development Workflow Integration

**Development Structure:**
Use `uv run multimodal-bias <command>`. Experiments may read from `configs/`, but final submission must be generated through CLI.

**Build Process Structure:**
Package code lives only in `src/multimodal_bias/`. Generated artifacts stay outside source.

**Deployment Structure:**
Final execution requires synced environment, local model snapshot, official data path, resolved config, and run manifest.

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All major decisions are mutually compatible: Python 3.10, local PyTorch/CUDA inference, file-based artifacts, `uv` packaging, typed schemas, Reasoner + conditional Verifier, and offline compliance controls form a coherent competition pipeline.

**Pattern Consistency:**
Naming, artifact, logging, parser, verifier-trigger, and submission-safety patterns directly support the architectural decisions. The architecture consistently prevents hidden/test leakage, Public LB overfit, and unlogged final-label generation.

**Structure Alignment:**
The `src/multimodal_bias/` package structure supports ingestion, model adaptation, reasoning, verification, arbitration, validation, compliance, logging, and submission generation. One minor structural refinement is recommended for `compare-runs`.

### Requirements Coverage Validation ✅

**Epic/Feature Coverage:**
The architecture supports the required capabilities: official data ingestion, multimodal inference, evidence-grounded labels, protected-attribute controls, conditional verification, private-generalization selection, compliance logging, and second-round reproducibility.

**Functional Requirements Coverage:**
All functional requirements are covered through `data_loader.py`, `image_io.py`, `models/adapter.py`, `reasoner.py`, `verifier.py`, `arbitration.py`, `parsing.py`, `submission.py`, and run artifacts.

**Non-Functional Requirements Coverage:**
Compliance, reproducibility, auditability, offline execution, practical GPU runtime, UTF-8 output, and Public LB overfit avoidance are architecturally supported.

### Implementation Readiness Validation ✅

**Decision Completeness:**
Critical implementation decisions are documented. Exact eligible model/revision selection remains a final configuration decision, not an architecture blocker.

**Structure Completeness:**
The project structure is sufficiently complete for implementation. Add `src/multimodal_bias/run_comparison.py` to own `compare-runs` behavior cleanly.

**Pattern Completeness:**
Parser behavior, verifier triggers, arbitration, run artifacts, compliance manifests, submission writing, and tests are specified enough for AI agents to implement consistently.

### Gap Analysis Results

**Critical Gaps:** None.

**Important Gaps:** The approved 2026-06-20 correction must be implemented and revalidated before Epic 3·4·5 execution: Reasoner v3, Shadow Private corpus, candidate tournament, and GPU readiness notification.

**Minor Gaps:**
- Exact winning VLM and pinned revision are intentionally deferred to the frozen tournament.
- Shadow Private sources and reviewed corpus are not yet built.
- Full GPU inference environment availability is not confirmed.
- `compare-runs` has a CLI requirement but should receive an explicit owner module: `run_comparison.py`.

### Validation Issues Addressed

No critical architecture changes are required. The only structural refinement is to add `run_comparison.py` during implementation so run comparison logic does not leak into validation, logging, or CLI glue code.

### Architecture Completeness Checklist

**Requirements Analysis**

- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**

- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**Implementation Patterns**

- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**

- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** CORRECTED — IMPLEMENTATION READINESS REVALIDATION REQUIRED

**Confidence Level:** high for architecture; model winner and GPU readiness remain evidence-gated

**Key Strengths:**
- Strong compliance and reproducibility posture.
- Clear Reasoner + conditional Verifier separation.
- Explicit anti-overfit strategy for Public LB.
- Immutable run artifacts and auditable final submissions.

**Areas for Future Enhancement:**
- Finalize eligible model snapshot and license ledger.
- Finalize independent validation data source.
- Confirm full A6000-class inference path.
- Add `run_comparison.py` as the owner for compare-runs logic.

### Implementation Handoff

**AI Agent Guidelines:**
Follow the architecture exactly, preserve raw model outputs, route final labels only through arbitration, generate submissions only from validated predictions, and record model/source/license evidence in every run.

**First Implementation Priority:**
Implement Story 2.7 Reasoner v3 contract, complete corrected Stories 3.1~3.4, then establish the decomposed Shadow Private foundation before model tournament or Verifier promotion.

## GPU Submission Readiness Gate

Before the 8,500-row production run, `readiness.py` writes `gpu_readiness.json` and evaluates these stable gate IDs: `target_environment`, `model_snapshot_license`, `data_image_validation`, `prompt_schema_identity`, `real_image_structured_output`, `diagnostic_blockers`, `vram_runtime_projection`, `atomic_artifact_persistence`, `final_submission_validation`, and `network_disabled_smoke`. `final_submission_validation` is a fixed-fixture/dry-run validation of the complete submission boundary before production; the real 8,500-row artifact is validated and audited after production. Each gate records status, evidence path and blocker. Only 10/10 may record `GPU_SUBMISSION_READY`. The operator is notified with candidate, run command, expected runtime and cleared blockers before production begins; any failed gate suppresses both readiness notification and production.
