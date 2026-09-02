# 코드공유와 우리 실험 비교

이 표는 다른 참가자의 게시물에서 확인한 접근과 현재 프로젝트의 실험 방향을 비교하는 작업 문서입니다. 빈칸은 미확인 상태이며, 추측으로 채우지 않습니다.

| 구분 | 게시물 | 모델/구조 | 확인된 성능·속도 | 우리 프로젝트 적용 | 상태 |
|---|---|---|---|---|---|
| 공식 기준선 | [LLaVA-OneVision](official-baseline/000-llava-onevision.md) | LLaVA-OneVision 기반 멀티모달 QA | 게시물 상세 재확인 필요 | 기존 오프라인 추론 파이프라인의 기준선 | reference-only |
| 상위/수상 | [4위](top-solutions/001-rank-04-public-1.0-private-0.9332142857.md) | 상세 확인 필요 | Public 1.0 / Private 0.9332142857 | 비교 대상 등록 | reference-only |
| 상위/수상 | [장려상](top-solutions/002-award-public-0.99975-private-0.9354759.md) | 상세 확인 필요 | Public 0.99975 / Private 0.9354759 | 비교 대상 등록 | reference-only |
| 상위 참고 | [Public 0.99633](top-solutions/003-public-0.99633-qwen3.6-27b.md) | Qwen3.6-27B, Reasoner + Verifier 2-pass | Pass1 1.096초/sample, Pass2 1.510초/sample | Reasoner·검증·bias 방지 프롬프트 비교 | reference-only |
| 상위 참고 | [Public 0.99517](top-solutions/004-public-0.99517-qwen3.5-9b.md) | Qwen3.5 9B | H100 기준 8,500개 56.4분, 398ms/sample | Qwen 계열 기준선과 실행 시간 비교 | reference-only |

## 비교할 항목

- 모델과 가중치 출처
- 이미지 입력 및 processor 설정
- 프롬프트와 답변 형식
- Reasoner·Verifier·재시도·fallback 유무
- 선택지 라벨 파싱 및 잘못된 출력 처리
- 추론 장치, batch/quantization, sample당 시간
- Public/Private 점수와 label distribution
- 외부 데이터·외부 API 사용 여부
- 공개 가능한 코드인지, 링크만 남겨야 하는지

## 다음 기록 순서

1. Multimodal 게시물에서 실제 다운로드 파일명과 라이선스 또는 공유 조건을 확인합니다.
2. 게시물별 핵심 흐름을 우리 파이프라인 입력·출력 형식에 맞춰 작은 재현 실험으로 분리합니다.
3. 동일한 로컬 검증셋과 동일한 실행 환경에서 속도·파싱 실패율·라벨 분포를 비교합니다.
4. 채택한 아이디어만 `src/`, `configs/`, `scripts/`에 반영하고 이 표에 반영 커밋을 기록합니다.
