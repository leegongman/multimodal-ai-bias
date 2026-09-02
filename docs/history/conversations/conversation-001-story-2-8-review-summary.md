# 대화 001 - Story 2.8 리뷰 마감 및 실행 범위 동결 정리

## 목적

BMad 흐름에서 Story 2.8의 리뷰를 마감하고, 현재 프로젝트에서 당장 작업할 범위와 나중에 할 범위를 명확히 동결·분리하는 것이 목표였다.

## 핵심 요약

이 대화에서는 Epic 2 진행 중 Story 2.8의 리뷰 상태를 마감했다. 사용자는 MiniCPM뿐 아니라 모든 비현재 실행 경로를 건드리지 말라고 요청했고, 이에 따라 Qwen/Qwen2.5-VL-7B-Instruct 기반 Reasoner v3 즉시 재제출 경로만 현재 활성 범위로 문서화했다. Story 2.9, Story 2.10, Epic 3/4/5, 그리고 비Qwen 후보 모델 관련 작업은 모두 미래 작업으로 동결되었다. Story 2.8에 대해서는 BMad 코드 리뷰 흐름을 사용했고, 사용자 승인 후 3개 리뷰 관점의 서브에이전트 검토가 수행되었다. 리뷰 결과 5개 주요 보완 항목이 도출되었고, 사용자가 “1”을 선택해 전체 패치를 적용했다. 이후 집중 테스트, 전체 테스트, Ruff, CLI help/version 검증이 통과했다. 최종적으로 Story 2.8 상태는 `review`에서 `done`으로 변경되었다. GPU 제출물 생성 가능 단계는 아직 아니며, 다음 실제 작업은 동결 범위를 해제하지 않는 한 Qwen v3 재제출 경로 준비다.

## 시도한 작업

시간 순서대로 정리했다.

| 순서 | 시도한 내용 | 사용한 방법·명령어 | 결과 |
| -- | ------ | ---------- | --------------- |
| 1 | 현재 BMad 진행 상태 파악 | `$bmad-help` 사용, 현재 Story/Epic 상태 확인 | 성공 |
| 2 | Story 2.8 상태 확인 | Story 2.8 상태가 `review`, VS 검증 `READY FOR DEV`, DS 구현 완료, 테스트 404 passed로 보고됨 | 성공 |
| 3 | 비현재 실행 경로 동결 요청 반영 | 문서 수정: `AGENTS.md`, `README.md`, `spec-epic-2-reasoner-mapping-and-raw-audit.md`, `docs/history/epics.md`, `sprint-status.yaml`, MiniCPM runbook | 성공 |
| 4 | “MiniCPM 말고도 모든 것 전부” 동결 범위 확장 | MiniCPM뿐 아니라 LLaVA-OneVision, InternVL, Qwen 32B/AWQ, Story 2.9/2.10, Epic 3/4/5 등 동결 명시 | 성공 |
| 5 | Story 2.8 리뷰 마감 착수 | `bmad-code-review` 사용 | 성공 |
| 6 | 리뷰 대상 확정 | 사용자 승인: `Y` | 성공 |
| 7 | 서브에이전트 리뷰 승인 | 사용자 승인: `Y` | 성공 |
| 8 | 3개 리뷰 관점 실행 | Blind Hunter, Edge Case Hunter, Acceptance 리뷰 서브에이전트 사용 | 성공 |
| 9 | 리뷰 결과 triage | 주요 패치 항목 5개 선정, 일부 항목 dismiss | 성공 |
| 10 | 패치 적용 여부 확인 | 사용자 선택: `1` = 모든 패치 적용 | 성공 |
| 11 | Story 2.8 코드 패치 | `apply_patch`로 `candidate_harness.py`, `tests/test_candidate_harness.py`, Story 문서, sprint 상태 수정 | 성공 |
| 12 | 집중 테스트 실행 | `PYTHONDONTWRITEBYTECODE=1 UV_CACHE_DIR=/tmp/uv-cache-story28 uv run pytest tests/test_candidate_harness.py -q -p no:cacheprovider` | 성공: 27 passed |
| 13 | 전체 테스트 실행 | `PYTHONDONTWRITEBYTECODE=1 UV_CACHE_DIR=/tmp/uv-cache-story28 uv run pytest -q -p no:cacheprovider` | 성공: 415 passed |
| 14 | Ruff check 실행 | `uv run ruff check src tests` | 성공 |
| 15 | Ruff format check 실행 | `uv run ruff format --check src tests` | 성공 |
| 16 | CLI help 확인 | `uv run multimodal-bias --help` | 성공 |
| 17 | CLI version 확인 | `uv run multimodal-bias --version` | 성공: `multimodal-bias 0.1.0` |
| 18 | Story 2.8 최종 상태 변경 | `sprint-status.yaml`, Story 문서 상태를 `done`으로 변경 | 성공 |

## 성공한 내용

- Story 2.8 리뷰가 완료되었다.
- Story 2.8 상태가 `review`에서 `done`으로 변경되었다.
- 리뷰에서 도출된 5개 주요 보완 항목이 모두 패치되었다.
- 후보 eligibility 및 adapter smoke harness 관련 방어 로직이 강화되었다.
- focused candidate harness 테스트가 `27 passed`로 통과했다.
- 전체 테스트가 `415 passed`로 통과했다.
- Ruff check 및 format check가 통과했다.
- CLI help/version 검증이 통과했다.
- 현재 활성 작업 범위가 Qwen/Qwen2.5-VL-7B-Instruct Reasoner v3 재제출 경로로 제한되었다.
- Story 2.9, Story 2.10, Epic 3/4/5, 비Qwen 후보 모델 작업이 동결 대상으로 문서화되었다.

## 실패하거나 중단된 내용

- GPU 제출물 생성 단계까지는 진행하지 않았다.
- Story 2.9, Story 2.10, Epic 3/4/5는 진행하지 않았다.
- MiniCPM-V 4.5, LLaVA-OneVision, InternVL, Qwen 32B/AWQ 등 비현재 후보 모델 작업은 중단·동결되었다.
- Git repository 상태 확인에서 현재 워크스페이스가 Git repo가 아닌 것으로 확인되었다. 정확한 명령 출력은 확인되지 않음.
- 새 GitHub 정리용 파일은 이 요청 이전에는 생성하지 않았다.

## 발생한 오류와 원인

오류 메시지가 있는 경우 핵심 부분을 포함하고, 확인된 원인과 추정 원인을 구분했다.

| 오류 또는 문제 | 확인된 원인 | 추정 원인 |
| ------ | ------ | ------ |
| `git rev-parse` 실패 | 현재 워크스페이스가 Git repository가 아님 | 해당 없음 |
| Story 2.8 리뷰에서 dummy adapter가 통과 가능하다는 문제 발견 | harness가 adapter/config identity를 충분히 fail-closed로 검증하지 않았음 | 해당 없음 |
| snapshot/commit mismatch가 실행 차단으로 이어지지 않는 문제 발견 | manifest와 model config identity 검증이 부족했음 | 해당 없음 |
| 네트워크 가능 config가 차단되지 않는 문제 발견 | `local_files_only` 같은 오프라인 강제 조건 검증이 부족했음 | 해당 없음 |
| real image smoke가 실제 decodable image를 충분히 보장하지 않는 문제 발견 | PNG/JPEG 등 이미지 구조 검증이 부족했음 | 해당 없음 |
| GPU 이름 substring 기반 검증 문제 발견 | RTX A6000 exact match가 아니라 느슨한 문자열 판정 가능성이 있었음 | 해당 없음 |
| peak VRAM telemetry 누락 가능성 발견 | `peak_vram_mib` 필수 검증이 부족했음 | 해당 없음 |
| report publication 실패가 안정적인 rejection code로 정리되지 않는 문제 발견 | report write/link 실패 처리 경로가 충분히 명확하지 않았음 | 해당 없음 |

## 결정사항

- 현재 활성 범위는 Qwen/Qwen2.5-VL-7B-Instruct 기반 Reasoner v3 즉시 재제출 경로로 제한한다.
- Story 2.8 리뷰 마감까지만 수행한다.
- Story 2.9, Story 2.10, Epic 3/4/5는 미래 작업으로 동결한다.
- MiniCPM-V 4.5뿐 아니라 LLaVA-OneVision, InternVL, Qwen 32B/AWQ 등 모든 비현재 후보 경로도 동결한다.
- 동결 범위의 코드, config, adapter, dependency, model snapshot, runbook, prompt, tests, artifacts는 생성·검증·구현·리뷰·수정·다운로드·로드·벤치마크·삭제하지 않는다.
- 동결 해제는 사용자가 정확한 story/epic/model/file을 명시적으로 지정할 때만 가능하다.
- Story 2.8 리뷰에서 나온 5개 주요 패치를 모두 적용한다.
- Story 2.8 최종 상태는 `done`이다.
- GPU 제출물 생성은 아직 진행하지 않는다.

## 변경된 파일

| 파일 경로 | 변경 유형 | 변경 내용 | 현재 상태 |
| ----- | ----------------- | ----- | ---------- |
| `/Applications/학교 외부/멀티모달 AI Bias/AGENTS.md` | 생성 또는 수정 | Human-Owned Current Execution Lock 추가. Qwen v3 경로만 활성 범위로 지정하고 나머지 범위 동결 명시 | 완료 |
| `/Applications/학교 외부/멀티모달 AI Bias/README.md` | 수정 | 현재 실행 lock 요약 추가 | 완료 |
| `/Applications/학교 외부/멀티모달 AI Bias/spec-epic-2-reasoner-mapping-and-raw-audit.md` | 수정 | `CURRENT EXECUTION LOCK — HUMAN OWNED` 섹션 추가 | 완료 |
| `/Applications/학교 외부/멀티모달 AI Bias/docs/history/epics.md` | 수정 | Story 2.9/2.10 및 Epic 3/4/5를 `[FROZEN — FUTURE ONLY]`로 표시. Story 2.8 이후 STOP 명시 | 완료 |
| `/Applications/학교 외부/멀티모달 AI Bias/sprint-status.yaml` | 수정 | Story 2.8 상태를 `done`으로 변경. Story 2.9/2.10 및 Epic 3/4/5 동결 주석 유지 | 완료 |
| `/Applications/학교 외부/멀티모달 AI Bias/docs/history/first-submission-minicpm-v-4-5-runbook-2026-06-19.md` | 수정 | archived/frozen 배너 추가 | 완료 |
| `/Applications/학교 외부/멀티모달 AI Bias/src/multimodal_bias/candidate_harness.py` | 수정 | fail-closed 검증, manifest evidence 검증, decodable image 검증, exact GPU/VRAM gate, report write error handling 추가 | 완료 |
| `/Applications/학교 외부/멀티모달 AI Bias/tests/test_candidate_harness.py` | 수정 | Story 2.8 리뷰 패치에 대한 테스트 추가·수정 | 완료 |
| `/Applications/학교 외부/멀티모달 AI Bias/docs/history/stories/2-8-build-candidate-eligibility-and-adapter-smoke-harness.md` | 수정 | 리뷰 findings 체크 완료, completion notes 및 changelog 추가, 상태 `done` 변경 | 완료 |
| `/Applications/학교 외부/멀티모달 AI Bias/conversation-001-story-2-8-review-summary.md` | 생성 | 이 대화의 GitHub 프로젝트 정리용 Markdown 문서 생성 | 완료 |

## 현재 상태

완료

Story 2.8 리뷰 마감은 완료되었다. 코드 패치, 테스트, lint/format, CLI 확인까지 통과했고 Story 상태도 `done`으로 정리되었다. 단, 전체 프로젝트 기준으로 GPU 제출물 생성 단계는 아직 완료되지 않았다.

## 미해결 사항

- GPU 제출물 생성은 아직 진행되지 않았다.
- Qwen v3 실제 RunPod 실행, 8,500-row inference, submission CSV 생성·검증은 아직 완료되지 않았다.
- Qwen 후보 manifest/config가 Story 2.8의 강화된 검증 조건을 모두 만족하는지는 확인되지 않음.
- Qwen config의 snapshot hash나 trust_remote_code evidence가 실제 실행 가능한 상태인지 확인되지 않음.
- `sprint-status.yaml`의 `last_updated` 시간이 실제 최신 시간과 일치하는지는 확인 필요.
- Git repository가 아닌 워크스페이스 상태에서 GitHub 프로젝트 정리를 어떻게 반영할지는 확인되지 않음.

## 다음 작업

1. Qwen/Qwen2.5-VL-7B-Instruct Reasoner v3 재제출 경로에 필요한 manifest/config 상태를 확인한다.
2. Story 2.8의 강화된 candidate smoke 조건을 Qwen active path 기준으로 만족시키는지 점검한다.
3. RunPod에서 Qwen v3 real-image smoke, small v2/v3 A/B, throughput/runtime 확인을 진행한다.
4. 문제가 없으면 8,500-row inference를 실행한다.
5. submission CSV 생성 및 검증을 수행한다.
6. 동결 범위인 Story 2.9/2.10, Epic 3/4/5, 비Qwen 후보 모델은 사용자가 명시적으로 해제하기 전까지 건드리지 않는다.

## 다른 대화와 공유할 정보

- 현재 활성 범위는 Qwen/Qwen2.5-VL-7B-Instruct Reasoner v3 즉시 재제출 경로뿐이다.
- Story 2.8은 `done`이다.
- Story 2.9, Story 2.10, Epic 3/4/5는 동결 상태다.
- MiniCPM-V 4.5뿐 아니라 LLaVA-OneVision, InternVL, Qwen 32B/AWQ 등 모든 비현재 후보 경로도 동결 상태다.
- 동결 범위 파일은 생성·수정·검증·실행·삭제하지 않는다.
- Story 2.8 이후 candidate harness는 더 엄격하다:
  - dummy adapter 차단
  - remote/network-enabled config 차단
  - snapshot/commit mismatch 차단
  - trust_remote_code 사용 시 custom code hash evidence 요구
  - 실제 decodable image 요구
  - exact RTX A6000 및 peak VRAM telemetry 요구
  - report write 실패를 안정적 rejection code로 처리
- 최종 검증 결과:
  - focused candidate harness: `27 passed`
  - full tests: `415 passed`
  - Ruff check: 통과
  - Ruff format check: 통과
  - CLI help/version: 통과
- 워크스페이스는 Git repository가 아닌 것으로 확인되었다. 정확한 오류 출력은 확인되지 않음.

## 근거 및 신뢰도

- 대화에서 직접 확인된 내용:
  - 사용자 요청: Story 2.8 리뷰 마감
  - 사용자 승인: `Y`, `Y`, `1`
  - Story 2.8 최종 상태: `done`
  - focused test 결과: `27 passed`
  - full test 결과: `415 passed`
  - Ruff 및 CLI 검증 통과
  - 동결 범위 문서화
  - 실제 수정된 파일 목록

- 대화 내용을 바탕으로 한 해석:
  - 이 대화의 실질적 목적은 “BMad 절차 소비를 멈추고, 실제 Qwen v3 제출 경로로 넘어가기 위한 Story 2.8 종료”로 해석된다.
  - Story 2.8 완료 후 다음 실무 작업은 Qwen v3 RunPod 실행 준비로 해석된다.

- 확인되지 않은 내용:
  - GitHub에 실제 commit/push가 되었는지 여부
  - RunPod에서 실제 GPU 작업이 실행되었는지 여부
  - Qwen manifest/config가 현재 강화된 harness 조건을 모두 만족하는지 여부
  - 제출 CSV가 생성되었는지 여부
  - leaderboard 제출 여부
  - 정확한 `git rev-parse` 오류 메시지
