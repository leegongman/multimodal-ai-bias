# Multimodal High Score 참고 자료

Multimodal 236722의 상위 점수·수상 코드와 공식 베이스라인을 프로젝트의 실험 기준선과 비교하기 위한 참고 영역입니다.

이 폴더의 목적은 다른 참가자의 코드를 그대로 프로젝트 코드로 섞는 것이 아니라, 어떤 접근이 높은 점수와 재현성을 보였는지 기록하고 우리 프로젝트에 적용할 아이디어를 추적하는 것입니다.

## 분류

```text
references/high-score/
├── README.md
├── comparison.md                 # 코드공유와 우리 실험의 비교표
├── templates/solution-card.md    # 상위 코드별 기록 양식
├── official-baseline/            # Multimodal 공식 베이스라인
└── top-solutions/                # Private 점수·등수·수상 여부를 우선한 상위 참고
```

## 현재 등록된 자료

### 공식 베이스라인

- [LLaVA-OneVision 기반 멀티모달 QA 추론](official-baseline/000-llava-onevision.md)

### 상위 참고 코드

- [4위, Public 1.0 / Private 0.9332142857](top-solutions/001-rank-04-public-1.0-private-0.9332142857.md)
- [장려상, Public 0.99975 / Private 0.9354759](top-solutions/002-award-public-0.99975-private-0.9354759.md)
- [Public 0.99633, Qwen3.6-27B](top-solutions/003-public-0.99633-qwen3.6-27b.md)
- [Public 0.99517, Qwen3.5 9B](top-solutions/004-public-0.99517-qwen3.5-9b.md)

## 기록 원칙

1. Public 점수만으로 “최고 성능”이라고 판단하지 않습니다. Private 점수, 등수, 수상 여부, 추론 시간과 재현 가능성을 함께 기록합니다.
2. 게시물 본문에서 확인한 사실과 우리 프로젝트에서 재현한 결과를 구분합니다.
3. 다운로드한 코드는 저작권·라이선스·평가 약관을 확인하기 전까지 공개 저장소에 커밋하지 않습니다.
4. 평가 제공 데이터, 제출 파일, 모델 가중치, 대용량 실행 결과는 이 저장소에 포함하지 않습니다.
5. 우리 코드에 반영한 아이디어는 원본 게시물 링크와 적용한 커밋 또는 실험 결과를 함께 남깁니다.

## 상태 표기

- `reference-only`: 링크와 메모만 확인한 상태
- `locally-reproduced`: 로컬에서 핵심 흐름을 재현한 상태
- `adopted`: 우리 프로젝트 코드에 반영한 상태
- `rejected`: 검토했지만 성능·시간·규정·재현성 문제로 채택하지 않은 상태

원문 목록은 [Multimodal 코드공유 페이지](공식 원문 링크 제외)에서 확인합니다. 이 저장소에서는 게시판 이름보다 자료의 목적을 드러내기 위해 `high-score`라는 폴더명을 사용합니다.
