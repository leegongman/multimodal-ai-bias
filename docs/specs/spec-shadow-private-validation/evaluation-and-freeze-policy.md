# Evaluation and Freeze Policy

## Corpus tiers

1. `diagnostic-48`: mapping, image-path, pixel-budget, engine 결함을 빠르게 분리한다. promotion 점수로 사용하지 않는다.
2. `shadow-private-300-600`: 모델, prompt, Verifier 승격을 위한 독립 suite다.

Shadow Private suite는 `selection`과 `sealed_holdout`으로 분리한다. sealed holdout은 전체의 30% 이상이며 최소 120건이다.

## Freeze protocol

- candidate tournament 전에 dataset files, image manifest, split manifest, schema version의 SHA-256을 기록한다.
- 동결 후 sample 추가·삭제·label 수정은 새 dataset version으로만 허용한다.
- selection split은 aggregate와 sample audit에 사용할 수 있다.
- sealed holdout은 최종 shortlist 전 aggregate metric만 공개하고 sample text, raw output, per-sample error를 prompt 작성자에게 노출하지 않는다.
- holdout을 열어 수정 결정을 내렸다면 해당 version은 더 이상 sealed가 아니며 새 holdout이 필요하다.

## Required metrics

- local balanced accuracy
- ambiguous accuracy
- disambiguated/resolvable accuracy
- worst-subset accuracy
- uncertainty-position accuracy for index 0/1/2
- unknown over-selection and person over-selection
- stereotype-trap and expression-trap error counts
- semantic consistency and parse failure rates
- image-load and unresolved rates
- verifier trigger rate, beneficial flips, harmful flips, no-effect flips
- average/p95 seconds per sample, peak VRAM, projected 8,500-row runtime

## Promotion gates

후보는 다음 조건을 모두 만족해야 한다.

- compliance blocker 0
- parse failure, image-load failure, unresolved가 제출 허용치 이내이며 최종 제출 후보는 unresolved 0
- 이전 후보 대비 worst-subset의 중대한 회귀 없음
- ambiguous 개선이 resolvable 붕괴로 얻어진 것이 아님
- uncertainty index 특정 위치에만 유의한 성능 붕괴가 없음
- A6000 48GB에서 전체 Reasoner와 선택된 Verifier 경로가 runtime gate를 통과함
- exact model revision/hash, prompt hash, engine/dependency version이 기록됨

Public score는 위 gate를 통과한 상위 2~3개 후보의 sanity check에만 사용한다.

