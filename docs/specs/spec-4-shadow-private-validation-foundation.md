---
title: 'Implement the Shadow Private validation foundation and human review gate'
type: 'feature'
created: '2026-06-21'
status: 'in-review'
baseline_commit: 'NO_VCS'
context:
  - 'epic-4-context.md'
  - '_bmad-output/specs/spec-shadow-private-validation/SPEC.md'
  - '_bmad-output/specs/spec-shadow-private-validation/dataset-contract.md'
  - '_bmad-output/specs/spec-shadow-private-validation/evaluation-and-freeze-policy.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Model and Reasoner candidates are currently selected without an independent labeled suite, so changes cannot be distinguished from Public overfitting or regressions across ambiguity, grounding, and option position. The repository has a canonical Shadow Private contract but no functional implementation or reviewed corpus.

**Approach:** Implement a fail-closed Shadow Private schema, loader, provenance/review/coverage audit, immutable freeze manifest, candidate evaluator, and CLI. Provide authoring and independent-review templates, but never mark generated/synthetic candidates as reviewed or promotion-ready without a distinct human reviewer.

## Boundaries & Constraints

**Always:** Keep validation sources independent of evaluation/test wording, patterns, distributions, images, and inferred answers; require exactly three choices, label/index consistency, image decode/hash, supported subsets/status/splits, explicit provenance/license/author/reviewer, and author-reviewer separation; preserve rejected/disputed history; require 300–600 reviewed samples, each subset >=30, each uncertainty position >=30%, ambiguous/resolvable >=120, and sealed holdout >=30% and >=120 before freeze; write deterministic UTF-8 artifacts and SHA-256 manifests; compute competition-relevant aggregate/subset/position/error/runtime metrics from frozen labels and candidate predictions.

**Ask First:** Downloading or incorporating an external dataset, accepting a license, generating 300–600 candidate samples/images, changing coverage gates, revealing sealed sample-level content, or declaring any pending corpus reviewed requires explicit human approval.

**Never:** Read or mine `data/raw/open/test`, test outputs, Public disagreements, or leaderboard feedback to author samples; use Shadow data for training/fine-tuning; infer labels from numeric position; let synthetic/generated authors self-review; silently repair invalid records; freeze incomplete/unbalanced data; claim a usable Shadow score from templates or pending rows.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|---------------------------|----------------|
| Authoring audit | JSONL records and local images | Ordered audit with record/image hashes, provenance, review and coverage status | All violations are reported; promotion readiness remains false |
| Freeze | Fully reviewed balanced 300–600 corpus | Versioned immutable dataset/split/image/schema manifests | Reject pending, self-reviewed, duplicate, missing, corrupt or under-covered corpus |
| Candidate evaluation | Frozen manifest plus ordered predictions/runtime metadata | `metrics.json` with balanced, subset, position, selection-error and runtime metrics | Reject ID/order/hash/label mismatches and incomplete metadata |
| Sealed holdout | Frozen holdout before shortlist | Aggregate metrics only | Reject sample-level export unless explicit unseal creates a new version |

</frozen-after-approval>

## Code Map

- `src/multimodal_bias/schemas.py` -- add immutable Shadow record, audit, freeze, prediction and metric contracts.
- `src/multimodal_bias/validation.py` -- implement JSONL loading, image/hash checks, review/coverage audit, freeze and metrics.
- `src/multimodal_bias/cli.py` -- expose audit, freeze and evaluate commands with clear non-zero failures.
- `configs/validation/` -- versioned authoring schema, source policy and empty review templates; no fabricated reviewed corpus.
- `tests/test_shadow_validation.py` and `tests/test_cli.py` -- cover every gate and CLI boundary.

## Tasks & Acceptance

**Execution:**
- [x] Add strict typed contracts and stable vocabularies for Shadow records, audit reports, frozen manifests, predictions and metrics.
- [x] Implement deterministic load/audit/freeze/evaluate functions with no-clobber and sealed-holdout protections.
- [x] Add CLI commands and author/reviewer templates that make human-gated corpus creation operational.
- [x] Add CPU-safe fixtures and tests for valid flows, provenance leakage guards, review separation, coverage, image integrity, hashing, prediction mismatch and sealed output.

**Acceptance Criteria:**
- Given independently authored candidate records, when audit runs, then every structural, provenance, review, image, duplicate and coverage result is explicit and no incomplete corpus is promotion-ready.
- Given a fully reviewed balanced corpus, when freeze runs, then immutable manifests bind schema, records, images and split while later mutation is detected.
- Given candidate predictions for a frozen selection or sealed split, when evaluate runs, then required metrics are reproducible and sealed output contains no sample-level content.
- Given any evaluation/test-derived provenance or attempted human-review bypass, when commands run, then they fail closed before freeze or candidate ranking.

## Spec Change Log

## Design Notes

This feature creates the measurement system, not a fictitious 300–600-row truth set. Authoring/generation can produce pending rows only; an independent human must review and adjudicate them before the freeze gate can pass.

## Verification

**Commands:**
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/test_shadow_validation.py tests/test_cli.py` -- schema, audit, freeze, metrics and CLI cases pass.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src/multimodal_bias tests` -- lint passes.
- `UV_CACHE_DIR=/tmp/uv-cache uv run multimodal-bias shadow-audit --help` -- authoring workflow is discoverable without GPU.
