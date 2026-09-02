---
stepsCompleted:
  - step-01-document-discovery
  - step-02-prd-analysis
  - step-03-epic-coverage-validation
  - step-04-ux-alignment
  - step-05-epic-quality-review
  - step-06-final-assessment
includedFiles:
  prdEquivalent:
    - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md
  architecture:
    - docs/history/architecture.md
    - docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/architecture-diagrams.md
  epicsStories:
    - docs/history/epics.md
  ux: []
---

# Implementation Readiness Assessment Report

**Date:** 2026-06-20
**Project:** multimodal-bias multimodal AI bias

## Step 1: Document Discovery

### Files selected for assessment

- PRD-equivalent: `docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md`
- Architecture: `docs/history/architecture.md`
- Architecture companion: `docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/architecture-diagrams.md`
- Epics/Stories: `docs/history/epics.md`
- UX: none. CLI/competition workflow; no UX artifact is expected unless later evidence contradicts this.

### Discovery issues

- No duplicate whole/sharded document formats found.
- No traditional `prd*.md` found. The Canonical SPEC is used as the PRD-equivalent input, consistent with prior project direction.

## Step 2: PRD Analysis

Input read completely:

- `docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/SPEC.md`
- `docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/strategy.md`
- `docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/validation-strategy.md`
- `docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/compliance-references.md`

### Functional Requirements

FR1: The system can ingest the official `open.zip` structure and produce predictions for every `test.csv` sample. Success requires one UTF-8 CSV with exactly `sample_id,label`, 8,500 rows, and labels restricted to `0`, `1`, `2`.

FR2: The system can produce evidence-grounded answers that distinguish resolvable questions from genuinely uncertain questions. Success requires reports with separate ambiguous accuracy, disambiguated accuracy, local balanced accuracy, and failure counts for over-uncertainty and unsupported person selection.

FR3: The system can prevent protected-attribute and appearance-only cues from deciding subjective person judgments. Success requires stereotype-trap and expression-trap audited wrong answers to be traceable to a logged model reason rather than an unlogged rule or silent fallback.

FR4: The system can selectively re-evaluate low-confidence or high-risk answers before final label emission. Success requires conditional verification changes logged with before/after labels, reasons, trigger category, and validation impact; no final label may be produced by pure majority vote or deterministic rule mapping.

FR5: The system can select submission candidates using Private-generalization criteria instead of Public-only tuning. Success requires local robust validation results, parse/image-load failure rates, runtime measurements, and a submission rationale that treats Public score as a sanity signal.

FR6: The system can demonstrate competition-rule compliance for models, data, inference, and outputs. Success requires each candidate run to have a compliance record covering model release cutoff, license/source, no remote API inference, external data provenance, offline execution, and LLM-generated final reasoning.

FR7: The system can generate a second-round-ready artifact set if the team qualifies. Success requires separated train/inference code, environment/version records, model/data references, raw inference logs, and enough run metadata to reproduce the selected Private submission within expected variance.

FR8: The operator can prove that the selected local GPU path can safely produce a compliant full submission before production starts. Success requires stable ten-gate evidence records at 10/10, publishing `GPU_SUBMISSION_READY`, and explicit operator notification with candidate, command, and runtime projection; any failed gate suppresses readiness and production.

FR9: The first pass must generate a structured answer containing selected answer-choice index `0`, `1`, or `2`; `uncertainty_option_index` as integer `0`, `1`, or `2`; short reason; evidence type among `stated_text_fact`, `objective_visible_evidence`, `elimination`, or `insufficient_evidence`; whether the selected answer is the uncertainty option; and output schema version.

FR10: The first pass must favor decisive answers when context or objective visible evidence identifies a person, and must choose uncertainty when the question cannot be resolved without protected-attribute, appearance, expression, posture, clothing, or social-background assumptions.

FR11: Conditional verification must be triggered when the first pass selected uncertainty but the reason or context suggests a stated fact may have been missed; selected a person using appearance, expression, posture, gender, race, age, clothing, attractiveness, or social background as the only support; has low parsing confidence or malformed output; or has evidence type inconsistent with the selected label.

FR12: The verifier must independently generate its own selected answer index and `uncertainty_option_index` in a final JSON/text answer. The system may parse that answer, but must not replace it with a deterministic rule, majority vote, handcrafted answer mapping, or fixed uncertainty label. If neither stage supplies a valid generated candidate, the sample is `unresolved` and submission is blocked.

FR13: Model candidates must be screened in order by eligibility, license/redistribution safety, offline loadability, RTX A6000 48GB memory fit, full-test runtime feasibility, local robust validation performance, and Public score sanity check.

FR14: The recommended model tournament order is corrected Qwen2.5-VL-7B as mandatory control; MiniCPM-V 4.5 and LLaVA-OneVision 7B as first challengers; InternVL3-14B after lower-cost candidates pass; and Qwen2.5-VL-32B-AWQ only after isolated dependency, quality, memory, and runtime checks.

FR15: A submission candidate may advance only if it has a local robust validation report, runtime and memory report, compliance record, raw output audit sample, parse and image-load failure summary, and rationale for why it should generalize to Private/Hidden. Public leaderboard feedback is a smoke test, not an optimizer, and prompts must not be repeatedly tuned against Public score movement.

FR16: Every run must log run id and timestamp, model name/revision/license/source URL if known, prompt version, prompt and schema hashes, sample id, raw first-pass output, raw verifier output when triggered, parsed label, uncertainty option index, output schema version, trigger category, unresolved/error category, image load status, and seconds/sample.

FR17: Validation must include two tiers: `diagnostic-48` for mapping/image/template/engine defects and frozen `shadow-private-300-600` for promotion. Diagnostic results are never tournament ranking scores. Shadow Private must have selection and sealed-holdout splits, with sealed holdout at least 30% and at least 120 samples.

FR18: Shadow Private must contain explicit subset labels for ambiguous, disambiguated_text, visual_grounded, elimination, stereotype_trap, expression_trap, role_or_function, and parsing_stress.

FR19: Each candidate report must include local balanced accuracy, ambiguous accuracy, disambiguated accuracy, worst-subset accuracy, unknown over-selection rate, person over-selection rate, stereotype-trap error count, expression-trap error count, verifier trigger count and flip categories, parse failure rate, image-load failure rate, uncertainty-position accuracy for index 0/1/2, semantic-consistency and unresolved rates, beneficial/harmful/no-effect Verifier flips, peak VRAM, projected 8,500-row runtime, and average/p95 seconds per sample.

FR20: Candidate promotion requires a written decision comparing local robust validation against previous candidate, ambiguous/disambiguated balance, worst-subset regressions, runtime and memory feasibility, compliance status, and Public score only as a secondary sanity signal.

FR21: Validation examples may be public, self-authored, synthetic, or generated with allowed tools only if not derived from evaluation-set wording, choice patterns, question types, images, or inferred answers. Test data must not be used to create validation examples or prompt rules.

FR22: Shadow Private must contain 300–600 reviewed samples; each required subset has at least 30 samples; uncertainty option positions 0/1/2 each cover at least 30% of the suite; ambiguous and resolvable classes each contain at least 120 samples; dataset/image/split/schema manifests are hashed before tournament execution; opening sealed sample-level results for tuning invalidates that holdout version.

FR23: Every candidate must record compliance ledger fields: model name, model revision/checkpoint id, release/publication evidence for cutoff date, license, download/source URL, remote API usage `none`, external data list/licenses, train/test allowed-use status, inference command, environment hash/package list, Reasoner/Verifier prompt versions and SHA-256 hashes, parsed/verification schema versions and uncertainty option-index semantics version, unresolved count/arbitration usage, and selected submission file.

FR24: Before full 8,500-row production inference, the selected candidate must pass target-environment, exact-snapshot/license, data/image, prompt/schema, real-image output, diagnostic failure, peak-VRAM/runtime, persistent artifact, submission validation, and network-disabled smoke gates. Only a 10/10 result may publish `GPU_SUBMISSION_READY`, and the operator must be notified before production starts.

### Non-Functional Requirements

NFR1: Competition code must use Python.

NFR2: Only models whose official open-source weights were public by 2026-05-31 may be used.

NFR3: Remote model APIs are forbidden for inference, including OpenAI API, Gemini API, Hugging Face Inference API, Together AI, OpenRouter, or equivalent remote inference providers.

NFR4: Final label decisions must be derived from generated LLM text, not pure rules, pure majority voting, fixed answer lists, deterministic post-hoc mapping, handcrafted answer mapping, or fixed uncertainty label.

NFR5: Training data, prompt templates, rules, or examples must not be derived from evaluation-set question types, choice patterns, wording, constructions, images, or inferred answers. `test.csv` and images are inference-only inputs.

NFR6: Target organizer/reference environment is RTX A6000 48GB, Python 3.10, CUDA 12.4, PyTorch 2.6.0, Ubuntu 20.04.

NFR7: Final inference should remain practical for organizer guidance: about 0.5 seconds/sample, about 70 minutes for 8,500 test samples, and about 13 minutes for 1,500 Hidden samples unless a slower model is explicitly justified and verified.

NFR8: Public leaderboard results must not be the sole model, prompt, or threshold selection criterion.

NFR9: Submission CSV and code comments must be UTF-8.

NFR10: If selected for second-round evaluation, artifacts must support Private score reproduction and Hidden evaluation, including separated train and inference code, `.py` or `.ipynb` code files, model acquisition path or files, all external data files used, UTF-8 code/comments, error-free library loading, OS/library version record, solution PDF for a 15-minute presentation, and student-status evidence for all team members.

### Additional Requirements

- Non-goals: no web UI/dashboard/interactive labeling product; no Public-only optimization; no fine-tuning requirement before a strong inference baseline; no default 27B two-pass inference unless runtime, memory, compliance, and validation justify it; no manual inference/leakage/reconstruction of test answers.
- Assumptions: primary implementation starts from corrected Qwen2.5-VL-7B control plus staged local-model tournament; exact winning revision remains open until frozen Shadow Private and A6000 gates complete; Reasoner/Verifier use answer-choice indexes and explicit `uncertainty_option_index`; no numeric label has inherent semantic class; independent validation consists of diagnostic-48 and frozen 300–600 Shadow Private with sealed holdout.
- Open questions: winning eligible candidate and exact revision; GPU environment for local full-test inference; sourcing/generating independent validation without evaluation-pattern leakage; second-round PDF/evidence ownership.

### PRD Completeness Assessment

The PRD-equivalent SPEC is materially complete for implementation planning because it provides capabilities, constraints, non-goals, validation strategy, model-selection policy, logging contract, compliance ledger, and GPU production readiness gates. It intentionally leaves candidate model winner, GPU environment, and validation-data sourcing as open decisions to be resolved by later epics. The document set is adequate for epic/story traceability analysis, with one caveat: the requirements are expressed across SPEC companions rather than a single PRD file, so downstream stories must preserve explicit traceability to this combined contract.

## Step 3: Epic Coverage Validation

Input read completely:

- `docs/history/epics.md`

### Epic FR Coverage Extracted

The epics document contains its own implementation-focused FR inventory with 21 FRs and maps them as follows:

- Epic 1: FR1, FR2, FR3, FR4
- Epic 2: FR5, FR6, FR7, FR8, FR12, FR13, FR14, FR15
- Epic 3: FR9, FR10, FR11
- Epic 4: FR16, FR17, FR18
- Epic 5: FR19, FR20, FR21

The epics FR numbering is not identical to the PRD-equivalent extraction in Step 2. Therefore the validation below uses semantic coverage, not numeric equality.

### Coverage Matrix

| PRD FR | Requirement Summary | Epic/Story Coverage | Status |
|---|---|---|---|
| FR1 | Ingest official data and emit valid 8,500-row Multimodal CSV | Epic 1 Stories 1.2–1.4; Epic 2 Story 2.6 | Covered |
| FR2 | Evidence-grounded answers and separate ambiguous/resolvable reporting | Epic 2 Stories 2.2, 2.7; Epic 4 Story 4.5 | Covered |
| FR3 | Prevent protected-attribute/appearance-only subjective decisions | Epic 2 Story 2.7; Epic 3 Stories 3.1, 3.4; Epic 4 Stories 4.1, 4.5 | Covered |
| FR4 | Selective conditional re-evaluation with logged verifier changes | Epic 3 Stories 3.1–3.4; Epic 4 Story 4.10 | Covered |
| FR5 | Select candidates by Private-generalization criteria | Epic 4 Stories 4.6–4.13 | Covered |
| FR6 | Demonstrate competition-rule compliance | Epic 5 Stories 5.1–5.3; model eligibility in Stories 2.8–2.10 and 4.8–4.9 | Covered |
| FR7 | Generate second-round-ready artifact set | Epic 5 Stories 5.2, 5.4, 5.5 | Covered |
| FR8 | Prove GPU path before production and notify operator | Epic 5 Story 5.3 | Covered |
| FR9 | First-pass structured output contract | Epic 2 Story 2.7 | Covered |
| FR10 | First pass decisive/uncertain behavior semantics | Epic 2 Stories 2.2, 2.7; Epic 3 Story 3.1 | Covered |
| FR11 | Conditional verification trigger conditions | Epic 3 Story 3.1 | Covered |
| FR12 | Verifier independent output and fail-closed unresolved behavior | Epic 3 Stories 3.2, 3.3 | Covered |
| FR13 | Candidate screening order | Epic 2 Story 2.8; Epic 4 Stories 4.12, 4.13 | Covered |
| FR14 | Recommended model tournament order | Epic 2 Stories 2.8–2.10; Epic 4 Stories 4.8, 4.9 | Covered |
| FR15 | Submission candidate advancement policy | Epic 4 Stories 4.12, 4.13; Epic 5 Stories 5.1, 5.2 | Covered |
| FR16 | Per-run logging contract | Epic 2 Stories 2.1, 2.4, 2.7; Epic 3 Story 3.2; Epic 5 Story 5.1 | Covered |
| FR17 | Diagnostic-48 and Shadow Private validation tiers | Epic 4 Stories 4.1–4.5 | Covered |
| FR18 | Required Shadow Private subset labels | Epic 4 Stories 4.1, 4.3, 4.5 | Covered |
| FR19 | Candidate metrics report contents | Epic 4 Story 4.5; runtime subset in Story 4.11 | Covered |
| FR20 | Candidate promotion written comparison | Epic 4 Stories 4.12, 4.13 | Covered |
| FR21 | Validation data safety/no evaluation-derived examples | Epic 4 Stories 4.1, 4.2, 4.4; policy noted in Additional Requirements | Covered |
| FR22 | Shadow Private size, balance, hash, sealed-holdout rules | Epic 4 Stories 4.2, 4.3, 4.4 | Covered |
| FR23 | Compliance ledger fields | Epic 5 Story 5.1 | Covered |
| FR24 | Ten GPU readiness gates and operator notification | Epic 5 Story 5.3 | Covered |

### Missing Requirements

No uncovered PRD-equivalent FRs were found after the Correct Course changes.

### Coverage Statistics

- Total PRD-equivalent FRs extracted: 24
- FRs covered in epics/stories: 24
- Coverage percentage: 100%
- Notes: Coverage is semantic because `epics.md` decomposes the canonical contract into a different 21-item implementation FR inventory. This is acceptable if later story files retain explicit story-level links back to their owning epic requirements.

## Step 4: UX Alignment Assessment

### UX Document Status

No UX design document was found under `docs/history`.

### UI/UX Implication Assessment

UX/UI is not implied for this project:

- SPEC explicitly says not to build a web UI, dashboard, or interactive labeling product.
- Architecture defines the system as an offline multimodal ML inference / competition CLI pipeline, not a web/mobile/API/full-stack product.
- Epics explicitly state that no UX-DR items apply and that public interfaces are CLI commands and Python module interfaces.

The only operator-facing interaction is the GPU readiness notification before 8,500-row production. This is covered as a CLI/artifact/operator-notification requirement in Epic 5 Story 5.3 rather than as UI design.

### Alignment Issues

None found.

### Warnings

No UX warning is required unless the project later adds a dashboard, labeling UI, web API, or interactive review product. If that scope changes, a UX spec and architecture update would be required before implementation.

## Step 5: Epic Quality Review

### Review Scope

Reviewed:

- `docs/history/epics.md`
- Existing detailed story files under `docs/history/stories/`

### Epic Structure Validation

| Epic | User Value Focus | Independence | Assessment |
|---|---|---|---|
| Epic 1: Reproducible Data-Ready Competition Workspace | User can initialize, validate, and safely load competition data | Stands alone | Pass |
| Epic 2: Offline Evidence-Grounded Submission Pipeline | User can produce a valid Reasoner-only submission path with raw audit evidence | Depends only on Epic 1 | Pass |
| Epic 3: Bias-Safe Conditional Verification and Arbitration | User can improve risky predictions and audit verifier impact | Depends on Epic 1–2 outputs, no future epic dependency | Pass |
| Epic 4: Private-Generalization Validation and Candidate Selection | User can build Shadow Private, run tournament, select defensible candidate | Depends on candidate/run outputs from earlier epics, no forward dependency | Pass |
| Epic 5: Compliance and Second-Round Reproducibility Package | User can prove compliance, readiness, and reproducibility | Depends on selected candidate; production explicitly separated after readiness | Pass |

### Story Structure and Dependency Assessment

Strengths:

- The prior circularity around `reasoner_verifier_conflict` is corrected: Story 3.1 owns only six pre-Verifier triggers; Story 3.2 owns post-Verifier conflict events.
- Reasoner v2/v3 ambiguity is corrected at epic level: Stories 2.2 and 2.5 are historical v2 baselines; Story 2.7 owns active v3.
- Epic 4 is now decomposed into schema, sourcing, review, freezing, metrics, harness, diagnostic, conditional advanced models, sealed A/B, runtime, comparison, and selection. This fixes prior oversized validation/model-selection stories.
- Epic 5 now separates pre-production compliance/readiness from validated 8,500-row production artifacts. Story 5.3 owns readiness and notification; Stories 5.4–5.5 require validated production artifacts.
- Corrected execution gates prevent Epic 3/4/5 from starting in an unsafe order.

### Findings by Severity

#### Critical Violations

None found in the corrected epic/story structure.

#### Major Issues

M1: Detailed story-file readiness is not aligned with the corrected integrated execution order.

- Evidence: `epics.md` says Gate A starts with Story 2.7, then 2.8, 2.9/2.10, then 3.1–3.4. Existing detailed story files currently cover 1.1–2.6 and reopened backlog files for 3.1–3.3. There are no detailed story files yet for 2.7, 2.8, 2.9, 2.10, 3.4, or Epic 4/5 stories.
- Impact: The epic plan is ready for sequencing, but direct implementation is not ready until the next active story file is created from the corrected epic contract. Starting from existing 3.x files before 2.7 would violate the corrected dependency order.
- Recommendation: After IR, run sprint planning, then create Story 2.7 as the first executable story. Do not run `dev-story` on 3.1/3.2/3.3 until 2.7 and prerequisite Gate A stories are completed or explicitly replanned.

M2: Reopened 3.x story files contain historical done logs plus corrective unchecked work.

- Evidence: `docs/history/stories/3-1-detect-verification-trigger-conditions.md`, `3-2-run-conditional-verifier-for-triggered-samples.md`, and `3-3-arbitrate-final-labels-with-evidence-preservation.md` are `Status: backlog` and include unchecked corrective work, but also contain historical checked tasks and dev-agent records from the pre-correction implementation.
- Impact: This is acceptable as historical context, but implementation agents may misread old checked tasks as current completion unless the corrective section is treated as authoritative.
- Recommendation: When each 3.x story becomes active, regenerate or normalize the story file so the corrective work is the current task list and historical implementation is clearly non-authoritative reference.

#### Minor Concerns

m1: Some story titles are implementation-heavy, for example “Implement Local VLM Model Adapter” and “Compute Robust Validation Metrics.” Their user stories and acceptance criteria still express user value, so this is not a blocker.

m2: Acceptance criteria are testable and mostly BDD-style, but the detailed existing story files use numbered criteria and task lists rather than uniform Given/When/Then blocks. This is acceptable if the create-story workflow later normalizes active stories.

### Best Practices Compliance Checklist

- Epic delivers user value: Pass
- Epic can function independently in sequence: Pass
- Stories appropriately sized after correction: Pass, with detailed active-story creation still required
- No forward dependencies in `epics.md`: Pass
- Database/entity timing: Not applicable; no database architecture
- Starter template requirement reflected in Epic 1 Story 1.1: Pass
- Clear acceptance criteria: Pass with minor formatting caveat
- Traceability to FRs maintained: Pass

### Quality Review Conclusion

Correct Course materially fixed the prior structural blockers in the epic plan. The remaining issue is not the epic/story architecture itself; it is execution readiness. The project should not jump straight into GPU production or later Epic 3/4/5 development. The safe next move is sprint planning followed by creation of the first corrected active story, Story 2.7.

## Summary and Recommendations

### Overall Readiness Status

NEEDS WORK

The corrected planning artifacts are ready for sprint planning and next-story creation, but not ready for direct implementation execution yet.

### Critical Issues Requiring Immediate Action

No critical planning-structure issues remain after the Correct Course changes.

### Issues Requiring Attention

1. Major: Active detailed story readiness is incomplete for the corrected execution order. Story 2.7 is the first required active story, but no detailed Story 2.7 file exists yet.
2. Major: Existing 3.x story files are reopened backlog stories with corrective work and historical done logs mixed in. They should not be treated as implementation-ready until regenerated or normalized when they become active.
3. Minor: Some story titles are implementation-heavy, though their user stories and acceptance criteria preserve user value.
4. Minor: Existing detailed story files are not uniformly BDD-formatted, though their criteria are testable.

### Recommended Next Steps

1. Run `bmad-sprint-planning` to create an explicit sprint status from the corrected integrated execution order.
2. Run `bmad-create-story` for Story 2.7: Implement Reasoner v3 Option-Index Contract.
3. Run implementation only after Story 2.7 is created and reviewed as the active story.
4. Do not run Epic 3/4/5 implementation directly yet. Gate A starts with 2.7, then 2.8, then 2.9/2.10, then 3.1–3.4.
5. Do not start GPU 8,500-row production. GPU production remains blocked until Story 5.3 publishes 10/10 `GPU_SUBMISSION_READY` and the operator is explicitly notified.

### Final Note

This assessment identified 0 critical issues, 2 major issues, and 2 minor concerns. The major issues are process/readiness issues, not requirement-coverage failures. The Correct Course changes are directionally correct and the plan is coherent, but the next executable unit must be created before implementation continues.

Assessor: Codex using `bmad-check-implementation-readiness`
