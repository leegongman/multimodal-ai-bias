# Multimodal AI Bias

오프라인 이미지·텍스트 QA 추론 및 평가 파이프라인

저장소: `leegongman/multimodal-ai-bias`

## 프로젝트 개요

멀티모달 모델 기반 이미지·텍스트 질문 응답, 근거 기반 추론, 출력 파싱, 라벨 검증, 결과 생성 기능의 통합

## 주요 기능

- 로컬 이미지·텍스트 입력 처리
- VLM 어댑터 및 모델 설정 관리
- Reasoner·Verifier 프롬프트 관리
- 구조화 응답 파싱 및 라벨 검증
- 실험 결과 비교 및 재현성 기록
- 공개 가능한 고득점 접근 분석

## 저장소 구조

```text
src/                 핵심 Python 패키지
scripts/             실행·검증 스크립트
configs/             모델·프롬프트·검증 설정
tests/               단위·계약 테스트
data/                데이터 준비 문서 및 비공개 로컬 영역
experiments/         실험·파이프라인·검증 자료
deploy/              원격 실행 재현 번들
docs/                프로젝트 문서·사양·이력
references/          외부 공개 자료 분석
```

## 빠른 시작

### 설치

```bash
uv sync
```

### 테스트

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q
```

### 입력 데이터 검증

```bash
uv run multimodal-bias validate-data --data-root data/raw/open
```

공식 평가 자료는 별도 취득 및 로컬 배치 대상
모델 가중치와 대용량 산출물은 외부 보관 대상
GitHub 공개 범위는 [데이터 공개 정책](docs/data-policy.md) 기준

## 문서

- [문서 인덱스](docs/README.md)
- [프로젝트 개요](docs/project-overview.md)
- [프로젝트 규칙](docs/project-rules.md)
- [저장소 구조](docs/repository-layout.md)
- [대화 기록 인덱스](docs/conversations.md)
- [통합 결정사항](docs/decisions.md)
- [데이터 공개 정책](docs/data-policy.md)
- [공개 전 체크리스트](docs/release-checklist.md)
- [참고 자료](references/high-score/README.md)

## 현재 상태

- 핵심 Python 패키지: 구현 완료
- 오프라인 테스트: 통과 상태
- GPU 실행: 환경별 재현 절차 별도 기록
- 공개 저장소: 민감·대용량 자료 제외 상태

## 기여 및 보안

- [기여 가이드](CONTRIBUTING.md)
- [보안 정책](SECURITY.md)

## 라이선스

라이선스 확정 전 상태
포함된 외부 모델·데이터의 라이선스는 각 출처 기준
