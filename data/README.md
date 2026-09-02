# 데이터 준비

이 저장소에는 Multimodal 공식 평가 데이터와 대용량 이미지 원본을 포함하지 않는다.

## 공식 데이터

공식 평가 페이지에서 `open.zip`을 내려받아 로컬에서 압축 해제한다.

```text
data/raw/open/
├── train/
├── test/
└── sample_submission.csv
```

준비 후 다음 명령으로 레이아웃을 확인한다.

```bash
PYTHONDONTWRITEBYTECODE=1 uv run multimodal-bias \
  validate-data --data-root data/raw/open
```

공식 데이터는 평가 규정과 Multimodal 약관의 접근·사용·재배포 조건을 따라야 한다. GitHub issue, release, 외부 링크에 원본 데이터나 평가셋 이미지를 업로드하지 않는다.

## 외부 데이터 및 Shadow 자료

외부 데이터를 사용한 경우 다음 정보를 문서화한다.

- 출처와 원본 URL
- 라이선스와 재사용·재배포 조건
- 수집일과 checksum
- 프로젝트에서 사용한 subset과 변환 과정
- 다른 참가자가 동일하게 접근할 수 있는 방법

현재 Shadow Validation 자료는 candidate/image/pending 단계가 섞여 있으므로, 최종 gold label이 없는 pending 문항을 평가 기준으로 사용하지 않는다. 대용량 이미지와 raw metadata는 GitHub 공개 대상에서 제외한다.
