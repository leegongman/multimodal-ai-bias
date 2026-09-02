# 기여 가이드

## 작업 순서

1. 변경 목적과 영향 범위 확인
2. 작은 단위의 변경 수행
3. 관련 테스트 실행
4. 문서와 설정 링크 갱신
5. 변경 내용, 검증 결과, 남은 항목 기록

## 코드 기준

- Python 3.10 기준
- `src/multimodal_bias/` 내부 모듈 구조 유지
- 공개 코드에 로컬 절대 경로·비밀값·원본 데이터 포함 금지
- 새 실행 스크립트는 `scripts/` 배치
- 새 실험 자료는 `experiments/` 목적별 배치

## 검증 명령

```bash
uv sync
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q
uv run ruff check src tests
```

## 커밋 기준

커밋 메시지는 변경 목적을 짧게 표현
문서 변경은 링크와 공개 범위를 함께 확인
