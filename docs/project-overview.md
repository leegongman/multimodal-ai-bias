# 프로젝트 개요

멀티모달 이미지·텍스트 QA 추론 및 평가 파이프라인의 구조와 현재 상태

## 목적

이미지, 문맥, 질문, 세 개 선택지를 입력으로 받아 선택지 인덱스 `0`, `1`, `2`를 예측하고 결과 파일을 생성하는 오프라인 파이프라인
명시적 근거와 합리적 배제를 우선하고 보호속성·외모·고정관념만으로 인물의 능력이나 역할을 추론하지 않는 운영 원칙

## 기술 구성

| 영역 | 구성 |
|---|---|
| 언어 | Python `>=3.10,<3.11` |
| 패키지 | `multimodal-bias` |
| 의존성 | Pillow, PyYAML, Typer |
| 개발 도구 | pytest, Ruff, uv |
| 모델 경로 | Hugging Face 로컬 어댑터, 원격 GPU·vLLM 재현 번들 |
| 입력 | `data/raw/open` 형식 |
| 출력 | 실행별 raw·parsed 결과와 결과 CSV |
| 검증 | 입력 레이아웃, 출력 파싱, Shadow audit·freeze·evaluate |

## 파이프라인

```text
입력 자료
  → 레이아웃 검증
  → 이미지·텍스트 SampleRecord 로딩
  → VLM 모델 어댑터
  → Reasoner 추론
  → raw output 보존
  → parser / verifier / arbitration
  → label 0·1·2 검증
  → 결과 CSV
```

Shadow Validation 흐름은 public-source metadata와 이미지를 후보화한 뒤 문항 생성, 검수, adjudication, audit, freeze, 평가 순서로 분리

## 실험 기준선

| 구성 | 보고값 | 해석 |
|---|---:|---|
| Qwen2.5-VL-7B 초기 경로 | `0.91` | label mapping 오류 가능성과 raw 보존 부족 확인 |
| Qwen3.5-9B Reasoner v3 | 약 `0.94` | 초기 개선 기록 |
| Qwen3.5-9B 공유 Reasoner 계열 | `0.9960833333` | 주요 기준선 |
| Qwen3.5-9B 2-pass | `0.99617` | 후속 인계 기록의 기준값 |

모든 값은 당시 기록의 보고값이며 현재 환경에서 재측정한 확정값이 아님

## 주요 결론

1. `label`은 선택지의 0-based 인덱스이며 특정 숫자를 불확실성 전용으로 해석하지 않음
2. 불확실성은 선택지 내용으로 판단하고 해당 선택지의 실제 인덱스를 출력
3. 모델과 프롬프트를 동시에 변경하지 않고 기준선 대비 변경 행 수와 agreement를 기록
4. 광범위한 프롬프트 재작성과 JSON-only 강제는 성능 저하 사례가 있어 주력 경로에서 제외
5. 행별 규칙·사후 라벨 패치는 누수와 재현성 문제로 사용하지 않음
6. 원격 실행은 raw output, prompt·image hash, engine metadata, 실행 로그를 영속 보존

## 현재 상태

- 핵심 패키지: 구현 완료
- 오프라인 테스트: `472 passed` 확인
- 저장소 구조: 표준 디렉터리 구조로 정리
- 공개 범위: 원본 자료·가중치·민감 산출물 제외
- 독립 검수와 최종 기준셋: 추가 확인 대상
- 공유 Reasoner 원본 prompt·parser·정확한 결과 매핑: 일부 확인 대상

## 외부 자원

- 입력 자료와 라이선스 확인 문서
- 모델 snapshot과 라이선스 정보
- GPU·CUDA·PyTorch·vLLM 호환 환경
- 실행별 설정, prompt, parser, raw output, 결과 CSV

외부 자원은 다운로드 절차, manifest, checksum, 보관 위치를 문서화하는 방식
