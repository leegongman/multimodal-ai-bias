# Multimodal AI Bias

이미지와 텍스트를 함께 읽고, 명시된 근거와 관찰 가능한 시각 정보를 바탕으로 답을 선택하는 오프라인 VLM 추론·검증 파이프라인.

단일 모델 실행기를 넘어 데이터 검증, Reasoner 추론, raw output 보존, 구조화 파싱, 조건부 검증, 최종 CSV 검증까지 하나의 재현 가능한 시스템으로 통합.

```text
이미지 · 문맥 · 질문 · 선택지
                ↓
데이터 계약 검증
                ↓
VLM Reasoner 추론
                ↓
Raw output 보존 · 구조화 파싱
                ↓
조건부 Verifier · 라벨 검증
                ↓
sample_id,label 생성
```

핵심 목표는 인종·성별·외모·표정·사회적 역할만으로 능력이나 행동을 추정하지 않으면서, 이름·위치·행동·관계처럼 명시된 사실은 정확히 활용하는 추론 경계의 구현.

Repository: [`leegongman/multimodal-ai-bias`](https://github.com/leegongman/multimodal-ai-bias)

## Project Overview

이미지, 문맥, 질문, 세 개의 답변 선택지를 입력으로 받아 선택지 인덱스 `0`, `1`, `2` 중 하나를 예측하는 멀티모달 QA 시스템. 특정 인물을 지목할 근거가 부족한 경우에는 불확실성 선택을 유지하고, 이름·위치·행동 주체가 명시된 경우에는 해당 사실을 활용하도록 설계.

## Project at a Glance

| 항목 | 내용 |
|---|---|
| 작업 유형 | 이미지·텍스트 기반 3지선다 질문 응답 |
| 입력 | 이미지, 문맥, 질문, 세 개 선택지 |
| 출력 | `sample_id,label` 형식의 라벨 `0`, `1`, `2` |
| 전체 입력 규모 | 기록 기준 test 8,500행 |
| 로컬 검증셋 | v2 188문항, v3 188문항 |
| 핵심 기준 모델 | `Qwen/Qwen3.5-9B` |
| 추론 구성 | Reasoner 단일 패스 및 Reasoner + Verifier 2-pass |
| 실행 환경 | Python 3.10, uv, CUDA GPU, vLLM 번들 |
| 품질 검증 | 오프라인 테스트 472개, Ruff, 데이터·출력 계약 |

## Key Features

- 이미지·텍스트 샘플 로딩 및 데이터 레이아웃 검증
- 타입 기반 VLM adapter 및 모델 설정 관리
- 버전별 Reasoner·Verifier prompt template 관리
- Raw response 보존 및 구조화 답변 파싱
- 라벨·행 순서·스키마·결과 CSV 검증
- 재현 가능한 실행 메타데이터·hash·실험 비교
- 고위험 추론 문항에 대한 조건부 검증
- 고성능 접근 방식에 대한 참고 분석

## What This Project Does

### Multimodal Evidence Grounding

각 샘플을 이미지와 텍스트 문맥으로 함께 처리. 후보 라벨을 확정하기 전에 시각적 근거, 명시적 텍스트 근거, 근거 없는 가정을 분리하는 구조.

### Bias-Aware Reasoning

이 시스템은 다음 두 가지 능력을 동시에 요구.

- **모호한 상황의 보류**: 그룹 정체성, 보호속성, 직업적 고정관념, 표정만으로 개인을 지목하지 않는 능력
- **명시된 사실의 활용**: 이름, 위치, 행동, 관계가 명확히 제시된 경우 해당 인물을 선택하는 능력

항상 사람을 고르거나 항상 불확실성을 선택하는 방식 모두 오류 가능성. 근거에 기반한 인물 식별과 근거 없는 추론 사이의 경계를 안정적으로 유지하는 것이 핵심 과제.

### Reasoner–Verifier Separation

Reasoner가 모든 행에 대해 1차 근거와 후보 라벨을 생성. Verifier는 근거 없는 개인 지목이나 불필요한 불확실성 선택처럼 위험 신호가 있는 행만 재검토. 최종 단계에서 파싱 가능 여부, 라벨 범위, 행 수, 출력 순서를 검증.

### Reproducible Experiment Tracking

프롬프트 버전, 모델 설정, raw generation, 파싱 결과, 실행 메타데이터, hash, 결과 파일을 실행 단위로 추적. 어떤 모델·프롬프트·파서·실행 환경에서 결과가 생성됐는지 확인 가능한 구조.

## Dataset Overview and Characteristics

### Raw Input Layout

원본 입력은 저장소에 직접 커밋하지 않고 로컬에 배치. 기본 레이아웃은 다음 구조.

```text
data/raw/open/
├── train/
│   ├── train.csv
│   └── images/
├── test/
│   ├── test.csv
│   └── images/
└── sample_submission.csv
```

test CSV의 기본 필드는 다음 구성.

```text
sample_id,image_path,context,question,answers
```

각 행에는 이미지 경로, 상황을 설명하는 문맥, 질문, 세 개의 답변 선택지가 포함. 출력 라벨은 선택지 위치인 `0`, `1`, `2`이며, 불확실성 선택지가 항상 같은 숫자라는 가정은 사용하지 않는 구조.

기록상 test 입력은 8,500행. test 라벨은 입력에 포함되지 않으므로 샘플 단위 공식 정답률은 주장하지 않는 원칙. 원본 이미지와 대용량 CSV는 공개 저장소 외부 보관.

### Observed Data Patterns

실험에서 확인된 핵심 난점은 단순한 시각 인식보다 인물 식별에 어떤 근거를 사용해도 되는지 판단하는 과정.

- 개인 식별 근거가 부족한 상태에서 보호속성 표현이 등장하는 문항
- 성별이나 직업적 역할을 실제 행동 주체로 오인하기 쉬운 문항
- 표정·자세·복장만으로 의도나 감정을 과도하게 추정하기 쉬운 문항
- 이름·위치·행동이 명시되어 특정 인물을 선택해야 하는 문항
- 단순 키워드 매칭만으로 해결하기 어려운 다문장 문맥 문항
- 어떤 행에서는 시각 정보가, 다른 행에서는 텍스트 정보가 결정적 근거가 되는 문항

기준 모델은 기록된 예측 중 58.6%에서 불확실성 선택지를 선택. 기준 모델·v3.1·2-pass 시스템은 전체 입력 중 8,089행, 약 95%에서 동일한 답을 생성. 모델 교체만큼 안정적인 추론 경계 유지가 중요하다는 분석.

### Local Validation Sets

모델과 프롬프트 변경을 비교하기 위한 내부 검증셋이며 원본 정답을 대체하는 자료는 아님. 이미지 픽셀과 대용량 원본 산출물은 별도 로컬 영역 보관.

| 버전 | 규모 | 구성 | 목적 |
|---|---:|---|---|
| v2 | 188문항 | 모호 90, 명시 사실 98 | 기본 추론 경계와 라벨 매핑 확인 |
| v3 | 188문항 | 모호 90, 명시 사실 98 | 안내 문구를 줄인 난이도 상향 검증 |

v2·v3의 세부 서브셋은 다음 구성.

| 서브셋 | 수량 | 확인 내용 |
|---|---:|---|
| `ambiguous_protected` | 50 | 보호속성만으로 개인을 지목하는 오류 방지 |
| `ambiguous_gender_role` | 20 | 성별·역할 고정관념에 의한 과추론 방지 |
| `ambiguous_expression` | 20 | 표정·자세 기반 의도 추정 방지 |
| `disambiguated_named` | 48 | 이름과 행동 주체의 연결 |
| `disambiguated_position` | 32 | 위치 기반 grounding과 소거 추론 |
| `disambiguated_protected` | 18 | 보호속성이 있어도 명시 사실을 사용하는지 확인 |

평가는 단일 종합 점수만으로 판단하지 않는 구조. `Acc_ambiguous`, `Acc_disambiguated`, 서브셋별 정확도, 라벨 분포, 파싱 실패율, 실행 시간을 함께 비교.

## Models and Experiment Results

| 모델 | 사용 목적 | 기록 결과 및 판단 |
|---|---|---|
| [`Qwen/Qwen3.5-9B`](https://huggingface.co/Qwen/Qwen3.5-9B) | 주력 Reasoner 기준선, v3.1, 2-pass | 기록 점수 약 `0.99608`~`0.99617`, 핵심 기준선 |
| [`Qwen/Qwen2.5-VL-7B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct) | 초기 로컬 VLM 및 vLLM 후보 | 로컬 다운로드·일부 생성 확인, HF 순차 경로는 느리고 vLLM 호환성 보완 필요 |
| [`openbmb/MiniCPM-V-4_5`](https://huggingface.co/openbmb/MiniCPM-V-4_5) | 초기 VLM 후보 | 실제 이미지 smoke test 성공, 처리량 문제로 전체 실행 보류 |
| [`Qwen/Qwen2.5-VL-32B-Instruct-AWQ`](https://huggingface.co/Qwen/Qwen2.5-VL-32B-Instruct-AWQ) | 대형 양자화 비교 후보 | 기록 점수 `0.98983`, 9B 기준선보다 낮은 결과 |
| [`cyankiwi/Qwen3.5-35B-A3B-AWQ-4bit`](https://huggingface.co/cyankiwi/Qwen3.5-35B-A3B-AWQ-4bit) | 35B AWQ 비교 실험 | 기록 점수 `0.9695`, 모델 크기만으로 개선되지 않은 결과 |
| [`cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit`](https://huggingface.co/cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit) | 계열 간 비교 | 기록 점수 `0.99175`, 주력 기준선보다 낮은 결과 |
| [`OpenGVLab/InternVL3-14B`](https://huggingface.co/OpenGVLab/InternVL3-14B) | 시각 grounding 후보 | 명시 사실 서브셋 하락, 약 `1.41초/sample` 기록 |

[`LLaVA-OneVision`](https://huggingface.co/llava-hf/llava-onevision-qwen2-7b-ov-chat-hf), [`Qwen3.6-27B`](https://huggingface.co/Qwen/Qwen3.6-27B), Qwen3.5-9B 관련 고성능 접근은 비교를 위해 `references/high-score/`에 별도 보관. 외부 구현은 그대로 복사하지 않고 모델·프롬프트·파서·처리량·점수·재현성 기준으로 분석.

### Key Findings from the Experiments

- 더 큰 모델이 자동으로 더 좋은 결과를 만들지는 않은 결과. 모호한 문항에서 불확실성을 유지하면서 명시 사실 문항에서는 정확히 선택하는 능력이 핵심.
- 복잡한 전역 규칙을 많이 추가한 프롬프트보다 간결하고 안정적인 Reasoner 프롬프트가 더 안정적인 경향.
- JSON-only 출력을 과도하게 강제한 실험에서 8,500행 중 391행만 파싱. 출력 복잡화가 생성 품질과 파서 안정성을 함께 저하시킬 수 있음을 확인.
- 2-pass Verifier가 로컬 검증셋의 일부 위험 구간을 개선했으나, 전체 기록 점수는 단일 v3.1과 같은 `0.99617`에 머문 결과.
- HF 순차 추론은 전체 입력 처리에 비효율적. A6000 48GB 환경에서는 vLLM 서버 또는 배치 실행 경로가 필요한 구조.

## Inference Pipeline

```text
CSV + 이미지 파일
        │
        ├─ validate-data: 경로 · 필드 · 이미지 · 행 수 검증
        │
        ├─ SampleRecord: 이미지 · 문맥 · 질문 · 선택지 정규화
        │
        ├─ Reasoner: 근거 기반 1차 응답 생성
        │       └─ raw_reasoner.jsonl 보존
        │
        ├─ Parser: 모델 출력에서 라벨 · 근거 · 상태 추출
        │
        ├─ Verifier: 고위험 행 조건부 재검토
        │
        ├─ Arbitration: 추론·검증 결과 결합
        │
        └─ Submission validator: 행 수 · 순서 · 라벨 · CSV 스키마 확인
```

### Output Contract

- 최종 라벨은 반드시 `0`, `1`, `2` 중 하나.
- 라벨은 선택지 인덱스이며 불확실성 선택지에 고정된 숫자는 없음.
- 불확실성 판단은 모델 출력과 답변 선택지 내용에 기반.
- 규칙 기반 조건문으로 모델의 최종 라벨을 직접 덮어쓰지 않는 원칙.
- Raw 응답, 파싱 실패, fallback, 검증 전환 이력을 보존.

## Repository Layout

```text
src/                 핵심 Python 패키지
scripts/             추론·검증 실행 진입점
configs/             모델·프롬프트·검증 설정
tests/               단위·계약·회귀 테스트
data/                데이터 계약 및 로컬 입력 영역
experiments/         실험 파이프라인 및 분석 자료
deploy/              원격 GPU 재현 번들
docs/                설계 기록 및 프로젝트 이력
references/          외부 접근 방식 비교 자료
```

## Quick Start

### Installation

```bash
uv sync
```

### Test the Pipeline

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q
```

### Validate Local Input Data

```bash
uv run multimodal-bias validate-data --data-root data/raw/open
```

원본 입력은 별도 취득 후 `data/raw/open/` 아래에 배치. 모델 가중치와 대용량 실행 산출물은 외부 보관. 저장소 구조와 로컬 데이터 기준은 프로젝트 내부 구성에 반영.

## License

프로젝트 라이선스는 미확정 상태. 외부 모델·데이터·참고 구현의 라이선스와 재배포 조건은 각 원 출처 기준 확인 대상.
