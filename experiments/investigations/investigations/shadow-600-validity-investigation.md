# Investigation: 600건 Shadow 데이터셋 정답성과 평가 Test 유사성

## Hand-off Brief

1. **What happened.** 600건 데이터는 파일상 존재하지만, 보고서가 독립 검수 0건과 승격 불가 상태를 명시하므로 정답 라벨이 검증됐다는 주장은 현재 반박된다.
2. **Where the case stands.** 정답성은 직접 증거로 판단 가능하며, 8,500건과의 유형 유사성은 스키마·템플릿·분포 비교가 아직 필요하다.
3. **What's needed next.** pending 600건과 공식 Test 8,500건의 구조·문항 유형·선택지·불확실성 표현을 정량 비교한다.

## Case Info

| Field            | Value |
| ---------------- | ----- |
| Ticket           | N/A |
| Date opened      | 2026-06-22 |
| Status           | Active |
| System           | Local workspace, macOS |
| Evidence sources | `data/shadow-private/pending-v1/{report.json,audit.json,records.jsonl}`, `data/raw/open/test/test.csv` |

## Problem Statement

사용자 질문: AI가 생성한 독립 Shadow 600건에 실제 정답 라벨이 제대로 붙어 있는가, 그리고 공식 Test 8,500건의 데이터 유형과 유사한가?

## Evidence Inventory

| Source | Status | Notes |
| ------ | ------ | ----- |
| `data/shadow-private/pending-v1/report.json` | Available | 600건, 독립 검수 대기, reviewed 0 |
| `data/shadow-private/pending-v1/audit.json` | Available | promotion_ready false, 전건 검수/재정 필요 위반 기록 |
| `data/shadow-private/pending-v1/records.jsonl` | Available | 600건 생성 레코드, 전체 내용 비교 미실시 |
| `data/raw/open/test/test.csv` | Available | 공식 Test 8,500건, 유형 비교 미실시 |
| 독립 인간/복수 모델 판정 기록 | Missing | 정답성 확정에 필요 |

## Investigation Backlog

| # | Path to Explore | Priority | Status | Notes |
| - | --------------- | -------- | ------ | ----- |
| 1 | 600건 라벨 생성 근거와 검수 상태 추적 | High | In Progress | 보고서상 미검수 확인 |
| 2 | 600건과 Test의 필드·선택지·불확실성 표현 비교 | High | Open | 정량 통계 필요 |
| 3 | 질문/문맥 유형과 이미지 의존도 비교 | High | Open | 템플릿 기반 비교 필요 |
| 4 | 샘플 시각 검증 | Medium | Open | 층화 표본 필요 |

## Timeline of Events

| Time | Event | Source | Confidence |
| ---- | ----- | ------ | ---------- |
| 2026-06-21 | 600개 pending 문항 생성 | `data/shadow-private/pending-v1/report.json` | Confirmed |
| 2026-06-22 | 정답성·유사성 재조사 시작 | 사용자 요청 | Confirmed |

## Confirmed Findings

### Finding 1: 600건은 독립 검수가 완료되지 않았다

**Evidence:** `data/shadow-private/pending-v1/report.json:1`, `data/shadow-private/pending-v1/audit.json:1`

**Detail:** `review_status`는 `pending_independent_human_review`, `reviewed_count`는 0, `promotion_ready`는 false다. 감사 위반은 전건 검수 또는 재정이 필요하다고 명시한다.

## Deduced Conclusions

### Deduction 1: 현재 라벨을 실제 정답으로 간주할 수 없다

**Based on:** Finding 1

**Reasoning:** 생성된 expected label은 존재하지만 독립 검수·재정 증거가 0건이고 승격 게이트도 실패한다.

**Conclusion:** 600건은 평가 점수 계산용 정답셋이 아니라 pending 후보셋이다.

## Hypothesized Paths

### Hypothesis 1: 600건은 공식 Test 유형과 충분히 유사하다

**Status:** Open

**Theory:** 스키마와 목표 오류 유형은 유사하도록 설계됐지만 실제 질문 표현·이미지 의존도·편향 범주는 다를 수 있다.

**Supporting indicators:** 3개 선택지, 불확실성 위치 균형, ambiguous/disambiguated 하위 집합이 존재한다.

**Would confirm:** Test와의 정량 분포 및 층화 샘플 비교가 주요 차이를 보이지 않음.

**Would refute:** 질문 구조, 이미지-텍스트 결합, 범주 분포가 Test와 체계적으로 다름.

**Resolution:** Open.

## Missing Evidence

| Gap | Impact | How to Obtain |
| --- | ------ | ------------- |
| 독립 검수 결과 | 라벨 정확도 확정 불가 | 인간 또는 허용된 독립 판정 절차 |
| Test 대비 유형 통계 | 유사성 확정 불가 | 두 데이터셋의 구조·표현·유형 비교 |

## Source Code Trace

| Element | Detail |
| ------- | ------ |
| Error origin | N/A — 데이터셋 유효성 조사 |
| Trigger | 600건을 평가셋으로 사용할 수 있는지 질문 |
| Condition | 생성 라벨은 있으나 reviewed_count=0 |
| Related files | `src/multimodal_bias/shadow_review.py`, `spec-4-2b-shadow-image-and-pending-corpus.md` |

## Conclusion

**Confidence:** Medium

정답 라벨 미검수 상태는 Confirmed다. 공식 Test와의 유형 유사성은 아직 Open이며 정량 비교가 필요하다.

## Recommended Next Steps

### Diagnostic

600건과 Test 8,500건의 스키마, 선택지, 불확실성 표현, 문맥 근거 유형, 이미지 의존도, 편향 범주를 비교한다.

## Reproduction Plan

보고서 상태 확인 → 두 데이터셋 통계 비교 → 층화 샘플 시각 검토 → 라벨 검수 증거 확인 순으로 진행한다.
