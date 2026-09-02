# Sprint Change Proposal — Story 4.3 사람 검수 제외

작성일: 2026-06-21  
검토 방식: Batch  
상태: 승인 및 반영 완료

사용자 승인: 2026-06-21 (`yes`)

## 1. Issue Summary

Story 4.3의 구현은 완료됐지만, 평가셋 승격에는 AI 작성 파이프라인과 분리된 사람이 600건을 검수하고 불일치를 재심해야 한다. 30건 pilot을 시작하는 과정에서 사용자는 이 수동 검수의 현재 가치가 투입 비용보다 낮다고 판단해 현재 실행 범위에서 제외하도록 요청했다.

현재 증거는 명확하다.

- `pending-v1/records.jsonl`은 600행 모두 `review_status=pending`, `reviewer_id=null`이다.
- 실제 사람 decision/adjudication JSONL과 `review-v1` 디렉터리는 없다.
- 따라서 이 corpus는 독립 검수·동결·평가 점수 산출 조건을 충족하지 않는다.
- 검수용 로컬 HTTP 서버는 종료됐다.

## 2. Impact Analysis

### Epic Impact

- Story 4.3은 현재 실행에서 보류한다. 구현된 계약·CLI·UI·테스트는 삭제하지 않는다.
- Epic 4 Gate B는 Story 4.3이 다시 명시적으로 해제되고 실제 사람 검수가 완료될 때까지 중단된다.
- Story 4.4–4.13은 기존처럼 동결한다. 이 600건으로 freeze, metrics, tournament 또는 모델 비교를 시작하지 않는다.
- 새 Epic이나 대체 AI 검수 Story는 만들지 않는다. AI 자기검수를 인간 검수로 위장하지 않는다.

### Requirements / Architecture Impact

- FR17과 Architecture의 “independently sourced, reviewed, hashed and frozen” 요구는 장기 요구사항으로 유지한다. 요구사항을 완화하거나 삭제하지 않는다.
- 즉시 Qwen Reasoner v3 재제출 경로는 Story 4.3과 독립이므로 계속 가능하다.
- Shadow Private 근거가 없으므로 상위 모델 또는 Reasoner v3의 평가·선정 결과에 이 corpus 점수를 인용할 수 없다.
- 별도 PRD, UX, API, 인프라 변경은 필요 없다.

### Technical / Artifact Impact

- 600개 pending record, 600개 검증 이미지, provenance/hash, review engine, 템플릿, 번역, UI와 테스트를 감사 가능한 미완료 산출물로 보존한다.
- `reviewed`, `adjudicated`, `promotion_ready=true`, frozen dataset version 또는 local robust metric을 생성하지 않는다.
- 데이터·코드 롤백이나 1.2GB 이미지 삭제는 수행하지 않는다.

## 3. Recommended Approach

선택: **직접 조정 + 현재 MVP 범위 보류**

- 노력: 낮음
- 기술 위험: 낮음
- 검증 근거 공백 위험: 중간
- 일정 영향: 당장의 수동 검수 시간을 제거하지만 Epic 4 기반 모델 선정을 무기한 연기한다.

완료된 구현을 롤백하는 선택지는 감사 증거와 향후 재개 비용만 악화하므로 채택하지 않는다. 사람 검수 대신 AI 승인을 넣는 선택지도 독립성 요구를 위반하므로 채택하지 않는다.

## 4. Detailed Change Proposals

### Story 4.3 상태

**OLD**

```text
Status: in-progress
사람 검수 checkpoint가 미완료인 활성 Story
```

**NEW**

```text
Status: backlog
Human-owned hold (2026-06-21): 현재 실행에서 사람 검수를 제외한다.
600건은 pending으로 보존하고 평가·동결·모델 비교에 사용하지 않는다.
재개에는 Story 4.3의 새 명시적 사용자 승인이 필요하다.
```

이유: 구현 완료와 데이터 승인 완료를 구분하고, 검수되지 않은 label을 평가 정답으로 오인하지 않기 위해서다.

### Sprint status

**OLD**

```yaml
4-3-independently-review-adjudicate-and-balance-samples: in-progress # UNLOCKED by user 2026-06-21
```

**NEW**

```yaml
4-3-independently-review-adjudicate-and-balance-samples: backlog # DEFERRED by user 2026-06-21; artifacts preserved
```

이유: 활성 실행을 종료하고 Epic 4의 기존 human-owned lock으로 되돌린다.

### Epic 4 cached context

**OLD**

```text
The user explicitly unlocked Story 4.3 review work.
```

**NEW**

```text
Story 4.3 was deferred by the user on 2026-06-21; all Epic 4 work is frozen until a new explicit unlock.
```

이유: 다음 agent가 과거 unlock을 현재 권한으로 오해하지 않도록 한다.

### 보존되는 항목

- `data/shadow-private/pending-v1/**`
- `data/shadow-private/image-pool-v1/**`
- `src/multimodal_bias/shadow_review.py` 및 관련 schema/CLI
- 검수 template/UI/한국어 번역/launcher
- Story 4.3 CPU-safe 테스트와 기존 검증 증거

## 5. Implementation Handoff

변경 규모: **Moderate — backlog 재정렬**

Product Owner / Developer가 다음만 수행한다.

1. Story 4.3 문서에 human-owned hold와 사용 금지 경계를 기록한다.
2. `sprint-status.yaml`의 Story 4.3을 `backlog`로 되돌리고 날짜를 갱신한다.
3. `epic-4-context.md`의 과거 unlock 문구를 보류 상태로 바꾼다.
4. 데이터·코드·이미지는 삭제하거나 재분류하지 않는다.
5. Story 4.4+, 모델 평가, sealed holdout 실행은 시작하지 않는다.

성공 기준:

- Story 4.3과 sprint status가 backlog/deferred로 일치한다.
- 600건 모두 pending이고 `review-v1`이 존재하지 않는다.
- Shadow Private promotion/freeze/evaluation artifact가 생성되지 않는다.
- Qwen Reasoner v3 즉시 경로 외 동결 범위는 변경되지 않는다.

## 6. Checklist Result

- [x] 1.1–1.3 Trigger, problem, evidence 확인
- [x] 2.1–2.5 Epic 4 및 후속 Story 영향 확인
- [x] 3.1 Requirements 충돌 분석 — 장기 FR17 유지
- [x] 3.2 Architecture 충돌 분석 — 설계 유지, 실행만 보류
- [N/A] 3.3 별도 UX specification 없음
- [x] 3.4 데이터·코드·테스트·운영 문서 보존 결정
- [x] 4.1 직접 조정 viable — low effort / low technical risk
- [x] 4.2 rollback not viable — 증거 손실 대비 이득 없음
- [x] 4.3 MVP review viable — 즉시 경로에서 FR17 실행 보류
- [x] 4.4 직접 조정 + 보류 선택
- [x] 5.1–5.5 제안서와 handoff 작성
- [x] 6.1–6.2 일관성·정확성 검토
- [x] 6.3 사용자 최종 승인 완료
- [x] 6.4 sprint/story/context 반영 완료
- [x] 6.5 handoff 완료 보고
