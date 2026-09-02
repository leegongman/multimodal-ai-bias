# Sprint Change Proposal: 선택지 인덱스 의미 정정 및 Epic 3·4·5 통합 스프린트

**작성일:** 2026-06-19
**프로젝트:** Multimodal 236722 Multimodal AI Bias Solution
**변경 범위:** Moderate — 기존 Epic 구조는 유지하되 완료/검토 중 Story 3.1~3.3을 재개하고 Epic 3·4·5 백로그 순서를 재구성한다.
**처리 모드:** Batch
**승인 상태:** 승인 대기

## 1. Issue Summary

### 변경 촉발 요인

Epic 2의 `reasoner_v2` 조사에서 Multimodal label `0/1/2`는 의미 클래스가 아니라 현재 답안 배열의 0-based 선택지 인덱스임이 확인됐다. 불확실성 선택지는 샘플마다 index `0`, `1`, `2` 중 어느 위치에도 올 수 있다.

Epic 2의 기본 Reasoner 프롬프트는 이 매핑을 수정했지만 Epic 3 구현과 계획 문서는 여전히 다음 전제를 사용한다.

- `label 2 = 불확실성`
- `label 0/1 = 사람 선택지`
- 유효한 Reasoner/Verifier 출력이 없으면 arbitration이 `2`를 생성한다.

이 전제는 선택지 순서가 바뀐 샘플에서 잘못된 trigger, Verifier parse 거부, 잘못된 arbitration label, 규칙 기반 fallback을 발생시킨다.

### 확인된 증거

- `configs/prompts/verifier_v1.yaml`: 객관적 근거가 부족하면 label 2를 선택하도록 지시한다.
- `src/multimodal_bias/parsing.py`: Verifier의 `label == "2"`만 `insufficient_evidence`와 결합할 수 있다.
- `src/multimodal_bias/verifier.py`: `PERSON_LABELS={"0","1"}`이며 label 2를 uncertainty로 판정한다.
- `src/multimodal_bias/arbitration.py`: 양 단계가 실패하거나 근거가 부족하면 label 2를 생성한다.
- `docs/history/architecture.md`, `docs/history/epics.md`, Story 3.1~3.3에도 같은 의미 전제가 남아 있다.
- 현재 회귀 기준은 CPU-safe test `370 passed`다. 기존 테스트 통과는 잘못된 고정 매핑을 계약으로 테스트하고 있기 때문에 의미 정확성을 증명하지 않는다.

### 핵심 설계 원칙

1. label은 항상 답안 배열의 인덱스일 뿐이며 고정 의미를 갖지 않는다.
2. 생성된 출력이 선택한 답을 불확실성으로 판단했다면 그 출력의 label이 해당 단계의 `uncertainty_option_index`다.
3. `uncertainty_option_index`는 생성 결과와 함께 감사 가능하게 보존하되, unknown 문구 regex나 test-derived 규칙으로 label을 만들지 않는다.
4. Reasoner와 Verifier 모두 유효한 label 후보를 생성하지 못한 경우 arbitration은 임의 label을 만들지 않고 `unresolved`로 실패시켜 submission 생성을 차단한다.

## 2. Change Navigation Checklist

### 2.1 Trigger and Context

- [x] 1.1 촉발 Story: Epic 2 Reasoner 선택지 매핑 수정과 후속 조사에서 Epic 3 잔존 결함 발견.
- [x] 1.2 문제 유형: 원래 요구사항의 의미 오해와 이미 구현된 고정 label 전제.
- [x] 1.3 증거: 프롬프트, parser, verifier, arbitration, 문서 및 테스트에서 고정 `2` 전제 확인.

### 2.2 Epic Impact

- [x] 2.1 Epic 3은 목적 자체는 유효하지만 Story 3.1~3.3의 acceptance criteria와 구현을 정정해야 한다.
- [x] 2.2 새 Epic은 필요하지 않다. 기존 Epic 3 범위 내 직접 조정으로 해결한다.
- [x] 2.3 Epic 4는 새 의미 계약을 검증하는 독립 validation과 metrics를 먼저 제공해야 한다.
- [x] 2.4 Epic 5는 폐기되지 않지만 최종 manifest/handoff는 승격된 candidate run 이후에만 확정할 수 있다.
- [x] 2.5 실행 순서를 일부 교차한다: 의미 계약 정정 → Epic 4.1/4.2 기반 → Epic 3 완료 → Epic 4.3/4.4 → Epic 5.

### 2.3 Artifact Impact

- [x] 3.1 PRD-equivalent SPEC의 핵심 목표는 유지된다. runtime logging의 `uncertainty option index` 계약을 구현 수준에서 명확히 한다.
- [!] 3.2 Architecture의 고정 label 정의, arbitration fallback, typed contracts를 수정해야 한다.
- [N/A] 3.3 UI/UX는 없는 CLI 프로젝트이므로 영향 없음.
- [!] 3.4 Epic/Story, prompt, parser, schemas, verifier, arbitration, submission guard, dummy adapter 및 관련 테스트 수정 필요.

### 2.4 Path Forward

- [x] 4.1 Direct Adjustment: **Viable**, effort Medium, risk Medium.
- [x] 4.2 Rollback: **Not viable**. Epic 2 `reasoner_v2`는 올바른 방향이며 되돌릴 이유가 없다.
- [x] 4.3 MVP Review: **Not required**. CAP-1~CAP-7과 평가 목표는 유지된다.
- [x] 4.4 선택: Direct Adjustment + backlog resequencing.

## 3. Impact Analysis

### Epic 3

- Story 3.1을 `done`에서 재개해 trigger 의미를 label 값이 아닌 선택지 의미 신호로 변경한다.
- Story 3.2를 `review`에서 재개해 `verifier_v2`와 Verifier output/parser 계약을 수정한다.
- Story 3.3을 `review`에서 재개해 고정 label fallback을 제거하고 unresolved fail-closed 경계를 도입한다.
- Story 3.4 audit에 uncertainty option 위치별 trigger/flip/accuracy 및 unresolved count를 추가한다.

### Epic 4

- Story 4.1 validation schema에 `uncertainty_option_index`를 필수로 추가하고 index 0/1/2가 균형 있게 포함되도록 한다.
- Story 4.2 metrics에 uncertainty-position별 성능, invalid semantic combination, unresolved rate를 추가한다.
- Story 4.3/4.4에서 Epic 3 활성화 전후의 개선과 harmful flip을 비교하고 승격 gate로 사용한다.

### Epic 5

- Story 5.1 manifest에 Reasoner/Verifier prompt version과 option-index contract version을 기록한다.
- Story 5.2 offline audit에서 prompt/schema/artifact 호환성과 unresolved=0을 검사한다.
- Story 5.3/5.4 구현은 진행할 수 있으나 최종 산출물의 run id, model revision, metrics, submission path는 최종 candidate 승격 후 채운다.

### 기술 영향

영향 파일은 최소 다음 범주다.

- 계약: `schemas.py`, `parsed_reasoner.csv`, `verification.jsonl`
- 프롬프트: 새 `verifier_v2.yaml`; 기존 `verifier_v1.yaml`은 재현용 보존
- 판정: `parsing.py`, `verifier.py`, `arbitration.py`
- 실행 경계: `submission.py`, `cli.py`, `models/dummy.py`
- 검증: prompting/parsing/verifier/arbitration/submission/CLI tests
- 계획: SPEC companion, architecture, epics, Story 3.1~3.3

## 4. Detailed Change Proposals

### 4.1 Requirements Inventory — FR11

**OLD**

> The system must arbitrate final labels ... and selecting `2` when objective support is insufficient.

**NEW**

> The system must arbitrate final labels from generated Reasoner and Verifier candidates. Labels remain zero-based answer-choice indexes. When evidence is insufficient, it may select only the uncertainty-choice index produced by a valid model output. If neither stage provides a valid generated candidate, arbitration marks the sample unresolved and blocks submission instead of inventing a label.

**근거:** label 2에 의미를 부여하지 않고 평가 규정의 LLM-generated final decision을 보존한다.

### 4.2 Architecture — Label and Error Handling

**OLD**

> `0`: first person, `1`: second person, `2`: uncertain / not objectively answerable
> Recoverable per-sample failures ... converted to label `2` only through arbitration.

**NEW**

> `0`, `1`, `2` are only zero-based answer-choice indexes. No index has an inherent person or uncertainty meaning.
> A valid generated output carries semantic uncertainty information. When it selects the uncertainty answer, its selected label is recorded as that stage's `uncertainty_option_index`. If no valid generated candidate survives, the sample is unresolved; submission generation fails closed.

**근거:** 고정 클래스 의미와 규칙 기반 fallback을 제거한다.

### 4.3 Story 3.1 — Trigger Detection

**OLD**

> person labels are `0/1`; an internally consistent label `2` uncertainty row does not trigger; label `2` with decisive evidence is inconsistent.

**NEW**

> Trigger consistency is evaluated from `uncertainty_signal`, `evidence_type`, selected label, and derived `uncertainty_option_index`, never from the numeric label alone. Any label `0/1/2` may be an uncertainty or person choice. `uncertainty_signal=true` requires `evidence_type=insufficient_evidence` and records `uncertainty_option_index=parsed_label`; decisive evidence requires `uncertainty_signal=false`.

추가 acceptance criteria:

- uncertainty 선택지가 0/1/2인 세 경우 모두 동일한 trigger 결과를 낸다.
- `PERSON_LABELS={"0","1"}` 또는 `parsed_label == "2"` 방식의 의미 판정이 없어야 한다.
- invalid parse는 trigger만 만들며 fallback label을 만들지 않는다.

### 4.4 Story 3.2 — Verifier Prompt and Parsing

**OLD**

> Choose label 2 when objective support is insufficient.
> `label == 2` requires insufficient evidence; labels 0/1 require objective support.

**NEW**

> Each label is only the number printed beside an answer choice. Independently identify the appropriate answer. If evidence is insufficient, select the answer choice expressing uncertainty wherever it appears and output that choice's index. No numeric label has inherent meaning.

Verifier output semantics:

- 모든 label `0/1/2`는 decisive 또는 uncertainty answer가 될 수 있다.
- `evidence_type=insufficient_evidence`와 `objective_support=false`이면 선택된 label을 Verifier의 `uncertainty_option_index`로 기록한다.
- decisive evidence와 `objective_support=true`이면 uncertainty index는 null이다.
- 기존 `verifier_v1.yaml`은 A/B 및 재현용으로 보존하고 새 `verifier_v2.yaml`을 기본값으로 사용한다.

### 4.5 Story 3.3 — Arbitration

**OLD**

> both outputs lack support → label 2
> invalid Reasoner + unusable Verifier → label 2

**NEW**

- Verifier가 구체적 결함과 더 강한 근거를 제시하면 Verifier가 생성한 label을 사용한다.
- 근거 부족을 판단한 유효 Verifier 출력이 있으면 Verifier가 생성한 uncertainty 선택지 index를 사용한다.
- Verifier가 실패해도 Reasoner의 유효한 generated candidate가 있으면 해당 candidate를 유지하고 실패를 기록한다.
- 두 단계 모두 유효한 generated candidate가 없으면 `unresolved`로 표시하고 `final_predictions.csv`/`submission.csv` 생성을 차단한다.
- arbitration은 label 숫자의 의미를 해석하거나 새 label을 발명하지 않는다.

### 4.6 Story 3.4 — Audit

기존 trigger/flip 통계에 다음을 추가한다.

- Reasoner/Verifier uncertainty option index 분포
- uncertainty index 0/1/2별 trigger, flip, keep, unresolved 수
- semantic inconsistency 수
- Verifier harmful flip과 beneficial flip
- unresolved sample 수와 submission-blocking 상태

### 4.7 Epic 4 Validation

Story 4.1 schema 변경:

- `expected_label`
- `uncertainty_option_index`
- `expected_is_uncertainty`
- 하나 이상의 subset label과 provenance

검증셋 gate:

- uncertainty option index 0/1/2를 모두 포함한다.
- test/evaluation 문구, 선택지 패턴, 이미지 또는 추론 정답에서 파생하지 않는다.
- 최소 A/B 세트는 기존 조사 기준인 `ambiguous 24 / disambiguated_text 12 / visual_grounded 12`와 uncertainty 위치 균형을 유지한다.

Story 4.2 추가 metrics:

- uncertainty-position accuracy (index 0/1/2)
- semantic consistency failure rate
- unresolved rate
- Reasoner-only 대비 conditional-verifier delta
- subset별 beneficial/harmful flip

### 4.8 Epic 5 Reproducibility

manifest/audit에 다음을 추가한다.

- Reasoner prompt version과 hash
- Verifier prompt version과 hash
- parsed/verification artifact schema version
- uncertainty option index semantics version
- unresolved count가 0인지 여부
- 최종 submission의 arbitration 사용 여부

## 5. Integrated Sprint Plan for Epics 3·4·5

### Gate A — Semantic Contract Repair

1. Story 3.1 재개: schema/trigger 의미 정정
2. Story 3.2 재개: `verifier_v2`, parser, verification artifact 정정
3. Story 3.3 재개: arbitration fail-closed 및 submission guard 정정

완료 조건: uncertainty index 0/1/2 parameterized tests 통과, 고정 label 의미 판정 제거, 전체 CPU suite 통과.

### Gate B — Independent Validation Foundation

4. Story 4.1: validation schema/subsets/provenance
5. Story 4.2: robust metrics와 position별 평가

완료 조건: test-derived 데이터 없이 고정된 Shadow Private 세트로 Reasoner-only와 verifier-enabled를 비교할 수 있음.

### Gate C — Verification Audit and Promotion

6. Story 3.4: verification audit 완성
7. Story 4.3: candidate run comparison
8. Story 4.4: promotion rationale와 regression gate

완료 조건: verifier가 local balanced accuracy와 worst-subset을 개선하고 harmful flip/unresolved/runtime gate를 통과할 때만 활성화.

### Gate D — Compliance and Handoff

9. Story 5.1: compliance manifest
10. Story 5.2: offline reproducibility audit
11. Story 5.3: second-round checklist
12. Story 5.4: final handoff generator

완료 조건: generator와 검사기는 구현·테스트되고, 최종 candidate-dependent 필드는 승격 run 이후 완성된다.

## 6. Effort, Risk, and Timeline Impact

- **구현 노력:** Medium. 핵심 의미 수정은 제한적이지만 artifact schema와 테스트가 여러 경계를 통과한다.
- **기술 위험:** Medium. 기존 370 tests 중 고정 label 전제를 가진 fixture를 의미 기반 fixture로 교체해야 한다.
- **일정 영향:** Epic 3 활성화 전에 corrective tranche가 추가된다. Epic 4.1/4.2를 앞당기므로 전체 Epic 수는 늘지 않지만 실행 순서는 교차된다.
- **가장 큰 위험:** 기존 `parsed_reasoner.csv`와 `verification.jsonl`의 schema 호환성. 기존 run은 schema version을 판별해 명시적으로 거부하거나 migration-free legacy read 정책을 문서화해야 한다.
- **완화책:** v1 prompts와 과거 run은 불변 보존, v2/default artifacts는 schema version 부여, atomic publication과 fail-closed submission 유지.

## 7. Implementation Handoff

### 분류

**Moderate:** Product Owner/Developer 수준의 backlog 재구성과 Developer 구현이 필요하다. PRD 목표나 전체 architecture의 재설계는 필요하지 않다.

### 담당

- **PO/Planning:** Epic/Story acceptance criteria와 상태 수정, 통합 sprint-status 생성.
- **Developer:** schema → prompt/parser → trigger/verifier → arbitration/submission → audit/validation → compliance 순으로 구현.
- **Reviewer:** 선택지 위치 0/1/2 독립성, 규칙 기반 fallback 부재, artifact 호환성, test-derived 규칙 부재를 적대적으로 검토.
- **사용자:** 독립 validation 데이터의 출처 승인과 최종 candidate promotion 승인.

### 구현 성공 기준

1. label `0/1/2` 어디에도 고정 의미를 부여하지 않는다.
2. uncertainty 선택지 위치 0/1/2에서 Reasoner, Verifier, trigger, arbitration이 동일한 의미로 동작한다.
3. 유효한 generated candidate가 없으면 submission이 생성되지 않는다.
4. 모든 trigger/flip/failure가 raw text와 option-index lineage를 보존한다.
5. 기존 Reasoner-only v2 경로와 370-test baseline에 회귀가 없고 새 semantic tests가 추가된다.
6. verifier-enabled candidate는 독립 local validation gate를 통과하기 전 Public 제출 후보로 승격되지 않는다.
7. 최종 run은 compliance와 offline reproducibility audit를 통과한다.

## 8. Approval Decision

승인 시 다음 작업을 수행한다.

1. 이 제안서를 `approved`로 확정한다.
2. `docs/history/architecture.md`, `docs/history/epics.md`, Story 3.1~3.3을 제안 내용대로 수정한다.
3. Epic 3·4·5 통합 sprint-status/backlog를 생성한다.
4. 구현은 Gate A부터 Story 단위로 진행한다.

승인 전에는 계획 문서와 구현 코드를 변경하지 않는다.
