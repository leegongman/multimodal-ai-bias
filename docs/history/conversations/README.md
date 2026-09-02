# Conversation Reports - 2026-09-02

이 폴더는 Multimodal 236722 프로젝트 관련 대화 정리 문서를 보관한다.

## 문서 목록

| 문서 | 용도 | 상태 |
| -- | -- | -- |
| `conversation-001-multimodal-bias-model-shadow-validation.md` | 이번 대화에서 요청한 “GitHub 프로젝트 정리용 문서”. 모델 실험, RunPod/vLLM 운영, 제출 점수, Shadow Validation 구축 내용을 대화에서 확인된 범위로 정리했다. | 최종 정리본 |
| `conversation-001-multimodal-bias.md` | 기존에 존재하던 별도 대화 정리 문서. v3.1~v3.6, 2-pass/3-pass, hires, RunPod 수거, Gemma4 vLLM 환경 문제 등이 정리되어 있다. | 참고 문서 |

## 사용 기준

- GitHub 프로젝트 정리에는 우선 `conversation-001-multimodal-bias-model-shadow-validation.md`를 사용한다.
- `conversation-001-multimodal-bias.md`는 같은 프로젝트의 추가 실험 히스토리를 확인할 때 참고한다.
- 두 문서 모두 확인되지 않은 내용은 “확인되지 않음” 또는 “확인 필요”로 표기하는 원칙을 따른다.

## 현재 결론

현재 프로젝트 상태는 “부분 완료”다.

- 모델 제출 실험은 Qwen/Gemma 계열에서 일부 완료되었다.
- Shadow Validation은 600건 pending corpus와 review UI까지 생성되었다.
- 다만 사람 검수와 adjudication이 끝나지 않아 Shadow Validation은 아직 freeze 가능한 평가셋이 아니다.
