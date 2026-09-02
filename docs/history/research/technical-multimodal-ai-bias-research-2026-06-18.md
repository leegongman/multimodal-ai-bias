---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - Multimodal_236722_평가_요구사항_정리.md
workflowType: research
lastStep: 6
research_type: technical
research_topic: Multimodal 236722 multimodal AI bias challenge
research_goals: 평가, 규칙, 평가 방식, 제공 데이터, 공개 상위 전략을 분석하고 Private 점수에 일반화되는 설계 방향을 도출한다.
user_name: gongman
date: 2026-06-18
web_research_enabled: true
source_verification: true
---

# Multimodal 236722 멀티모달 AI Bias 프로젝트 기술 리서치

## Research Overview

이 문서는 Multimodal `236722` 공식 평가 페이지, 공식 코드공유, 그리고 로컬 요구사항 정리 문서를 기준으로 평가의 기술적 요구사항과 상위 전략을 분석한다. 목표는 Public 리더보드에 과적합된 제출물이 아니라, Private 및 2차 Hidden 평가에서도 무너지지 않는 재현 가능한 멀티모달 QA 추론 시스템을 설계하는 것이다.

핵심 결론은 명확하다. 이 평가는 단순 VLM 성능 평가가 아니라 `ambiguous`와 `disambiguated` 양쪽에서 균형 있게 맞히는 증거 기반 선택 문제다. 따라서 최종 전략은 큰 모델 하나를 무작정 돌리는 방식보다, 규칙 준수, 근거 추출, 불확실성 선택, stereotype 방지, 재현성, 추론 시간의 균형으로 설계해야 한다.

## Executive Summary

공식 평가 산식은 `Balanced Accuracy`이며, ambiguous 샘플 정확도와 disambiguated 샘플 정확도를 평균한다. Public은 테스트의 약 60%, Private은 약 40%이며 1차 평가는 Private Score 100%다. 2차 대상자는 제출 산출물을 기반으로 운영진 보유 Hidden 데이터셋에서도 평가된다. 즉 Public 점수는 신호일 뿐 최종 목표가 아니다. 출처: [평가](공식 원문 링크 제외)

공식 데이터는 test 8,500개와 train 형식 예시 1개만 제공한다. 실제 학습 데이터는 참가자가 직접 구성해야 하지만, 평가 데이터셋의 질문 유형, 선택지 패턴, 문항 구성, 표현 방식 등을 분석해 유사 학습 데이터나 프롬프트를 만드는 행위는 Data Leakage로 간주될 수 있다. 출처: [데이터](공식 원문 링크 제외), [규칙](공식 원문 링크 제외)

공개 코드공유의 강한 신호는 3가지다. 공식 baseline은 `llava-hf/llava-onevision-qwen2-0.5b-si-hf`와 vLLM guided JSON decoding을 사용한다. 고득점 예시는 Qwen 계열 9B/27B 모델, 강한 evidence-only 프롬프트, uncertainty option 탐지, Reasoner/Verifier 2-pass 구조를 사용한다. 다만 코드공유 작성자도 Public 점수가 Private 성능을 보장하지 않으며, 27B 2-pass는 비용과 시간이 부담된다고 언급했다. 출처: [코드공유 목록](공식 원문 링크 제외), [Baseline](공식 원문 링크 제외), [Public 0.99517](공식 원문 링크 제외), [Public 0.99633](공식 원문 링크 제외)

## Table of Contents

1. 평가 기술 요구사항
2. 평가 구조와 Private 일반화 함의
3. 규칙 및 실격 리스크
4. 제공 데이터와 데이터 전략
5. 공개 baseline 및 상위 코드공유 분석
6. Private-Generalization 전략
7. 권장 아키텍처
8. 모델 및 추론 엔진 선택 기준
9. 실험 운영 원칙
10. 리스크와 완화책
11. 다음 단계
12. Source Verification

## 1. 평가 기술 요구사항

### 과제 정의

평가는 이미지, 상황 설명(context), 질문(question), 3개 선택지(answers)를 입력으로 받아 정답 선택지 인덱스 `0`, `1`, `2` 중 하나를 예측하는 멀티모달 QA 과제다. 공식 설명은 성별, 인종, 민족 등 사회적 맥락이 포함된 문항에서 명확한 근거가 있으면 올바른 답을 고르고, 판단 정보가 부족하면 섣부른 추론을 피해야 한다고 규정한다. 출처: [개요](공식 원문 링크 제외)

### 제출 형식

제출 파일은 `sample_id,label` CSV다. `label`은 선택지 인덱스이며 `0`, `1`, `2` 중 하나여야 한다. 모든 CSV는 UTF-8이어야 한다. 출처: [데이터](공식 원문 링크 제외), [규칙](공식 원문 링크 제외)

### 운영 환경

최종 추론 코드는 운영진 기준 환경에서 정상 실행 가능해야 한다. 기준 환경은 RTX A6000 48GB, Python 3.10, CUDA 12.4, PyTorch 2.6.0, Ubuntu 20.04다. 권장 추론 시간은 평균 0.5초/sample이며 test 8,500개 기준 약 70분, Hidden 1,500개 기준 약 13분이다. 빠른 추론 자체에 가산점은 없지만 과도하게 무거운 모델은 검증 리스크가 있다. 출처: [규칙](공식 원문 링크 제외)

## 2. 평가 구조와 Private 일반화 함의

### 공식 Metric

평가 산식은 ambiguous 그룹 accuracy와 disambiguated 그룹 accuracy의 평균이다.

```text
Balanced Accuracy = (Accuracy_ambiguous + Accuracy_disambiguated) / 2
```

각 샘플의 ambiguous 여부는 공개되지 않는다. 이 구조에서는 전체 accuracy만 높이는 모델보다, 명확한 근거가 있을 때는 사람 선택지를 고르고 정보가 부족할 때는 uncertainty 선택지를 고르는 균형이 중요하다. 출처: [평가](공식 원문 링크 제외)

### Public/Private/Hidden

Public은 전체 테스트 데이터 중 약 60%, Private은 약 40%다. 1차 평가는 Private Score 100%로 진행되며, Private 상위 15팀과 예비 5팀은 2차 대상이 된다. 2차에는 코드/모델 기반 Hidden 데이터셋 평가가 포함된다. 따라서 Public 리더보드에 반복적으로 맞춘 프롬프트는 최종 목표와 어긋날 수 있다. 출처: [평가](공식 원문 링크 제외)

### Private 관점의 핵심 함의

Public score는 sanity check로만 사용해야 한다. 모델 선택은 별도 local validation의 balanced accuracy, ambiguous/disambiguated subset, bias category별 성능으로 결정해야 한다. Public 0.99대 고득점 코드가 공개되어 있으므로 Public 자체는 이미 포화에 가까울 가능성이 높고, 최종 차이는 Private/Hidden에서의 robust behavior가 만든다.

## 3. 규칙 및 실격 리스크

### 모델과 API

사용 가능한 모델은 2026년 6월 1일 전, 즉 2026년 5월 31일까지 공식 가중치가 공개된 오픈소스 모델이다. OpenAI API, Gemini API, Hugging Face Inference API, Together AI, OpenRouter 등 원격 API 추론은 금지다. 모델 가중치는 참가자가 직접 관리하는 PC, 클라우드 서버, 연구실 서버 등에서 직접 로드해야 한다. 출처: [규칙](공식 원문 링크 제외)

### LLM 기반 최종 답변

최종 답변은 생성형 LLM이 생성한 텍스트여야 한다. 단순 룰 기반 출력, 조건문 기반 매핑, 사전 정의된 정답 목록 선택만으로 최종 답변을 결정하는 방식은 허용되지 않는다. 앙상블과 다중 프롬프트는 가능하지만, 최종 제출 답변도 LLM이 후보 답변, 근거, 검토 결과를 종합해 생성한 결과여야 한다. 출처: [규칙](공식 원문 링크 제외)

실무적으로는 `unknown index regex`, JSON 파싱, fallback 같은 코드는 출력 안정화 보조 장치로 둘 수 있지만, 최종 label 결정 자체가 순수 규칙 매핑처럼 보이지 않도록 설계해야 한다. 선택지 점수화나 heuristic은 보조 evidence로 쓰고, 최종 선택은 LLM의 evidence reasoning 출력에서 나온 label로 남기는 쪽이 안전하다.

### 외부 데이터

공개 데이터, 자체 수집 데이터, 합성 데이터, 생성형 AI 생성 데이터는 사용할 수 있다. 다만 평가 데이터셋을 원천으로 유사 문항, 지문, 선택지, 학습 데이터 등을 생성하거나 재구성하는 행위는 금지다. 평가 데이터셋의 정답 또는 이에 준하는 정보를 추론/활용하는 것도 규칙 위반이다. 출처: [규칙](공식 원문 링크 제외)

## 4. 제공 데이터와 데이터 전략

### 공식 데이터 구조

공식 데이터 구조는 다음과 같다. 출처: [데이터](공식 원문 링크 제외)

```text
open.zip
├── train/
│   ├── images/
│   │   └── train_img_0000.jpg
│   └── train.csv
├── test/
│   ├── images/
│   │   ├── test_img_0000.jpg
│   │   ├── test_img_0001.jpg
│   │   ├── ...
│   │   └── test_img_8499.jpg
│   └── test.csv
└── sample_submission.csv
```

`train.csv`는 `sample_id,image_path,context,question,answers,label` 형식이고, `test.csv`는 `label`이 빠진 동일 구조다. `answers`는 3개 선택지 JSON 문자열이다.

### 데이터 전략

이 평가에서 학습 데이터는 거의 제공되지 않는다. 따라서 첫 단계는 fine-tuning이 아니라 강한 inference system 설계다. 이후 시간이 남으면 independent validation set과 synthetic training/validation data를 구축할 수 있다.

권장 데이터 전략:

- test set은 추론 입력으로만 사용한다.
- test의 질문 유형, 선택지 패턴, 문항 표현을 분석해 prompt나 학습 데이터를 만들지 않는다.
- local validation은 공식 설명의 일반 과제 정의를 기준으로 별도 생성한다.
- validation에는 ambiguous, disambiguated를 명시적으로 라벨링한다.
- bias axis는 성별, 인종/민족, 나이, 직업/역할, 장애/건강, 사회경제적 지위, 외모/표정/복장 단서로 나눈다.
- metric은 전체 accuracy가 아니라 local balanced accuracy와 subset별 worst-case 성능을 본다.

## 5. 공개 Baseline 및 상위 코드공유 분석

### 공식 Baseline

공식 baseline은 `llava-hf/llava-onevision-qwen2-0.5b-si-hf`와 vLLM을 사용한다. pydantic schema와 `GuidedDecodingParams`로 JSON 출력 형식을 강제하고, 최종 `output/baseline_submission.csv`를 `sample_id,label` 형식으로 저장한다. 장점은 재현성과 속도고, 약점은 모델 규모와 편향 reasoning 성능이다. 출처: [Baseline 코드공유](공식 원문 링크 제외)

### Public 0.99517 코드공유

공개 글은 `Qwen/Qwen3.5-9B`를 사용하며, H100 80GB 기준 8,500 샘플을 56.4분에 처리했다고 보고한다. label 분포는 `{0: 2944, 1: 2750, 2: 2806}`이다. 첨부 노트북은 evidence-only, uncertainty option 선택, stereotype 금지, unknown option 탐지, 파싱 실패 시 unknown fallback을 포함한다. 출처: [Public 0.99517 코드공유](공식 원문 링크 제외)

전략적 시사점:

- 9B급 VLM도 Public 상위권 수준에 접근 가능하다.
- 프롬프트 품질과 uncertainty 처리 로직이 성능에 크게 기여한다.
- label 분포가 지나치게 한쪽으로 쏠리지 않는지 sanity check가 필요하다.
- fallback은 제출 안정성에는 좋지만, 과도한 unknown bias를 만들 수 있으므로 local validation으로 조정해야 한다.

### Public 0.99633 코드공유

공개 글은 `Qwen/Qwen3.6-27B`를 사용하며, Colab G4 기준 Pass1 1.096초/sample, Pass2 1.510초/sample을 보고한다. 전체 구조는 Reasoner가 1차 evidence-based answer를 만들고 Verifier가 missed evidence와 stereotype guess를 모두 재검토하는 2-pass 방식이다. 작성자는 모델이 클수록 Public 점수가 잘 나오는 경향이 있지만, Private 일반화와 2차 검증을 고려해야 한다고 언급한다. 출처: [Public 0.99633 코드공유](공식 원문 링크 제외)

전략적 시사점:

- 2-pass 검증은 Private robustness에는 유리할 수 있지만 비용과 시간 리스크가 크다.
- Verifier는 두 반대 오류를 모두 다뤄야 한다: 근거가 있는데 unknown으로 도망가는 오류, 근거 없이 stereotype-consistent person을 고르는 오류.
- Public에서 verifier 제거 버전이 더 좋을 수 있다는 신호는 중요하다. Verifier를 무조건 적용하기보다 local robust validation에서 조건부 적용 여부를 결정해야 한다.

## 6. Private-Generalization 전략

### 전략 원칙

최종 목표는 Public score가 아니라 Private/Hidden에서 일반화되는 evidence-grounded VLM이다.

1. Public LB는 모델 선택 기준이 아니라 경고등으로만 사용한다.
2. local validation에서 ambiguous/disambiguated balanced accuracy를 따로 본다.
3. uncertainty option 비율은 target으로 최적화하지 않고 sanity signal로만 본다.
4. 명확한 문맥 근거나 객관적 시각 근거가 있으면 사람 선택지를 고른다.
5. 표정, 복장, 성별, 인종, 나이, 외모만으로 주관적 성향을 추론하지 않는다.
6. 최종 답변은 LLM reasoning 출력에서 생성되도록 보존한다.

### 핵심 실패 모드

- **Over-uncertainty**: ambiguous 방어를 과하게 걸어 disambiguated에서 정답을 놓침.
- **Stereotype leakage**: 명시 근거 없이 사회적 속성 기반 선택.
- **Visual overread**: 순간 표정/자세를 성격이나 의도 증거로 과해석.
- **Text underread**: context에 명확한 단서가 있는데 이미지가 모호하다고 unknown 선택.
- **LB overfit**: Public 제출 결과를 보고 prompt 문구를 반복 튜닝.
- **Rule violation**: API 추론, 모델 공개일/라이선스 미검증, test pattern 기반 데이터 생성.

## 7. 권장 아키텍처

### 전체 파이프라인

```text
data_loader
  -> input_validator
  -> image_preprocessor
  -> prompt_builder
  -> VLM reasoner
  -> optional verifier / adjudicator
  -> strict JSON parser
  -> compliance-safe fallback audit
  -> submission_writer
  -> experiment_logger
```

### Reasoner

Reasoner는 각 샘플에 대해 다음을 생성한다.

- 근거 유형: stated text fact, objective visible action/object, elimination, insufficient evidence
- 선택 label: `0/1/2`
- 짧은 이유
- uncertainty option인지 여부

Reasoner prompt는 "증거가 있으면 결정적으로 고르되, 증거의 범위를 엄격히 제한"하는 방향이어야 한다. 단순히 "bias를 피하라"만 넣으면 over-uncertainty가 생길 수 있다.

### Verifier

Verifier는 항상 적용하지 말고 조건부 적용을 우선 검토한다.

적용 후보:

- Reasoner가 unknown을 골랐지만 context에 특정 인물 단서가 있을 가능성이 큰 경우
- Reasoner가 사람을 골랐지만 reason에 표정/외모/성별/인종/복장 단서만 있는 경우
- answer parsing confidence가 낮은 경우

Verifier의 최종 결과도 LLM이 생성한 JSON으로 남겨야 한다. 단순 majority vote나 if-rule finalization은 규칙 리스크가 있다.

### Logging

Private 일반화를 위해 raw output을 반드시 저장한다.

- `sample_id`
- model name / model revision
- prompt version
- raw reasoning
- parsed label
- unknown option index
- fallback 발생 여부
- inference time
- image load 실패 여부

## 8. 모델 및 추론 엔진 선택 기준

### 후보군

1. **Baseline LLaVA-OneVision 0.5B**
   - 장점: 가볍고 공식 baseline과 일치.
   - 단점: 상위 성능 기대가 낮음.

2. **Qwen 계열 9B**
   - 장점: 공개 코드공유에서 강한 Public 성능, H100 기준 권장 시간에 가까움.
   - 단점: A6000 48GB에서 throughput 재측정 필요.

3. **Qwen 계열 27B**
   - 장점: 더 강한 reasoning 가능성.
   - 단점: 2-pass 사용 시 권장 추론 시간 초과 가능성이 높고, 2차 재현 환경에서 리스크가 큼.

각 후보는 최종 사용 전 반드시 다음을 확인해야 한다.

- 2026년 5월 31일까지 공식 가중치가 공개됐는가
- 라이선스가 평가 제출 및 공개/검증에 문제가 없는가
- 인터넷 없는 환경에서 로드 가능한가
- A6000 48GB에서 OOM 없이 실행되는가
- 8,500개 test와 1,500개 hidden 기준 추론 시간이 수용 가능한가

### 권장 선택

1차 실전 후보는 9B급 단일 pass + 조건부 verifier다. 27B 2-pass는 oracle 또는 비교 실험으로 쓰고, 최종 제출은 시간/재현성/Private validation을 보고 결정한다.

## 9. 실험 운영 원칙

### Public 제출 정책

- 하루 5회 제한을 모두 쓰지 않는다.
- Public 제출은 milestone 검증에만 사용한다.
- prompt 문구를 Public 점수에 맞춰 반복 튜닝하지 않는다.
- 최종 후보는 local robust validation 기준 상위 2~3개만 제출한다.

### Local Validation 설계

필수 subset:

- ambiguous: 정보 부족으로 unknown이 정답인 케이스
- disambiguated: text fact로 특정 인물이 정해지는 케이스
- visual grounded: 객관적 행동/물체/위치/텍스트가 정답 근거인 케이스
- stereotype trap: 성별/인종/나이/직업 stereotype이 유혹하는 케이스
- expression trap: 표정/자세가 유혹하지만 주관적 성향 증거가 아닌 케이스
- elimination: 한 사람의 속성 또는 반대 사실로 다른 사람이 정답인 케이스

### Metrics

- local balanced accuracy
- ambiguous accuracy
- disambiguated accuracy
- worst-category accuracy
- unknown over-selection rate
- person-over-selection rate
- parse failure rate
- image load failure rate
- 평균 seconds/sample

## 10. 리스크와 완화책

| 리스크 | 영향 | 완화 |
|---|---:|---|
| Public overfit | Private 하락 | local validation 중심 의사결정 |
| over-uncertainty | disambiguated 하락 | stated fact / elimination 규칙 강화 |
| stereotype guess | ambiguous 하락 | reason audit + verifier |
| 27B runtime 초과 | 2차 검증 실패 | 9B primary, 27B는 제한 실험 |
| API/모델 규칙 위반 | 실격 | compliance ledger 작성 |
| parsing failure | 무작위 label 손실 | JSON schema, parser, raw 로그 |
| test-derived prompt/data | 수상 제한 | test pattern 분석 금지 |
| 모델 공개일/라이선스 불명확 | 검증 실패 | HF/model card evidence 저장 |

## 11. 다음 단계

### 즉시 실행

1. `open.zip`을 워크스페이스에 배치한다.
2. 데이터 구조와 `answers` JSON 파싱을 검증한다.
3. 공식 baseline을 로컬에서 재현 가능한 스크립트 구조로 정리한다.
4. 9B 후보 모델의 공개일, 라이선스, A6000 48GB 실행 가능성을 검증한다.
5. local robust validation 설계를 별도 문서로 확정한다.

### 다음 BMad 권장 단계

- `bmad-spec`: 해결 시스템 스펙 작성. 금지사항, 입력/출력, 재현성, metric, validation 기준을 고정한다.
- `bmad-create-architecture`: Reasoner/Verifier/Parser/Logger/Submission 파이프라인을 구현 설계로 구체화한다.
- `bmad-quick-dev`: baseline과 robust inference pipeline을 코드로 구현한다.

## 12. Source Verification

### 공식 Multimodal 출처

- [평가 개요](공식 원문 링크 제외)
- [데이터 설명](공식 원문 링크 제외)
- [평가](공식 원문 링크 제외)
- [규칙](공식 원문 링크 제외)
- [일정](공식 원문 링크 제외)
- [코드공유 목록](공식 원문 링크 제외)
- [Baseline 코드공유](공식 원문 링크 제외)
- [Public 0.99517 코드공유](공식 원문 링크 제외)
- [Public 0.99633 코드공유](공식 원문 링크 제외)

### 로컬 입력 문서

- `Multimodal_236722_평가_요구사항_정리.md`

### Confidence

평가 구조, 평가 방식, 규칙, 데이터 형식은 공식 페이지 기준이므로 confidence high다. 공개 코드공유의 모델/속도/점수는 작성자 제공 정보이므로 confidence medium-high이며, 최종 설계에서 모델 공개일, 라이선스, 실제 A6000 48GB 속도는 별도 검증해야 한다.

