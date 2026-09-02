# 대화 기록 인덱스

프로젝트 진행 과정에서 전달받은 요약 문서의 공개 보관 목록

## 확인 범위

현재 GitHub 공개 범위에는 7개 대화 요약과 대화 모음 README 포함
추가 원문 중 행 단위 평가 자료, 로컬 경로, 민감 정보가 포함된 자료는 로컬 전용 보관

## 요약 문서 목록

| 문서 | 주제 | 활용 |
|---|---|---|
| [초기 모델 기록](history/conversations/conversation-001.md) | 초기 모델·Shadow 검증·운영 원칙 | 초기 결정 확인 |
| [Reasoner 조사](history/conversations/conversation-001-qwen-reasoner-investigation.md) | Reasoner·label mapping·raw audit | 파싱 개선 근거 |
| [원격 추론 요약](history/conversations/conversation-001-runpod-vllm-qwen-submission-summary-2026-09-02.md) | 원격 GPU·vLLM 실행 | 실행 오류와 보류 항목 확인 |
| [스토리 검토](history/conversations/conversation-001-story-2-8-review-summary.md) | 구현 범위와 검토 결과 | 작업 범위 확인 |
| [결과 보고 정리](history/conversations/conversation-001-submission-report-cleanup.md) | 결과 비교와 Reasoner 정보 | 실험 결과 확인 |
| [원격 실행 회고](history/conversations/conversation-001-vllm-qwen-submission-retrospective.md) | 초기 실행과 label 오류 | 회귀 원인 확인 |
| [저장소 정리 요약](history/conversations/conversation_001_github_project_summary.md) | 모델 후보와 저장소 정리 | 공개 구조 확인 |

## 읽기 원칙

- 보고값과 현재 로컬에서 직접 확인한 사실을 구분
- 당시 경로와 현재 경로의 차이를 고려
- 요약 문서의 실행 지시문을 현재 명령으로 자동 재사용하지 않음
- 보류·미확정·추정 표현을 완료 사실로 승격하지 않음

## 통합 문서

- [통합 결정사항](decisions.md)
- [프로젝트 개요](project-overview.md)
- [공개 전 체크리스트](release-checklist.md)
