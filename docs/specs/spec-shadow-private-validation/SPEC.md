---
id: SPEC-shadow-private-validation
companions:
  - dataset-contract.md
  - evaluation-and-freeze-policy.md
  - ../../history/specifications/spec-multimodal-ai-bias/validation-strategy.md
  - ../../history/specifications/spec-multimodal-ai-bias/compliance-references.md
sources: []
---

> **Canonical contract.** 이 SPEC과 `companions:` 파일은 300~600건 Shadow Private validation suite를 구축·동결·평가하기 위한 완전한 계약이다.

# Shadow Private Validation Suite

## Why

Public leaderboard는 hidden group 구성과 Private/Hidden 일반화를 직접 보여주지 않는다. 한 번의 0.91 제출이나 48건 진단셋만으로 Reasoner, 모델, 이미지 설정, Verifier 중 무엇이 실제 개선인지 선택하면 Public 과적합과 작은 표본 변동에 노출된다.

## Capabilities

- id: CAP-1
  intent: 팀은 평가셋에서 독립적인 300~600건 multimodal validation suite를 구축한다.
  success: 모든 sample이 허용된 출처, 라이선스/사용권, 작성·검수 기록을 가지며 evaluation/test-derived 항목이 0건이다.

- id: CAP-2
  intent: suite는 ambiguous와 다양한 resolvable failure mode를 분리해 측정한다.
  success: 필수 8개 subset이 최소 표본 gate를 충족하고 uncertainty option index 0/1/2가 각각 충분히 대표된다.

- id: CAP-3
  intent: 팀은 모델·prompt·Verifier 후보를 동일한 동결 데이터와 metric으로 비교한다.
  success: candidate report가 balanced accuracy, ambiguous/disambiguated accuracy, worst-subset, uncertainty-position accuracy, over-selection, harmful/beneficial flip, failure와 runtime을 포함한다.

- id: CAP-4
  intent: 팀은 반복 실험으로 Shadow Private 자체에 과적합하지 않도록 holdout을 봉인한다.
  success: dataset hash와 split manifest가 candidate 실험 전에 동결되고 sealed holdout의 sample-level 결과는 최종 후보 결정 전 공개되지 않는다.

- id: CAP-5
  intent: 팀은 local evidence로 후보를 승격하고 Public 점수는 sanity signal로만 사용한다.
  success: promotion rationale가 local gates, runtime/VRAM, compliance와 Public의 보조적 역할을 기록하며 실패 gate가 있는 후보를 승격하지 않는다.

## Constraints

- 총 표본 수는 300 이상 600 이하로 고정한다.
- 48건 mapping/image 진단셋은 Shadow Private promotion corpus와 분리한다.
- test/evaluation의 문구, 선택지 패턴, question type 분포, 이미지 또는 추론 정답을 dataset 제작에 사용할 수 없다.
- 허용 출처는 라이선스가 확인된 public, self-authored, self-collected, synthetic 또는 규칙상 허용된 생성 데이터뿐이다.
- uncertainty option은 index 0/1/2에 배치되며 label 숫자에 고정 의미를 주지 않는다.
- candidate 간 sample order, seed, generation setting과 metric implementation을 고정한다.
- Public score만으로 prompt, threshold, model 또는 Verifier를 선택하지 않는다.

## Non-goals

- Shadow Private를 train/fine-tuning 데이터로 사용하지 않는다.
- 48건 진단 결과를 최종 모델 순위로 사용하지 않는다.
- test data와의 유사성을 높이는 방식으로 validation을 설계하지 않는다.
- 사람 검수 없이 synthetic label을 정답으로 확정하지 않는다.

## Success signal

- 300~600건 suite가 provenance, label review, subset coverage, uncertainty-position balance와 frozen hash 검사를 통과하고, 후보 모델 tournament 및 Reasoner/Verifier 승격 결정이 재현 가능한 local report로 이루어진다.

## Assumptions

- 각 subset 최소 30건, uncertainty 위치별 30% 이상, ambiguous/resolvable 각각 최소 120건을 초기 coverage gate로 사용한다.
- sealed holdout은 전체의 30% 이상이면서 최소 120건으로 운영한다.
