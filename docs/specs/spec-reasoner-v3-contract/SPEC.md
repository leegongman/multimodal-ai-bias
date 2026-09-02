---
id: SPEC-reasoner-v3-contract
companions:
  - output-contract.md
  - ../../history/specifications/spec-multimodal-ai-bias/SPEC.md
  - ../../history/specifications/spec-multimodal-ai-bias/compliance-references.md
  - ../../../experiments/investigations/submission-score-091-investigation.md
  - ../spec-epic-2-reasoner-mapping-and-raw-audit.md
sources: []
---

> **Canonical contract.** 이 SPEC과 `companions:` 파일은 Reasoner v3를 구현·시험·검증하기 위한 완전한 계약이다.

# Reasoner v3 선택지 의미 계약

## Why

Multimodal label은 의미 클래스가 아니라 현재 답안 배열의 0-based 인덱스다. Reasoner v2는 고정 `label 2 = uncertainty` 오류를 프롬프트에서 제거했지만, 불확실성 선택지의 실제 위치를 구조화해 보존하지 않아 parser, Verifier, arbitration과 validation이 숫자 label에 다시 의미를 부여할 위험이 남아 있다.

## Capabilities

- id: CAP-1
  intent: Reasoner는 선택한 답과 불확실성 답의 위치를 서로 독립적인 선택지 인덱스로 생성한다.
  success: 모든 유효 출력에 `label`과 `uncertainty_option_index`가 각각 `0`, `1`, `2` 중 하나로 존재하며 어느 숫자에도 고정 의미가 부여되지 않는다.

- id: CAP-2
  intent: 시스템은 생성된 label, 불확실성 위치, evidence 의미의 일관성을 검증한다.
  success: `uncertainty_signal == (label == uncertainty_option_index)`가 성립하고 uncertainty 선택은 `insufficient_evidence`, decisive 선택은 decisive evidence type을 갖지 않으면 parse가 실패한다.

- id: CAP-3
  intent: downstream 단계는 uncertainty 위치를 명시적으로 전달하고 감사한다.
  success: parsed Reasoner, Verifier, arbitration, validation, audit artifact가 schema version과 `uncertainty_option_index` lineage를 보존한다.

- id: CAP-4
  intent: 시스템은 유효한 LLM 생성 후보 없이 최종 label을 발명하지 않는다.
  success: Reasoner와 Verifier 모두 유효한 generated candidate를 제공하지 못하면 sample은 `unresolved`가 되고 submission 생성이 차단된다.

- id: CAP-5
  intent: 운영자는 v2와 v3를 동일 조건에서 비교해 계약 변경의 효과와 회귀를 판정한다.
  success: 독립 진단셋에서 uncertainty 위치 0/1/2별 parse 성공률, semantic consistency, 정확도, over-uncertainty를 비교한 보고서가 생성된다.

## Constraints

- `label`은 답안 배열의 0-based 인덱스이며 고정 person/uncertainty 의미를 갖지 않는다.
- `uncertainty_option_index`는 Reasoner가 모든 sample에서 직접 생성해야 하며 unknown 문구 regex, test-derived 사전, 고정 위치 규칙으로 만들 수 없다.
- 최종 label은 유효한 LLM 생성 텍스트에서만 유래해야 한다.
- `reasoner_v2`는 mapping-only A/B 기준으로 변경 없이 보존한다.
- test/evaluation 데이터의 문구, 선택지 패턴, 이미지 또는 추론 정답을 prompt/schema 규칙 작성에 사용할 수 없다.
- 원본 raw text, exact prompt/hash, image hash와 parse 오류를 보존한다.

## Non-goals

- Reasoner v3에서 모델 계열, 이미지 pixel budget 또는 추론 엔진을 동시에 변경하지 않는다.
- self-reported confidence를 검증 없이 verifier trigger로 사용하지 않는다.
- parser나 arbitration이 누락된 label을 보정하지 않는다.

## Success signal

- uncertainty 선택지가 index 0/1/2인 parameterized test와 독립 진단 A/B가 모두 통과하고, 코드·prompt·artifact에서 `label 2 = uncertainty` 전제가 사라지며, 생성 후보가 없는 sample은 submission 전에 명시적으로 차단된다.
