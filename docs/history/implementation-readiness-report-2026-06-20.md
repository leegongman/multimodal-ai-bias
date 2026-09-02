---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md
  - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/strategy.md
  - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/validation-strategy.md
  - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/compliance-references.md
  - _bmad-output/specs/spec-reasoner-v3-contract/SPEC.md
  - _bmad-output/specs/spec-reasoner-v3-contract/output-contract.md
  - _bmad-output/specs/spec-shadow-private-validation/SPEC.md
  - _bmad-output/specs/spec-shadow-private-validation/dataset-contract.md
  - _bmad-output/specs/spec-shadow-private-validation/evaluation-and-freeze-policy.md
  - docs/history/architecture.md
  - docs/history/epics.md
workflowType: implementation-readiness
project_name: Multimodal 236722 Multimodal AI Bias Solution
date: 2026-06-20
status: complete
overallReadiness: NOT READY
assessor: Codex using bmad-check-implementation-readiness
---

# Implementation Readiness Assessment Report

**Date:** 2026-06-20
**Project:** Multimodal 236722 Multimodal AI Bias Solution

## Document Inventory

### PRD-equivalent Requirements

- Canonical SPEC and its strategy, validation, and compliance companions
- Reasoner v3 contract and output-contract companion
- Shadow Private contract and dataset/freeze-policy companions

### Architecture

- `docs/history/architecture.md`

### Epics and Stories

- `docs/history/epics.md`

### UX

- Not applicable: offline CLI project with no UI requirement

### Discovery Issues

- No duplicate whole/sharded documents found.
- No separate PRD file exists; user confirmed the Canonical SPEC set as PRD-equivalent.

## PRD Analysis

### Functional Requirements

FR1: The system must ingest the official Multimodal `open.zip` structure and produce a prediction for every `test.csv` sample.

FR2: The system must validate required data files, CSV columns, UTF-8 encoding, image paths, answer fields, and sample ordering before inference.

FR3: The system must parse each row into a typed record containing `sample_id`, image reference, context, question, and exactly three ordered answers.

FR4: The system must load and preprocess local images for multimodal inference while preserving per-sample image status and hash evidence.

FR5: The system must construct versioned evidence-grounded prompts that select a person only from stated or objective evidence and select the uncertainty answer when evidence is insufficient without protected-attribute or appearance-only assumptions.

FR6: The system must run eligible open-source VLM weights locally through model adapters and preserve raw generated text, generation metadata, and timing.

FR7: Reasoner v3 must generate a selected answer-choice index, integer `uncertainty_option_index`, evidence, evidence type, uncertainty signal, protected-attribute risk, and schema version for every valid sample.

FR8: The parser must accept only the approved final marker and strict schema, enforce `uncertainty_signal == (label == str(uncertainty_option_index))` and evidence consistency, preserve invalid raw output, and never repair a candidate through fixed position, regex, or fallback mapping.

FR9: The system must trigger verification only for explicit risk categories while interpreting semantics from generated option-index fields rather than a numeric label.

FR10: The Verifier must run only for triggered samples, independently generate its own selected label and uncertainty index under the same semantic invariant, and preserve raw output, prompt/schema identity, before/after lineage, failures, and skips.

FR11: Arbitration must keep or flip only between valid LLM-generated candidates; evidence insufficiency may use only a valid stage-generated uncertainty-choice index, and if neither candidate is valid the sample must be unresolved and submission blocked.

FR12: The system must generate `final_predictions.csv` and a UTF-8 Multimodal `submission.csv` with exactly `sample_id,label`, 8,500 ordered rows, and labels restricted to `0`, `1`, `2`.

FR13: Submission artifacts must be generated only through the approved submission boundary from validated final predictions and only when unresolved count is zero.

FR14: Every run must create immutable artifacts containing resolved configuration, environment, prompt/schema/image/model identities, raw/parsed Reasoner output, verification, arbitration, metrics, compliance, and submission lineage.

FR15: Repeatable CLI commands must cover data validation, model smoke, inference, triggered verification, submission, validation/comparison, compliance audit, and readiness operations.

FR16: Local evaluation must report balanced, ambiguous/resolvable, worst-subset, uncertainty-position, semantic-consistency, over-selection, stereotype/expression, parse/image/unresolved, Verifier flip, latency, peak-VRAM, and projected full-path runtime metrics.

FR17: The system must support a separate diagnostic-48 and an independently sourced, reviewed, versioned, hashed, frozen 300–600 sample Shadow Private suite with selection/sealed-holdout splits and required subset/position coverage.

FR18: The system must integrate eligible candidate models through official local multimodal serialization and execute a staged tournament from eligibility and real-image smoke through diagnostic, Reasoner-only selection, sealed shortlist, Verifier A/B, runtime, compliance, comparison, and promotion rationale.

FR19: Each candidate must generate a compliance record covering model revision/hash, cutoff evidence, license/source/custom code, API usage, data provenance, prompt/schema hashes, environment, inference command, unresolved count, arbitration use, and selected file.

FR20: The system must prepare offline reproduction and second-round artifacts including separated code, environment versions, model/data acquisition evidence, raw logs, run metadata, checklist, and handoff summary.

FR21: Before 8,500-row production, the system must evaluate ten GPU submission-readiness gates, publish `GPU_SUBMISSION_READY` only on a 10/10 result, suppress readiness on any blocker, and explicitly notify the user with the selected candidate and command before production starts.

Total FRs: 21

### Non-Functional Requirements

NFR1: Competition implementation must use Python and remain compatible with Python 3.10.

NFR2: The final path must run in the organizer reference environment: RTX A6000 48GB, CUDA 12.4, PyTorch 2.6.0, and Ubuntu 20.04.

NFR3: All inference must load weights on participant-controlled infrastructure without remote model-response APIs or network fallback.

NFR4: Only officially open-source weights publicly available by 2026-05-31 may be used, with exact revision and license evidence.

NFR5: Final labels must derive from generated LLM text; pure rules, majority voting, fixed answer lists, deterministic post-hoc mapping, and invented fallback labels are forbidden.

NFR6: Evaluation data is inference-only and must not supply wording, patterns, images, inferred answers, examples, prompt rules, validation data, or training data.

NFR7: Full inference should fit the official guidance of about 70 minutes for 8,500 rows and 13 minutes for 1,500 Hidden rows; the project uses a 63-minute internal full-path target.

NFR8: Public leaderboard score must be secondary and cannot be the sole model, prompt, threshold, Verifier, or submission-selection criterion.

NFR9: CSV, JSON, YAML, code comments, and submission artifacts must be UTF-8.

NFR10: Dependencies, model revisions/snapshot hashes, prompts, schemas, datasets, splits, environments, and run outputs must be pinned or hashed for reproducibility.

NFR11: Raw generation, parsed semantics, image status, triggers, candidates, flips, arbitration, failures, metrics, and compliance evidence must remain auditable.

NFR12: The solution remains an offline modular CLI/file pipeline with no required database, web UI, public network API, or interactive labeling product.

NFR13: CPU-safe automated tests must cover schemas, parsing, semantic invariants, artifacts, validation, compliance, and submission boundaries without GPU dependencies.

NFR14: GPU load, real-image, VRAM, runtime, offline, and submission checks must be explicit smoke/integration operations rather than default unit tests.

NFR15: Raw data, model weights, datasets, runs, and submissions must remain outside importable source code and final publication must be atomic/fail-closed.

NFR16: Sealed holdout sample-level content and errors must remain hidden from prompt/model tuning until shortlist selection; opening it invalidates that holdout version.

Total NFRs: 16

### Additional Requirements

- Reasoner v2 remains immutable as the mapping-only A/B control.
- The strict Reasoner v3 final record uses `FINAL_ANSWER_JSON` and schema version `reasoner_output_v3`.
- Required evidence types are `stated_text_fact`, `objective_visible_evidence`, `elimination`, and `insufficient_evidence`.
- Required validation subsets are `ambiguous`, `disambiguated_text`, `visual_grounded`, `elimination`, `stereotype_trap`, `expression_trap`, `role_or_function`, and `parsing_stress`.
- Each subset needs at least 30 samples; uncertainty positions 0/1/2 each need at least 30% coverage; ambiguous and resolvable classes each need at least 120 samples.
- Sealed holdout is at least 30% of Shadow Private and at least 120 samples.
- Candidate order begins with corrected Qwen2.5-VL-7B control, then MiniCPM-V 4.5 and LLaVA-OneVision 7B, then InternVL3-14B, with Qwen2.5-VL-32B-AWQ conditional.
- Candidate A/B must not change prompt contract, model, image budget, engine, and Verifier simultaneously.
- Public submissions are limited to milestone sanity checks for locally promoted candidates.
- Final production requires compliance blockers zero, unresolved zero, target runtime/VRAM success, network-disabled smoke, and atomic submission validation.

### PRD Completeness Assessment

The Canonical SPEC set is detailed enough to act as a PRD-equivalent for this offline competition pipeline. Functional behavior, rule compliance, semantic invariants, independent validation, tournament sequencing, operational readiness, and non-goals are explicit. The main traceability risk is that the newly explicit operator-notification behavior is a distinct functional requirement (FR21) and must be represented consistently in the Epic requirements inventory and coverage map rather than only as Story 5.3 acceptance criteria. Open questions about the winning model, GPU provider, validation sources, and second-round ownership are intentionally evidence- or operator-dependent and do not block planning validation.

## Epic Coverage Validation

### FR Coverage Matrix

| FR | Epic/Story coverage | Status |
|---|---|---|
| FR1 | Epic 1; Stories 1.1, 1.2 | Covered |
| FR2 | Epic 1; Story 1.2 | Covered |
| FR3 | Epic 1; Story 1.3 | Covered |
| FR4 | Epic 1; Story 1.4 | Covered |
| FR5 | Epic 2; Stories 2.2, 2.7 | Covered |
| FR6 | Epic 2; Stories 2.3, 2.4, 2.8; Story 4.4 | Covered |
| FR7 | Epic 2; Stories 2.2, 2.5, 2.7 | Covered |
| FR8 | Epic 2; Stories 2.5, 2.7 | Covered |
| FR9 | Epic 3; Story 3.1 | Covered |
| FR10 | Epic 3; Stories 3.2, 3.4 | Covered |
| FR11 | Epic 3; Stories 3.3, 3.4 | Covered |
| FR12 | Epic 2; Stories 2.6, 2.7; Story 5.3 | Covered |
| FR13 | Epic 2; Story 2.6 | Covered |
| FR14 | Epic 2; Stories 2.1, 2.4, 2.7, 2.8; Story 5.3 | Covered |
| FR15 | Epic 2; Stories 2.1, 2.6 | Covered |
| FR16 | Epic 4; Stories 4.2, 4.3, 4.4 | Covered |
| FR17 | Epic 4; Stories 4.1, 4.2 | Covered |
| FR18 | Epic 4; Stories 4.2, 4.4, 4.5, 4.6; Story 2.8 | Covered |
| FR19 | Epic 5; Stories 5.1, 5.2, 5.3; Story 2.8 | Covered |
| FR20 | Epic 5; Stories 5.2, 5.3, 5.4, 5.5 | Covered |
| FR21 | Story 5.3 implements the behavior, but FR21 is absent from the requirements inventory, FR coverage map, Epic 5 FR list, and Story 5.3 requirements line | Partial — traceability gap |

### Missing or Partially Traced Requirements

**FR21 — GPU readiness verdict and explicit operator notification**

- Required behavior is substantively specified by Story 5.3, including ten gates, `GPU_SUBMISSION_READY`, notification suppression on failure, and pre-production operator notification.
- Formal traceability is incomplete because the epic document defines only FR1–FR20 and therefore cannot map Story 5.3 to FR21.
- Required correction: add FR21 to the Functional Requirements inventory, FR Coverage Map, Epic 5 coverage list, and Story 5.3 `Requirements` field.

### Coverage Statistics

- Total PRD-equivalent FRs: 21
- Formally mapped FRs: 20
- Partially traced FRs: 1
- Completely missing implementation behavior: 0
- Formal traceability coverage: 95.2%
- Behavioral story coverage: 100%, subject to formalizing FR21

### Coverage Assessment

The epics and stories cover the full intended behavior, including the corrected option-index semantics, independent Shadow Private validation, staged model tournament, and GPU submission readiness. Implementation should not begin from the current artifacts until FR21 is formally added, because readiness notification is a release gate and must be testable and traceable as a first-class requirement rather than an unnumbered additional requirement.

## UX Alignment Assessment

### UX Document Status

Not found, and not required for the defined product scope.

### Alignment Issues

None. The Canonical SPEC explicitly excludes a web UI, dashboard, and interactive labeling product. The architecture consistently defines an offline packaged Python CLI with file artifacts as the public interaction boundary, and the epics implement that boundary through repeatable commands and auditable outputs.

### Warnings

No UX warning is required. A UX specification would become necessary only if scope changes to include a web/mobile interface, dashboard, network API, or interactive labeling workflow. Such a change would require an explicit architecture revision under NFR12.

## Epic Quality Review

### Epic-Level Assessment

| Epic | User value | Independence from later epics | Story/AC quality | Result |
|---|---|---|---|---|
| Epic 1 | Reproducible, validated competition workspace | Yes | Starter requirement and failure paths are explicit | Pass |
| Epic 2 | Locally generated, auditable submission path | Yes in intended flow | Contract ownership overlaps between legacy stories and Story 2.7 | Needs correction |
| Epic 3 | Conditional verification and safe arbitration | Intended to depend only on Epics 1–2 | One trigger is temporally impossible in the stated lifecycle; corrected execution order delays Story 3.4 until after Story 4.4 | Needs correction |
| Epic 4 | Independent Private-generalization evidence and candidate selection | Depends on prior inference/verification capabilities as expected | Two stories are too large for reliable execution | Needs decomposition |
| Epic 5 | Compliance, GPU readiness, and reproducible handoff | Depends only on prior candidate artifacts | Clear user/operator outcomes, but FR21 traceability and executable story artifacts are incomplete | Needs correction |

All five epic goals express user or operator outcomes rather than infrastructure-only milestones. Epic 1's setup story is acceptable because it is the architecture-mandated starter and immediately establishes a reproducible executable workspace. No database/entity-timing issue applies. The absence of CI/CD is not treated as a defect for this offline competition pipeline because reproducible local commands, locked environments, and audit artifacts are the required delivery mechanism.

### Critical Violations

#### C1. `reasoner_verifier_conflict` is an unreachable pre-Verifier trigger

Story 3.1 says trigger detection can assign `reasoner_verifier_conflict`, while Story 3.2 runs the Verifier only for rows already selected by Story 3.1. A Reasoner–Verifier conflict cannot exist before a Verifier candidate exists. As written, this creates a lifecycle cycle and makes the trigger either unreachable or dependent on an undocumented unconditional Verifier pass.

**Required remediation:** split trigger phases. Story 3.1 should define only pre-Verifier triggers. `reasoner_verifier_conflict` must be a post-Verifier comparison/audit flag evaluated for already verified rows, with explicit ownership in Story 3.2, 3.3, or 3.4. Tests must prove it never causes an unconditional Verifier pass.

### Major Issues

#### M1. Legacy Reasoner stories conflict with the v3 contract owner

Stories 2.2 and 2.5 still describe the older label-centric prompt/parsed artifact. Story 2.2 does not require `uncertainty_option_index` or `schema_version`; Story 2.5's parsed output omits both and does not state the v3 semantic invariant. Story 2.7 later corrects these concerns, leaving overlapping and contradictory acceptance criteria for the same prompt/parser components.

**Required remediation:** either update Stories 2.2 and 2.5 to the v3 contract and make Story 2.7 an explicit migration/A-B story, or mark their old acceptance criteria as completed v2 baseline behavior that Story 2.7 supersedes. There must be one unambiguous final contract for implementation.

#### M2. Corrected execution order violates epic completion order

Gate C specifies `Story 2.8 → Story 4.4 → Story 3.4 → Story 4.5 → Story 4.6`. This starts Epic 4 before Epic 3 is complete and conflicts with the stated architecture order, which corrects Verifier behavior before tournament execution. It also weakens Epic 3's independent completion test.

**Required remediation:** complete Story 3.4 after Stories 3.1–3.3 and before Story 4.4, or explicitly redefine Story 3.4 as an Epic 4 tournament-analysis story and renumber it. Preferred order: `2.7 → 3.1 → 3.2 → 3.3 → 3.4`, then `2.8 → 4.4 → 4.5 → 4.6` after the Shadow Private foundation.

#### M3. Story 2.8 is epic-sized

One story covers eligibility evidence, official serialization, dependency isolation, AWQ isolation, local loading, real-image v3 smoke, VRAM/latency capture, and integration of up to five materially different model families. It cannot be estimated or completed independently with stable risk.

**Required remediation:** separate a common eligibility/adapter-smoke harness from candidate-specific integration stories. Keep the conditional 32B-AWQ path as its own story so failure or environment isolation does not block all challengers.

#### M4. Story 4.2 is epic-sized and mixes production work with human governance

Building, reviewing, balancing, deduplicating, splitting, sealing, and hashing 300–600 multimodal examples—while enforcing provenance and human review—is not a single implementation-sized story.

**Required remediation:** split into source/authoring and provenance, schema/quality validation, independent review and balancing, and freeze/seal publication stories. Define the human reviewer handoff and the evidence that permits freeze.

#### M5. Story 4.4 is epic-sized

The story combines tournament orchestration, v2/v3 control A/B, diagnostic-48, Reasoner-only selection, sealed shortlist evaluation, two Verifier configurations, runtime/compliance gates, Public sanity checks, and immutable decisions.

**Required remediation:** split tournament harness/frozen experiment contract from diagnostic promotion, sealed shortlist, Verifier A/B, and final runtime/compliance stages. Each stage should emit a stable artifact consumed by the next.

#### M6. New integrated-sprint stories lack executable story artifacts

Dedicated story files exist only for Stories 1.1–3.3. No context-filled story artifact exists for Stories 2.7, 2.8, 3.4, 4.1–4.6, or 5.1–5.5. The epic document is enough for portfolio planning but not for `bmad-dev-story` execution, test task breakdown, or per-story status tracking.

**Required remediation:** after correcting/decomposing the epics, run sprint planning to establish the authoritative order and status, then create executable story artifacts one at a time in that dependency order. Do not create implementation files from the current oversized definitions.

#### M7. FR21 is not traceable from Epic 5 or Story 5.3

The GPU readiness behavior is testable in Story 5.3, but the story's requirements line and the Epic 5 coverage declaration omit FR21 because the functional inventory ends at FR20.

**Required remediation:** apply the FR21 mapping correction identified in the coverage assessment before sprint planning.

### Minor Concerns

#### m1. Story 5.3 gate identity should be normative

The ten gate categories are listed in prose, but stable gate IDs, per-gate result fields, and the exact readiness artifact are not named in the story. This makes 10/10 testing and failure reporting more ambiguous than necessary.

**Recommended remediation:** define ten stable gate IDs and a machine-readable readiness report schema containing pass/fail, evidence path, blocker, candidate, command, runtime projection, and notification status.

#### m2. Story status is split across artifacts

Existing dedicated story files carry `done`/`backlog`, while the canonical epic document contains corrected and new work without status. This is manageable after sprint planning but currently obscures which old acceptance criteria are historical and which are active.

**Recommended remediation:** generate `sprint-status.yaml` only after the corrected story set is approved, then use it as the single execution-status view.

### Acceptance-Criteria Assessment

Most stories use testable Given/When/Then criteria and include important failure behavior such as invalid parse, unresolved submission blocking, compliance failure, data mismatch, and readiness suppression. The principal AC defects are the lifecycle impossibility in C1, contract ambiguity in M1, and excessive scope in M3–M5. No generic database, frontend, or authentication boilerplate contaminates the plan.

## Summary and Recommendations

### Overall Readiness Status

**NOT READY**

The product direction and architecture are coherent, and all 21 functional behaviors have a plausible story path. Implementation readiness nevertheless fails because the conditional-Verifier lifecycle contains one critical circularity, the v3 contract has overlapping legacy ownership, three stories are too large for dependable execution, the integrated order crosses epic boundaries incorrectly, and the new sprint lacks executable story artifacts.

This is a planning-readiness failure, not evidence that the selected modeling strategy is wrong. No GPU production run should start from this plan.

### Critical Issues Requiring Immediate Action

1. Remove `reasoner_verifier_conflict` from the pre-Verifier trigger set and define it as a post-Verifier comparison/audit flag with explicit lifecycle ownership.
2. Establish one final Reasoner v3 contract across Stories 2.2, 2.5, and 2.7; preserve v2 only as an explicitly superseded A/B baseline.
3. Add FR21 to the requirements inventory, FR coverage map, Epic 5 coverage, and Story 5.3 requirements.
4. Move Story 3.4 before tournament execution or renumber it into Epic 4 so Epic 3 completes without a future-epic dependency.
5. Decompose Stories 2.8, 4.2, and 4.4 before creating implementation stories.

### Recommended Next Steps

1. Run a focused `bmad-correct-course` update on `docs/history/epics.md` to resolve C1, M1, M2, M3, M4, M5, and M7 while preserving the approved strategy.
2. Re-run `bmad-check-implementation-readiness` against the corrected artifact; the target is zero critical issues, zero formal FR gaps, and no forward dependency.
3. Run `bmad-sprint-planning` after the corrected epics pass readiness so `done`, `backlog`, and corrective work have one authoritative execution order and status view.
4. Run `bmad-create-story` from that sprint plan, beginning with the decomposed Reasoner v3 migration story. Create only the next implementation-ready story at each handoff.
5. Implement and verify Gate A, then Gate B, then candidate integration/tournament. Do not treat Public LB or the current 0.91 result as the primary selection signal.
6. Notify the user only when Story 5.3 produces a genuine 10/10 `GPU_SUBMISSION_READY` result. Until then, GPU submission production is blocked.

### Final Note

This assessment identified 10 issues: 1 critical violation, 7 major issues, and 2 minor concerns. UX alignment is valid and requires no work. The critical lifecycle defect and major story-structure issues must be corrected before implementation proceeds.

**Assessment date:** 2026-06-20  
**Assessor:** Codex using `bmad-check-implementation-readiness`
