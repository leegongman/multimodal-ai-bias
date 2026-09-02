# 저장소 구조

GitHub 공개 저장소 기준의 표준 디렉터리 구조

```text
.
├── .github/workflows/       자동 테스트 설정
├── configs/                 모델·프롬프트·검증 설정
├── data/                    데이터 배치 문서 및 로컬 영역
├── deploy/                  원격 실행 재현 번들
├── docs/                    운영 문서·사양·이력
├── experiments/             분석·실험·검증 자료
├── references/              외부 공개 자료 분석
├── requirements/            환경별 의존성 목록
├── scripts/                 실행·검증 스크립트
├── src/multimodal_bias/     핵심 Python 패키지
├── tests/                   단위·계약 테스트
├── models/snapshots/        모델 보관 위치, Git 제외
├── runs/                    실행 산출물 위치, Git 제외
└── submissions/             제출 산출물 위치, Git 제외
```

## 디렉터리 역할

| 경로 | 역할 | 공개 기준 |
|---|---|---|
| `src/` | 재사용 가능한 핵심 로직 | 공개 |
| `scripts/` | 실행·검증 진입점 | 공개, 비밀값 제외 |
| `configs/` | 모델·프롬프트·검증 설정 | 공개, 로컬 경로 제외 |
| `tests/` | 회귀·계약 테스트 | 공개 |
| `experiments/` | 실험 기록과 비교 자료 | 선별 공개 |
| `docs/` | 사용법·사양·의사결정 이력 | 공개 |
| `data/` | 입력 데이터 준비 영역 | 원본 제외 |
| `models/` | 모델 가중치 영역 | 가중치 제외 |
| `runs/` | 실행 결과 영역 | 산출물 제외 |
| `submissions/` | 제출 파일 영역 | 민감 결과 선별 |

## 구조 원칙

루트에는 프로젝트 진입점과 대표 문서만 배치
기능 코드는 `src/`, 실행 진입점은 `scripts/`, 문서는 `docs/`에 배치
실험별 자료는 `experiments/` 아래에서 목적별로 분리
대용량·민감·재배포 제한 자료는 Git 추적에서 제외
