# Sprint Change Proposal: IR 결함 교정 및 실행 가능 백로그 재구성

**작성일:** 2026-06-20
**프로젝트:** Multimodal 236722 Multimodal AI Bias Solution
**변경 범위:** Moderate — 기존 목표와 Epic 1~5는 유지하되 요구사항 추적성, Verifier 생명주기, Story 소유권·크기·순서를 교정한다.
**처리 모드:** Batch
**승인 상태:** 승인 및 계획 문서 적용 완료 (2026-06-20)

## 1. Issue Summary

2026-06-20 Implementation Readiness 평가가 `NOT READY`를 판정했다. 모델 전략 자체가 아니라 계획 문서에 다음 실행 결함이 남아 있다.

1. Story 3.1은 Verifier 실행 전 단계에서 `reasoner_verifier_conflict`를 trigger로 계산하도록 요구하지만, conflict는 Verifier 결과가 생성된 뒤에만 존재한다.
2. Stories 2.2·2.5의 완료된 v2 계약과 Story 2.7의 활성 v3 계약이 같은 prompt/parser 최종 상태를 서로 다르게 정의한다.
3. GPU readiness/operator notification 요구가 Story 5.3에는 있으나 FR21로 정식 추적되지 않는다.
4. Story 3.4가 Story 4.4 뒤에 배치되어 Epic 3이 Epic 4 없이 완료되지 않는다.
5. Stories 2.8, 4.2, 4.4가 여러 독립 산출물과 위험을 한 Story에 묶는다.
6. 신규 통합 스프린트 Story의 전용 실행 파일과 authoritative sprint status가 없다.

추가 문서 대조에서 Architecture inference diagram이 Reasoner parsing 전에 verification trigger를 계산하도록 표현한 순서 결함도 확인했다. Trigger가 `parse_status`, selected index, uncertainty index와 evidence semantics를 사용하므로 parsing이 반드시 먼저다.

### Trigger Classification

- 원래 요구사항의 생명주기 오해
- 완료된 v2 baseline과 corrective v3 목표의 소유권 충돌
- 구현 전 백로그 품질·크기 결함
- 신규 운영 요구의 정식 추적성 누락

### Evidence

- `docs/history/implementation-readiness-report-2026-06-20.md`: Critical 1, Major 7, Minor 2
- `docs/history/epics.md`: Story 3.1 pre-trigger 목록에 `reasoner_verifier_conflict` 포함
- `docs/history/specs/spec-multimodal-236722-multimodal-ai-bias/architecture-diagrams.md`: Reasoner → Trigger → Parse 순서
- `_bmad-output/specs/spec-reasoner-v3-contract/`: parse 후 semantic invariant와 downstream lineage 요구
- `docs/history/epics.md`: FR inventory/coverage가 FR20에서 종료되지만 Story 5.3은 별도 GPU notification behavior를 요구

## 2. Change Navigation Checklist

### 2.1 Trigger and Context

- [x] 1.1 Triggering scope: Stories 2.2, 2.5, 2.7, 3.1~3.4 및 IR 재검사.
- [x] 1.2 Core problem: 전략은 타당하지만 생명주기, 최종 계약 소유권, Story 크기와 FR traceability가 구현 가능한 상태가 아니다.
- [x] 1.3 Evidence: IR report, canonical SPEC companions, architecture, epics, Reasoner v3/Shadow Private contracts.

### 2.2 Epic Impact

- [x] 2.1 Epic 2는 완료된 v2 baseline과 활성 v3 migration을 명시적으로 분리한다.
- [x] 2.2 Epic 3은 pre-Verifier trigger와 post-Verifier comparison event를 분리하고 Story 3.4까지 연속 완료한다.
- [x] 2.3 Epic 4는 corpus 제작·검수·freeze와 tournament 단계를 implementation-sized Stories로 분해한다.
- [x] 2.4 Epic 5는 FR21과 stable readiness gate IDs를 소유한다.
- [x] 2.5 새 Epic은 필요 없다. 기존 목표와 capability는 유지된다.
- [x] 2.6 Epic 4의 candidate selection과 Epic 5의 submission release를 구분해 future-epic dependency를 제거한다.

### 2.3 Artifact Impact

- [x] 3.1 Canonical SPEC: GPU readiness를 CAP-8로 명시하고 companion의 기존 10-gate 요구에 연결했다.
- [x] 3.2 Architecture: parse/trigger/compare/arbitration 순서, event taxonomy, readiness artifact/module을 교정했다.
- [N/A] 3.3 UX: offline CLI non-goal이므로 영향 없음.
- [x] 3.4 Epics/Stories: FR21, v2 supersession, Story decomposition, corrected DAG를 반영했다.
- [x] 3.5 Existing story files: Stories 2.2·2.5에 v2 baseline supersession note, Stories 3.1~3.3에 lifecycle correction을 반영했다.
- [N/A] 3.6 `sprint-status.yaml`: 아직 없으며 승인된 교정 후 Sprint Planning에서 생성한다.

### 2.4 Path Forward

- [x] 4.1 Direct Adjustment: **Viable**, effort Medium-High, risk Medium.
- [x] 4.2 Rollback: **Not viable**. v2 artifacts는 실험 control로 필요하고 기존 정상 기반을 폐기할 이유가 없다.
- [x] 4.3 MVP Review: **Not required**. CAP-1~CAP-7과 경쟁 목표는 그대로 달성 가능하다.
- [x] 4.4 Selected path: Direct Adjustment + backlog decomposition + dependency correction + IR revalidation.

### 2.5 Proposal and Handoff

- [x] 5.1 Issue summary와 evidence 작성.
- [x] 5.2 Epic/artifact impact 작성.
- [x] 5.3 권장 경로와 대안 평가 작성.
- [x] 5.4 MVP 영향과 실행 순서 작성.
- [x] 5.5 PO/Developer/Reviewer/User handoff 작성.
- [x] 6.1 적용 가능한 checklist 검토 완료.
- [x] 6.2 proposal consistency 검토 완료.
- [x] 6.3 사용자가 2026-06-20 명시적으로 승인했다.
- [N/A] 6.4 sprint status는 승인 후 `bmad-sprint-planning`에서 신규 생성.
- [x] 6.5 승인된 planning artifact 적용 완료. 다음 handoff는 IR 재검사다.

## 3. Impact Analysis

### Canonical SPEC

기존 CAP-1~CAP-7은 유지한다. GPU production release behavior를 CAP-8로 명시해 이미 compliance companion에 존재하는 10/10 요구와 정식 연결한다. MVP 범위 확대가 아니라 기존 운영 gate의 traceability 교정이다.

### Architecture

기술 스택과 modular CLI 구조는 바꾸지 않는다. 다음 계약만 수정한다.

- Reasoner raw output은 먼저 parse/semantic validation을 거친다.
- pre-Verifier trigger는 Reasoner-only 정보로 계산 가능한 여섯 종류만 사용한다.
- `reasoner_verifier_conflict`는 Verifier parsing 후 생성되는 comparison event다.
- arbitration은 parsed candidates와 post-Verifier event를 소비한다.
- `readiness.py`가 stable 10-gate evaluation을 소유하고 `gpu_readiness.json`을 생성한다.

### Epic 2

Stories 2.2와 2.5는 완료된 v2 baseline임을 명시한다. 활성 최종 계약과 migration은 Story 2.7만 소유한다. 기존 v2 prompt와 run은 변경하지 않는다.

Story 2.8은 공통 eligibility/smoke harness만 담당한다. 첫 challenger의 공식 serialization과 dependency risk는 독립 Stories 2.9~2.10으로 분리한다. lower-cost selection 이후에만 검토할 InternVL/AWQ는 Epic 4의 조건부 Stories로 둔다.

### Epic 3

Stories 3.1~3.4를 한 gate에서 연속 완료한다. Story 3.1은 pre-trigger, Story 3.2는 conditional generation과 post-parse conflict event, Story 3.3은 arbitration, Story 3.4는 audit을 소유한다. Labeled validation이 없는 production run에서는 beneficial/harmful을 추정하지 않고 단순 keep/flip/conflict/semantic 상태만 보고한다.

### Epic 4

Shadow Private는 acquisition, review, freeze, metrics로 분리한다. Tournament는 harness, diagnostic/reasoner selection, sealed/Verifier A/B, runtime gate, comparison, candidate selection으로 분리한다. Epic 4의 결과는 **selected candidate**이며 submission release는 Epic 5가 담당한다.

### Epic 5

FR21을 정식 소유하고 final compliance/reproducibility audit 후 GPU readiness 10/10을 판정한다. `GPU_SUBMISSION_READY`가 나오기 전에는 8,500-row production을 시작할 수 없다.

## 4. Detailed Change Proposals

### 4.1 Canonical SPEC — Add CAP-8

**OLD**

> CAP-1~CAP-7만 존재하며 GPU readiness는 compliance companion에만 기술됨.

**NEW**

> CAP-8 intent: The operator can prove that the selected local GPU path can safely produce a compliant full submission before production starts.
> CAP-8 success: Stable ten-gate evidence records 10/10, publishes `GPU_SUBMISSION_READY`, and explicitly notifies the operator with candidate, command and runtime projection; any failed gate suppresses readiness and production.

**Rationale:** Story 5.3의 release behavior를 first-class capability로 추적한다.

### 4.2 Epic Requirements — Add FR21

**OLD**

> Functional Requirements and coverage map end at FR20.

**NEW**

> FR21: Before 8,500-row production, the system must evaluate the ten stable GPU submission-readiness gates, publish `GPU_SUBMISSION_READY` only on 10/10, suppress production on any blocker, and explicitly notify the operator with the selected candidate, command, expected runtime and evidence artifact.

Add mappings:

- `FR21: Epic 5 - GPU submission readiness and operator notification`
- Epic 5 covered FRs: `FR19, FR20, FR21`
- Story 5.3 Requirements: `FR12, FR14, FR19, FR20, FR21, NFR2, NFR7`

### 4.3 Architecture — Correct Inference Lifecycle

**OLD**

> Reasoner → Verification Trigger? → Parse Reasoner / Verifier → Submission Writer

**NEW**

> Reasoner → Parse and semantic validation → Pre-Verifier Trigger?
> no → Reasoner-only arbitration → validated final prediction
> yes → Verifier → Parse Verifier → Post-Verifier comparison event → arbitration → validated final prediction
> unresolved → submission publication blocked

**Rationale:** Trigger fields do not exist until parsing is complete, and Reasoner–Verifier conflict cannot exist until both candidates are parsed.

### 4.4 Architecture — Split Trigger and Comparison Taxonomy

**OLD**

> Stable Verifier trigger names include `reasoner_verifier_conflict`.

**NEW**

Pre-Verifier triggers:

- `invalid_parse`
- `low_confidence`
- `unsupported_evidence`
- `protected_attribute_risk`
- `appearance_only_reasoning`
- `ambiguous_visual_grounding`

Post-Verifier comparison event:

- `reasoner_verifier_conflict`

`reasoner_verifier_conflict` must never invoke an otherwise untriggered Verifier pass.

### 4.5 Stories 2.2 and 2.5 — Mark Completed v2 Baseline

**OLD**

> Both stories appear to define the active final prompt/parser contract but omit v3 index/schema requirements.

**NEW**

Add a supersession note to the epic and dedicated story files:

> This story records the completed Reasoner v2 baseline. Its prompt/parser fields are historical A/B control behavior. Story 2.7 exclusively owns migration to and acceptance of the active Reasoner v3 contract; v2 artifacts remain immutable.

Remove FR7 active-contract ownership from these legacy story requirement lines where it creates ambiguity; retain traceability to the original baseline implementation.

### 4.6 Story 2.7 — Exclusive v3 Migration Owner

Add explicit acceptance criteria:

- active config selects v3 only through a versioned prompt/schema pair;
- `parsed_reasoner.csv`, Verifier input, arbitration and final lineage all contain `uncertainty_option_index` and `schema_version`;
- v2 and v3 artifacts cannot be mixed in one run;
- position 0/1/2 and invalid-output tests pass;
- identical Qwen snapshot/image/engine/decoding v2-v3 diagnostic A/B artifact is produced.

### 4.7 Decompose Story 2.8

**OLD**

> One story integrates eligibility, official paths, dependency isolation and up to five model families.

**NEW**

- **2.8 Build Candidate Eligibility and Adapter Smoke Harness** — common manifest schema, cutoff/license checks, offline load, official serialization evidence, real-image v3 smoke, latency/VRAM record and rejection reasons.
- **2.9 Integrate MiniCPM-V 4.5 Candidate** — official processor/chat/image path and isolated dependencies.
- **2.10 Integrate LLaVA-OneVision 7B Candidate** — official path and isolated dependencies.
- **4.8 Integrate Conditional InternVL3-14B Candidate** — lower-cost Story 4.7 evidence 뒤에 실행하는 performance-candidate path.
- **4.9 Evaluate Conditional Qwen2.5-VL-32B-AWQ Candidate** — lower-cost Story 4.7 evidence 뒤에 실행하는 isolated AWQ path; optional and non-blocking.

The corrected Qwen2.5-VL-7B control uses the existing adapter plus Stories 2.7 and 2.8 harness evidence.

### 4.8 Story 3.1 — Pre-Verifier Triggers Only

**OLD**

> Trigger list includes `reasoner_verifier_conflict`.

**NEW**

> Trigger detection consumes parsed Reasoner v3 status and may emit only the six pre-Verifier triggers. Invalid parse triggers review but never creates a fallback candidate. Conflict is not available at this stage.

### 4.9 Story 3.2 — Own Post-Verifier Conflict Event

Add acceptance criteria:

- after a valid/invalid Verifier parse, compare valid Reasoner and Verifier selected indexes;
- emit `reasoner_verifier_conflict` only when both valid candidates exist and selected indexes differ;
- preserve no-conflict, one-invalid and both-invalid states distinctly;
- never run Verifier solely to discover a conflict.

### 4.10 Story 3.4 — Complete Epic 3 Before Tournament

Move Story 3.4 immediately after Story 3.3. For labeled validation, report beneficial/harmful/no-effect flips. For unlabeled production, report only observable trigger, conflict, keep/flip, schema, unresolved and position counts.

### 4.11 Decompose Shadow Private Work

**OLD**

> Story 4.2 builds, reviews, balances, splits, seals and hashes 300~600 multimodal records.

**NEW**

- **4.1 Define Validation Dataset Schema and Subsets**
- **4.2 Acquire or Author Shadow Private Samples and Provenance**
- **4.3 Independently Review, Adjudicate and Balance Samples**
- **4.4 Freeze Selection and Sealed-Holdout Version**
- **4.5 Compute Robust Validation Metrics**

Each story emits a separately verifiable artifact consumed by the next. Freeze requires reviewed/adjudicated status, coverage gates, duplicate checks and dataset/image/split/schema hashes.

### 4.12 Decompose Tournament Work

**OLD**

> Story 4.4 owns the complete seven-stage tournament and all candidate decisions.

**NEW**

- **4.6 Implement Frozen Tournament Harness and Experiment Contract**
- **4.7 Run Diagnostic-48 and Reasoner-Only Candidate Selection**
- **4.8 Integrate Conditional InternVL3-14B Candidate**
- **4.9 Evaluate Conditional Qwen2.5-VL-32B-AWQ Candidate**
- **4.10 Run Sealed Shortlist and Verifier A/B**
- **4.11 Validate Shortlist Runtime and Memory**
- **4.12 Compare Candidate Runs Without Public-Only Optimization**
- **4.13 Select Candidate and Record Promotion Rationale**

Story 4.13 selects a candidate for final compliance/readiness; it does not authorize production. Public remains a secondary sanity signal.

### 4.13 Story 5.3 — Stable Readiness Contract

Add `gpu_readiness.json` with stable gate IDs:

1. `target_environment`
2. `model_snapshot_license`
3. `data_image_validation`
4. `prompt_schema_identity`
5. `real_image_structured_output`
6. `diagnostic_blockers`
7. `vram_runtime_projection`
8. `atomic_artifact_persistence`
9. `final_submission_validation`
10. `network_disabled_smoke`

Each result records `status`, `evidence_path`, `blocker`, candidate id and timestamp. The aggregate records command, projected runtime, notification status and `GPU_SUBMISSION_READY` only when all ten pass.

`final_submission_validation` is a fixed-fixture/dry-run of the full submission boundary before production. The real 8,500-row `submission.csv` and finalized compliance hash are required by the post-production audit, preventing a circular requirement for the final file before readiness releases production.

## 5. Corrected Dependency Plan

### Gate A — Reasoner and Verification Contract

`2.7 → 2.8 → (2.9 || 2.10) → 3.1 → 3.2 → 3.3 → 3.4`

Completion: one active v3 contract, lower-cost candidate smoke eligibility, no fixed label semantics, valid lifecycle, CPU suite and diagnostic v2/v3 A/B.

### Gate B — Independent Validation Foundation

`4.1 → 4.2 → 4.3 → 4.4 → 4.5`

Completion: reviewed 300~600 corpus, balanced positions/classes, sealed holdout and frozen metric implementation.

### Gate C — Common Candidate Foundation

`4.6 → 4.7`

The Qwen control and lower-cost candidates already cleared the common smoke harness in Gate A; this gate applies the frozen tournament contract.

### Gate D — Expanded Shortlist and Selection

`conditional 4.8/4.9 → 4.10 → 4.11 → 4.12 → 4.13`

InternVL and AWQ proceed only when lower-cost evidence justifies their cost/risk. Story 4.13 selects but does not release a production candidate.

### Gate E — Compliance and GPU Release

`5.1 → 5.2 → 5.3`

Completion: final compliance blockers zero, unresolved zero, readiness 10/10 and explicit operator notification.

### Gate F — Production and Handoff

`validated 8,500-row production → 5.4 → 5.5`

## 6. Recommended Approach

### Selected Approach

**Direct Adjustment + backlog decomposition + dependency correction + IR revalidation**

### Alternatives Rejected

- **Rollback v2 implementation:** loses the required A/B control and does not fix planning quality.
- **Proceed directly to model tournament:** confounds contract defects with model differences.
- **Reduce MVP:** unnecessary; no competition goal is infeasible.
- **Create a new Epic:** unnecessary; all work belongs to existing capability boundaries.

### Effort, Risk and Timeline

- **Effort:** Medium-High. Planning corrections are small; human-reviewed Shadow Private construction remains the largest workload.
- **Technical risk:** Medium before correction, Low-Medium after lifecycle and Story boundaries are explicit.
- **Timeline impact:** additional Story handoffs, but fewer mixed changes and failed GPU experiments.
- **MVP impact:** none.

## 7. Implementation Handoff

### Scope Classification

**Moderate** — Product Owner/Developer backlog reorganization. Fundamental PM/Architecture redesign is not required.

### Responsibilities

- **Planning/PO:** apply approved SPEC, Architecture, Epics and legacy-story supersession edits.
- **Reviewer:** rerun IR; require zero Critical, zero formal FR gaps and zero future-epic dependency.
- **Sprint Planning:** create authoritative story order/status only after IR passes.
- **Developer:** create and implement one context-filled Story at a time from the sprint plan.
- **User:** approve this proposal, candidate escalation to InternVL/AWQ, final candidate selection and GPU production release.

### Success Criteria

1. `reasoner_verifier_conflict` is post-Verifier only and cannot trigger an unconditional pass.
2. Story 2.7 is the sole active v3 migration owner; v2 remains immutable control.
3. FR21 is mapped end-to-end.
4. Epic 3 completes before Epic 4 tournament execution.
5. Model integration, Shadow Private and tournament work are implementation-sized.
6. Architecture diagram and text agree on parse → trigger → verify → compare → arbitrate.
7. IR rerun returns READY or NEEDS WORK with no blocking issue.
8. GPU production remains blocked until a real 10/10 `GPU_SUBMISSION_READY` artifact and user notification exist.

## 8. Approval and Application Log

- **User approval:** explicit `승인`, 2026-06-20
- **Scope:** Moderate
- **Applied artifacts:** Canonical SPEC, architecture diagram, architecture decision document, epic/story breakdown, Stories 2.2, 2.5, 3.1 and 3.2
- **Implementation code:** unchanged
- **Sprint status:** not created; deferred to `bmad-sprint-planning` after IR passes
- **Next handoff:** `bmad-check-implementation-readiness`
