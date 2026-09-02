# Sprint Change Proposal: Reasoner v3·Shadow Private·Model Tournament 통합 교정

**작성일:** 2026-06-20
**프로젝트:** Multimodal 236722 Multimodal AI Bias Solution
**변경 범위:** Moderate — 제품 목표와 Epic 1~5 구조는 유지하고 Epic 2 corrective tranche 및 Epic 3·4·5 backlog를 재구성한다.
**처리 모드:** Batch
**승인 상태:** 승인됨 (2026-06-20, 사용자 명시 승인)

## 1. Issue Summary

### 변경 촉발 요인

첫 Qwen2.5-VL-7B 제출은 Public 0.91을 기록했지만 다음 원인이 분리되지 않았다.

- Multimodal label은 의미 클래스가 아니라 현재 세 선택지의 0-based index인데 기존 Epic 3과 architecture는 `label 2 = uncertainty`를 전제한다.
- Reasoner v2는 prompt mapping을 수정했지만 불확실성 선택지 위치를 generated structured field로 보존하지 않는다.
- 독립적인 300~600건 Shadow Private가 없어 prompt, model, image budget과 Verifier의 Private 일반화 효과를 판정할 수 없다.
- 모델 후보 연구는 완료됐지만 candidate eligibility/adapter/tournament를 구현하는 backlog item이 없다.
- A6000에서 submission을 안전하게 생성할 수 있는 시점을 판정하고 사용자에게 알리는 acceptance criterion이 없다.

### 확인된 증거

- `docs/history/architecture.md`는 `0=first person`, `1=second person`, `2=uncertain`을 고정하고 failure를 arbitration label 2로 전환하도록 규정한다.
- `docs/history/epics.md` FR11과 Story 3.3은 근거 부족 시 label 2를 선택한다.
- `_bmad-output/specs/spec-reasoner-v3-contract/`는 `uncertainty_option_index` 생성, semantic invariant와 unresolved fail-closed를 요구한다.
- `_bmad-output/specs/spec-shadow-private-validation/`는 300~600건, sealed holdout 30% 이상·최소 120건, provenance와 subset/position gate를 요구한다.
- `docs/history/research/technical-multimodal-236722-vlm-model-tournament-research-2026-06-20.md`는 staged tournament와 GPU readiness 10개 gate를 확정했다.
- 기존 `docs/history/sprint-change-proposal-2026-06-19.md`는 label 의미 교정은 다루지만 위 세 신규 실행 단위와 GPU operator gate를 Story로 만들지 않았다.

### 문제 유형

- 원래 요구사항의 의미 오해
- 구현 중 발견된 semantic contract 결함
- Private 일반화를 판단하기 위한 검증 요구사항 구체화
- 모델 선정 및 운영 준비를 실행 가능한 backlog로 전환해야 하는 신규 계획 요구

## 2. Change Navigation Checklist

### 2.1 Trigger and Context

- [x] 1.1 촉발 범위: Epic 2 Reasoner v2 조사, 첫 0.91 제출, Epic 3 고정 label 전제.
- [x] 1.2 핵심 문제: 모델 성능·prompt contract·Verifier 효과를 분리할 generated semantics와 independent holdout이 없음.
- [x] 1.3 증거: source/config, 기존 proposal, Reasoner v3/Shadow Private SPEC, model tournament research.

### 2.2 Epic Impact

- [x] 2.1 Epic 2는 유지하되 Story 2.7 Reasoner v3와 Story 2.8 candidate adapter eligibility를 corrective tranche로 추가한다.
- [x] 2.2 Epic 3 목적은 유지하고 Story 3.1~3.4를 option-index semantics로 정정한다.
- [x] 2.3 Epic 4는 schema만 정의하는 수준에서 실제 corpus build/freeze와 staged tournament까지 확장한다.
- [x] 2.4 Epic 5는 GPU readiness/notification story를 추가하고 최종 candidate 이후 handoff를 완료한다.
- [x] 2.5 새 Epic은 필요 없다. 기존 capability 범위 안의 direct adjustment다.
- [x] 2.6 실행 순서는 Epic 번호 순차가 아니라 Gate A~E의 dependency 순으로 재배치한다.

### 2.3 Artifact Impact

- [x] 3.1 PRD-equivalent canonical SPEC의 CAP-1~CAP-7과 MVP는 유지한다. Strategy/Validation companion과 model assumption을 정정한다.
- [!] 3.2 Architecture의 label definitions, fallback, schemas, validation tiers, tournament와 operations gate를 수정해야 한다.
- [N/A] 3.3 UI/UX는 없는 offline CLI이므로 영향이 없다.
- [!] 3.4 Epics/Stories, prompt/schema/parser/verifier/arbitration/submission, validation/tournament/compliance와 tests가 영향받는다.
- [!] 3.5 sprint-status가 아직 없으므로 승인 후 Sprint Planning에서 새로 생성해야 한다.

### 2.4 Path Forward

- [x] 4.1 Direct Adjustment: **Viable**, effort Medium-High, risk Medium.
- [x] 4.2 Rollback: **Not viable**. Reasoner v2와 기존 artifact는 A/B baseline으로 보존한다.
- [x] 4.3 MVP Review: **Not required**. 경쟁 목표와 CAP-1~CAP-7은 그대로 달성 가능하다.
- [x] 4.4 선택: Direct Adjustment + backlog resequencing + readiness revalidation.

### 2.5 Proposal and Handoff

- [x] 5.1 issue summary와 evidence 작성.
- [x] 5.2 Epic/Story/Architecture/SPEC 영향 정의.
- [x] 5.3 권장 경로와 대안 trade-off 정의.
- [x] 5.4 MVP 영향 없음과 Gate A~E action plan 정의.
- [x] 5.5 PO/Developer/Reviewer/User handoff 정의.
- [x] 6.1 적용 가능한 checklist 검토 완료.
- [x] 6.2 proposal consistency 검토 완료.
- [!] 6.3 사용자 명시적 승인 필요.
- [N/A] 6.4 기존 sprint-status 없음. 승인 후 `bmad-sprint-planning`으로 생성.
- [!] 6.5 승인 후 backlog 반영 및 readiness 재검사 필요.

## 3. Impact Analysis

### PRD-equivalent SPEC

핵심 capability와 평가 scope는 바뀌지 않는다. 다음 companion/assumption을 구체화한다.

- generated output은 `label`과 `uncertainty_option_index`를 독립적으로 생성한다.
- 유효한 generated candidate가 없으면 `unresolved`이며 submission을 차단한다.
- primary model assumption을 9B 단일 후보에서 staged shortlist/tournament로 변경한다.
- local validation은 실제 300~600건 selection/sealed suite와 별도 diagnostic-48을 사용한다.

### Architecture

다음 항목은 직접 충돌하므로 수정이 필수다.

- `Required label names`의 고정 person/uncertainty 의미
- recoverable failure를 label 2로 변환하는 error handling
- Reasoner/Verifier schema에 `uncertainty_option_index`, `schema_version` 부재
- validation tier/freeze와 candidate tournament stage 부재
- GPU readiness와 operator notification gate 부재

Architecture는 modular monolith CLI, typed boundaries, immutable artifacts와 local inference를 그대로 유지한다.

### Epic 2

- Story 2.7을 추가해 Reasoner v3 contract를 prompt/schema/parser/artifact/submission 경계에 구현한다.
- Story 2.8을 추가해 tournament candidate eligibility manifest와 model-specific adapter/config를 구현한다.
- 기존 v1/v2 prompts와 legacy run은 불변 baseline으로 보존하고 schema version이 다른 run은 직접 혼합하지 않는다.

### Epic 3

- Story 3.1 trigger는 숫자 label이 아니라 generated uncertainty index와 semantic consistency를 사용한다.
- Story 3.2 Verifier는 자신의 `uncertainty_option_index`를 생성하고 같은 invariant를 통과한다.
- Story 3.3 arbitration은 Reasoner/Verifier generated candidate만 keep/flip하고 label을 발명하지 않는다.
- Story 3.4는 position별 trigger/flip, beneficial/harmful flip과 unresolved를 감사한다.

### Epic 4

기존 네 Story를 여섯 Story로 확장한다.

1. 4.1 validation schema/provenance/subset 계약
2. 4.2 Shadow Private 300~600건 구축·이중 검수·freeze
3. 4.3 robust metrics와 position/semantic/verifier metrics
4. 4.4 staged model tournament 실행
5. 4.5 candidate run comparison
6. 4.6 promotion rationale와 sealed holdout regression gate

### Epic 5

기존 네 Story를 다섯 Story로 확장한다.

1. 5.1 compliance manifest
2. 5.2 offline reproducibility audit
3. 5.3 GPU submission readiness 판정과 사용자 알림
4. 5.4 second-round checklist
5. 5.5 final handoff summary

## 4. Detailed Change Proposals

### 4.1 Requirements Inventory — FR7

**OLD**

> The Reasoner output must include a parseable final label candidate `0`, `1`, or `2`, concise evidence, evidence type, uncertainty signal, and protected-attribute risk signal.

**NEW**

> The Reasoner output must generate a final answer-choice index and the uncertainty answer's current index as separate fields, with evidence, evidence type, uncertainty signal, protected-attribute risk and schema version. `uncertainty_signal` must equal whether the selected label matches the generated uncertainty option index.

### 4.2 Requirements Inventory — FR11

**OLD**

> ... selecting `2` when objective support is insufficient.

**NEW**

> Arbitration may retain or select only a valid label generated by the Reasoner or Verifier. Insufficient evidence uses the uncertainty-choice index generated by a valid model output. If neither stage provides a valid candidate, the sample is unresolved and submission is blocked.

### 4.3 Architecture — Label and Failure Semantics

**OLD**

> `0`: first person; `1`: second person; `2`: uncertain. Recoverable failures are converted to label `2` through arbitration.

**NEW**

> `0`, `1`, `2` are answer-choice indexes only. Any index may represent a person or uncertainty. Each generated candidate carries `uncertainty_option_index`; failures never create a label. No surviving generated candidate means `unresolved` and fail-closed submission.

### 4.4 New Story 2.7 — Implement Reasoner v3 Option-Index Contract

**Requirements:** FR5, FR7, FR8, FR12, FR14

As a competition developer, I want Reasoner outputs to identify the selected answer and uncertainty answer positions independently, so that every choice order is interpreted correctly and downstream stages never infer semantics from a number.

**Acceptance Criteria:**

- `configs/prompts/reasoner_v3.yaml` requires strict `FINAL_ANSWER_JSON` with integer `uncertainty_option_index` 0..2.
- parser enforces `uncertainty_signal == (label == str(uncertainty_option_index))` and evidence-type consistency.
- `parsed_reasoner.csv` records `schema_version=reasoner_output_v3` and uncertainty index.
- raw prompt, prompt hash, image hash, raw output and parse error remain auditable.
- invalid rows are not repaired with regex, fixed position, unknown phrase mapping or fallback label.
- Reasoner v2 remains unchanged for isolated A/B.
- uncertainty index 0/1/2 parameterized tests and v2/v3 diagnostic A/B contract are defined.

### 4.5 New Story 2.8 — Integrate Eligible Tournament Model Adapters

**Requirements:** FR6, FR14, FR18, FR19

As a competition developer, I want each tournament model integrated through its official local multimodal path, so that model comparisons are eligible, auditable and not confounded by incorrect serialization.

**Acceptance Criteria:**

- candidate manifest records official repo, exact commit, cutoff evidence, license, snapshot/custom-code hashes and remote API usage `none`.
- Qwen2.5-VL-7B is the corrected control; MiniCPM-V-4.5 and LLaVA-OneVision-7B are first challengers; InternVL3-14B is a performance candidate; Qwen2.5-VL-32B-AWQ is conditional.
- each adapter preserves the official processor/chat template, original local image bytes/path and preprocessing metadata.
- model-specific dependencies are isolated; AWQ does not mutate the baseline environment.
- real-image structured-output smoke records load status, prompt rendering evidence, latency and peak VRAM.
- candidate failing eligibility, offline load or A6000 smoke cannot enter diagnostic-48.

### 4.6 Story 3.1~3.4 — Verification Semantics

**OLD**

> Numeric label 2 represents uncertainty; numeric 0/1 represent person choices; invalid or unsupported output may be routed to label 2.

**NEW**

- trigger consistency uses selected label, generated uncertainty index, uncertainty signal and evidence type.
- Verifier independently generates the same v3 semantic fields.
- arbitration only keeps/flips between valid generated candidates.
- both candidates invalid means `unresolved`; final prediction/submission publication fails.
- audit reports position 0/1/2 trigger/keep/flip, beneficial/harmful flip, semantic failures and unresolved.

### 4.7 Story 4.1 — Define Validation Contract

기존 schema에 `uncertainty_option_index`, `expected_is_uncertainty`, provenance/license, author/reviewer, review status, split과 image hash를 추가한다. 필수 subset 여덟 개와 uncertainty position 0/1/2 coverage를 검사한다.

### 4.8 New Story 4.2 — Build, Review and Freeze Shadow Private

**Requirements:** FR16, FR17, FR18

As a competition developer, I want an independently sourced and sealed 300~600 sample validation suite, so that candidate selection approximates Private/Hidden generalization without test-derived leakage.

**Acceptance Criteria:**

- 총 300~600건이며 evaluation/test-derived sample은 0건이다.
- 각 필수 subset은 최소 30건, uncertainty position 0/1/2는 각각 전체의 30% 이상이다.
- ambiguous와 resolvable은 각각 최소 120건이다.
- synthetic/generated label은 독립 사람 검수 전 승인되지 않는다.
- sealed holdout은 전체의 30% 이상이고 최소 120건이다.
- dataset/image/split/schema SHA-256 manifest를 tournament 전에 freeze한다.
- sealed sample-level detail은 shortlist 전 prompt/model 조정자에게 공개하지 않는다.
- 별도 diagnostic-48은 promotion 점수에 포함하지 않는다.

### 4.9 Story 4.3 — Robust Metrics

기존 metrics에 uncertainty-position accuracy, semantic consistency, unresolved, beneficial/harmful/no-effect flips, peak VRAM과 projected 8,500-row full-path runtime을 추가한다. dataset/hash가 다른 run은 동일 ranking에 직접 비교하지 않는다.

### 4.10 New Story 4.4 — Execute Staged Model Tournament

**Requirements:** FR6, FR16, FR18

As a competition developer, I want candidates evaluated through fixed promotion gates, so that model selection isolates quality, runtime and integration risk.

**Acceptance Criteria:**

- funnel 순서는 eligibility → real-image smoke → diagnostic-48 → Reasoner-only selection → sealed shortlist → Verifier A/B → runtime/compliance다.
- Qwen v2/v3는 동일 snapshot/image/engine/decoding으로 먼저 비교한다.
- prompt, model, image budget, engine과 Verifier를 한 A/B에서 동시에 변경하지 않는다.
- reasoner-only, same-model verifier, stronger-verifier는 별도 candidate run이다.
- Public score는 local gate 통과 상위 2~3개의 secondary sanity signal로만 기록한다.
- 모든 promotion/rejection은 immutable comparison artifact를 가진다.

### 4.11 Story 4.5/4.6 — Comparison and Promotion

기존 Story 4.3/4.4를 4.5/4.6으로 이동한다. sealed aggregate, worst-subset regression, position collapse, unresolved, harmful flips, runtime, compliance를 blocking gate로 추가한다.

### 4.12 New Story 5.3 — Validate GPU Submission Readiness and Notify Operator

**Requirements:** FR12, FR14, FR19, FR20, NFR2, NFR7

As a competition operator, I want an explicit GPU readiness verdict and notification before full inference, so that an 8,500-row run starts only when it can produce a valid submission on the target path.

**Acceptance Criteria:**

- target GPU/environment, exact snapshot/license, data/images, prompt/schema hashes, real-image output, diagnostic failures, peak VRAM/runtime projection, persistent atomic artifacts, submission validation and network-disabled smoke를 검사한다.
- 열 개 gate가 모두 통과한 경우에만 `GPU_SUBMISSION_READY` artifact/status를 기록한다.
- 8,500건 production을 시작하기 전에 사용자에게 준비 완료와 candidate/run command를 명시적으로 알린다.
- 하나라도 실패하면 준비 완료를 알리지 않고 blocking reason을 기록한다.
- 내부 목표는 startup부터 submission publication까지 63분 이하이며 공식 70분 기준 초과 위험을 별도 표시한다.

## 5. Integrated Sprint Plan

### Gate A — Reasoner v3 Contract Repair

1. Story 2.7 Reasoner v3
2. Story 3.1 trigger semantic correction
3. Story 3.2 Verifier v3-compatible output
4. Story 3.3 fail-closed arbitration/submission

완료 조건: position 0/1/2 tests, fixed-label 의미 제거, valid generated lineage, CPU suite 통과.

### Gate B — Independent Validation Foundation

5. Story 4.1 validation contract
6. Story 4.2 Shadow Private build/review/freeze
7. Story 4.3 robust metrics

완료 조건: 300~600건 frozen suite, sealed holdout, provenance/blocking checks와 deterministic metric report.

### Gate C — Candidate Integration and Tournament

8. Story 2.8 model adapters/eligibility
9. Story 4.4 staged tournament
10. Story 3.4 verification audit
11. Story 4.5 comparison
12. Story 4.6 promotion

완료 조건: corrected Qwen control과 challengers가 동일 frozen contract에서 평가되고 shortlist rationale가 남음.

### Gate D — Compliance and GPU Readiness

13. Story 5.1 compliance manifest
14. Story 5.2 offline audit
15. Story 5.3 GPU readiness/notification

완료 조건: readiness 10/10, unresolved 0, full-path runtime/VRAM/compliance 통과 후 사용자 알림.

### Gate E — Production and Handoff

16. 8,500건 production inference와 validated submission
17. Story 5.4 second-round checklist
18. Story 5.5 final handoff

## 6. Recommended Approach

### 선택안

**Direct Adjustment + backlog resequencing + readiness revalidation**

새 Epic이나 PRD 재작성은 필요하지 않다. 핵심 architecture는 유지하면서 누락된 executable Story를 추가하고 고정 label 전제를 제거한다.

### 대안 평가

- **기존 Epic 3부터 계속 구현:** 빠르지만 잘못된 label 의미와 validation 부재를 고착하므로 거부.
- **모델부터 교체:** 0.91 원인을 분리하지 못하고 prompt/image/engine confounder를 키우므로 거부.
- **Reasoner v2만 즉시 8,500건 제출:** Public sanity 제출로는 가능하지만 Private selection 근거가 아니며 통합 구현을 대신하지 못한다.
- **새 Epic 생성:** capability가 기존 Epic 2·4·5에 속하므로 불필요.

### Effort, Risk and Timeline

- **Effort:** Medium-High. application code보다 Shadow Private corpus 제작·검수가 가장 큰 작업이다.
- **Technical Risk:** Medium. schema와 legacy artifact compatibility, model-specific preprocessing, AWQ environment가 주요 위험이다.
- **Schedule Impact:** corrective tranche와 validation foundation이 선행되어 Epic 3 완료가 늦어지지만 잘못된 full GPU run과 Public overfit 비용을 줄인다.
- **MVP Impact:** 없음. 원래 CAP-1~CAP-7 달성 가능성이 오히려 높아진다.

## 7. Implementation Handoff

### Scope Classification

**Moderate:** Product Owner/Developer 수준 backlog 재구성과 Story 단위 구현이 필요하다. PM/Architecture 전면 재설계는 필요하지 않다.

### Responsibilities

- **PO/Planning:** canonical SPEC companion, architecture, epics, story acceptance criteria와 dependency order 반영.
- **Developer:** Gate A부터 schema → prompts/parsers → verifier/arbitration → validation → adapters/tournament → compliance/readiness 순으로 구현.
- **Reviewer:** label-position independence, no invented label, leakage/provenance, official serialization, sealed holdout와 runtime gate를 적대적으로 검토.
- **User:** Shadow Private source 정책, shortlist promotion과 GPU production 시작을 승인.

### Success Criteria

1. 코드·prompt·docs에서 숫자 label의 고정 의미가 제거된다.
2. Reasoner와 Verifier가 모든 sample에서 uncertainty index를 생성·감사한다.
3. invalid generated candidates가 label로 보정되지 않으며 unresolved는 submission을 차단한다.
4. 300~600건 Shadow Private가 검수·동결되고 sealed policy를 지킨다.
5. model tournament가 corrected control과 challengers를 동일 조건에서 비교한다.
6. Verifier는 beneficial/harmful flip과 runtime gate를 통과할 때만 채택된다.
7. GPU readiness 10/10 후 사용자에게 알리고 나서만 full production을 실행한다.
8. final run은 compliance와 offline reproducibility audit를 통과한다.

## 8. Approval Decision

승인되면 다음을 수행한다.

1. 이 제안서를 `approved`로 확정한다.
2. canonical SPEC companion, architecture와 epics를 변경안대로 수정한다.
3. 기존 Story 3.1~3.3 파일을 option-index semantics로 정정한다.
4. 새 Story는 backlog에 반영하고 `bmad-create-story`로 구현 직전 상세 파일을 생성한다.
5. `bmad-check-implementation-readiness`를 다시 실행한다.
6. `bmad-sprint-planning`으로 Epic 2 corrective tranche와 Epic 3·4·5 통합 sprint-status를 생성한다.

사용자 승인에 따라 planning source를 수정한다. implementation code는 Story 실행 전까지 변경하지 않는다.

## 9. Approved Change Execution Log

**승인:** 2026-06-20 사용자 명시 승인
**적용 범위:** Moderate / planning and backlog correction
**수정된 artifact:** canonical SPEC companions, `architecture.md`, `epics.md`, Story 3.1, Story 3.2, Story 3.3
**코드 변경:** 없음
**sprint-status:** 기존 파일이 없어 이번 단계에서는 N/A; Sprint Planning에서 신규 생성
**다음 라우팅:** `bmad-check-implementation-readiness` → `bmad-sprint-planning` → Gate A Story 구현
