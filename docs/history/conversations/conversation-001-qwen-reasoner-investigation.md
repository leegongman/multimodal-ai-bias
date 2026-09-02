# 대화 001 - Qwen2.5-VL-7B Reasoner 점수 0.91 원인 조사 및 Epic 2 수정

## 목적

Epic 3은 건드리지 않고, Epic 1·2 범위에서 Qwen2.5-VL-7B Reasoner 단독 제출 점수 0.91의 원인을 조사하고, 확인된 원인에 따라 Epic 2의 프롬프트·실행기·로깅만 수정하는 것이 목표였다.

## 핵심 요약

Qwen2.5-VL-7B Reasoner 단독 제출 점수 0.91의 주요 원인 후보로 `reasoner_v1` 프롬프트의 label 2 의미 오염이 확인되었다. Multimodal 제출 label은 단순히 선택지 인덱스 0/1/2인데, 기존 프롬프트는 label 2를 “불확실/객관적으로 답변 불가” 경로로 설명하고 있었다. 선택지 순서와 label 매핑을 보존하는 데이터·프롬프트·파싱·제출 코드는 정상으로 확인되었다. 실제 실행 경로는 vLLM이 아니라 Transformers 기반 `hf_local` 경로였다. RunPod 원본 raw output은 보존되지 않았고, ephemeral 환경 삭제로 인해 사후 복원은 불가능한 상태로 정리되었다. 이에 따라 `reasoner_v2`를 추가하고 기본 프롬프트를 v2로 변경했으며, raw output에 prompt/image hash와 원문 prompt를 남기도록 로깅을 강화했다. Epic 3 verifier/arbitration 파일은 수정하지 않았다. 로컬 검증은 pytest 370개 통과, Ruff lint/format 통과로 완료되었다.

## 시도한 작업

시간 순서대로 정리한다.

| 순서 | 시도한 내용 | 사용한 방법·명령어 | 결과 |
| -- | ------ | ---------- | --------------- |
| 1 | 사용자가 지정한 조사 플로우 확인 | `bmad-investigate` 스킬 사용 지시 확인 | 성공 |
| 2 | `_bmad` / `_bamd` 관련 혼선 확인 | 대화상 사용자 지적 확인. `_bamd`는 오타, `_bmad`는 전역/프로젝트 맥락에서 확인됨 | 부분 성공 |
| 3 | 기존 조사 산출물 확인 | `experiments/investigations/submission-score-091-investigation.md` 확인 | 성공 |
| 4 | Multimodal label 의미 확인 | 평가 요구사항 문서 확인. label은 선택지 인덱스 0/1/2, 평가지표는 Balanced Accuracy로 확인 | 성공 |
| 5 | 선택지 순서와 label 매핑 검증 | `data_loader.py`, `templates.py`, `parsing.py`, `submission.py` 코드 흐름 확인 | 성공 |
| 6 | `reasoner_v1` 프롬프트 점검 | `configs/prompts/reasoner_v1.yaml` 확인 | 성공 |
| 7 | label 2 과다 선택 여부 확인 | 제출 분포 `0:2661`, `1:2649`, `2:3190` 확인 | 부분 성공 |
| 8 | 이미지 전달 경로 확인 | 이미지 파일 수, JPEG header, data validation, HF adapter 경로 확인 | 성공 |
| 9 | vLLM 실행 경로 확인 | 모델 config와 adapter registry 확인 | 성공. 실제 경로는 vLLM이 아니라 `hf_local` |
| 10 | Qwen 7B 자체 성능 한계 분리 계획 수립 | A/B 실험표 A0~A6 작성 | 성공 |
| 11 | raw output 보존 방법 확정 | `raw_reasoner.partial.jsonl`, flush/fsync, 최종 rename 방식 결정 | 성공 |
| 12 | Epic 2 수정 실행 | `bmad-quick-dev` 범위로 프롬프트·실행기·로깅 수정 | 성공 |
| 13 | 사용자 제공 `reasoner_v2` 초안 검토 | 참고만 하고, label 2를 다시 특별 취급하는 문구는 채택하지 않음 | 성공 |
| 14 | 새 프롬프트 추가 | `configs/prompts/reasoner_v2.yaml` 생성 | 성공 |
| 15 | 기본 프롬프트 변경 | `src/multimodal_bias/prompting/templates.py` 수정 | 성공 |
| 16 | raw logging schema 확장 | `src/multimodal_bias/schemas.py` 수정 | 성공 |
| 17 | reasoner 실행기 로깅 강화 | `src/multimodal_bias/reasoner.py` 수정 | 성공 |
| 18 | CLI 출력 개선 | `src/multimodal_bias/cli.py` 수정 | 성공 |
| 19 | 테스트 업데이트 | `tests/test_prompting.py`, `tests/test_reasoner.py`, `tests/test_cli.py` 수정 | 성공 |
| 20 | 로컬 테스트 실행 | `env PYTHONDONTWRITEBYTECODE=1 PATH=".../.venv/bin:$PATH" ./.venv/bin/pytest -q` | 성공, `370 passed` |
| 21 | Ruff lint 실행 | `./.venv/bin/ruff check src tests` | 성공 |
| 22 | Ruff format check 실행 | `./.venv/bin/ruff format --check src tests` | 성공 |
| 23 | Runtime zip 생성 | `multimodal-bias-runtime-qwen-reasoner-v2-20260619.zip` 생성 | 성공 |
| 24 | Runtime zip 검증 | `unzip -t` 실행 | 성공 |
| 25 | 현재 산출물 존재 여부 재확인 | `pwd`, `rg --files | rg ...` | 성공 |
| 26 | Git 상태 확인 | `git status --short` | 실패, 현재 디렉터리가 Git 저장소가 아님 |

## 성공한 내용

실제로 완료되었거나 정상적으로 동작한 작업은 다음과 같다.

- 0.91 원인 조사 보고서가 작성·정리되었다.
- 핵심 원인 후보로 `reasoner_v1`의 label 2 의미 오염이 확인되었다.
- 선택지 순서와 label 0/1/2 매핑은 데이터 로딩부터 제출 CSV 작성까지 보존되는 것으로 확인되었다.
- 실제 실행 경로는 vLLM이 아니라 Transformers 기반 `hf_local`임이 확인되었다.
- 이미지 파일과 전달 경로는 로컬 기준 정상으로 확인되었다.
- `reasoner_v2`가 생성되었고 기본 reasoner prompt로 지정되었다.
- raw output 보존을 위해 partial JSONL, prompt/image hash, image byte count, image format, prompt text 기록이 추가되었다.
- CLI가 실행 시작 시 `run_id`, `run_dir`, `partial_raw_reasoner_path`를 출력하도록 수정되었다.
- pytest 전체 테스트 370개가 통과했다.
- Ruff lint와 format check가 통과했다.
- RunPod용 새 runtime zip이 생성되었다.

## 실패하거나 중단된 내용

실패한 시도, 중단된 작업, 해결하지 못한 문제는 다음과 같다.

- 기존 RunPod production raw output은 복구하지 못했다.
- raw output이 없어서 실제 0.91 제출의 per-sample reasoning, raw model output, label 2 선택 근거는 확인하지 못했다.
- vLLM 요청 프롬프트는 재구성하지 못했다. 이유는 실제 실행 경로가 vLLM이 아니었기 때문이다.
- Qwen 7B 자체 성능 한계는 로컬 조사만으로 확정하지 못했고, 다음 RunPod A/B 실험으로 분리하기로 했다.
- Epic 3 verifier/arbitration 쪽 label 2 가정은 수정하지 않았다.
- Git commit은 생성하지 않았다. 현재 작업 디렉터리가 Git 저장소가 아니었다.

## 발생한 오류와 원인

오류 메시지가 있다면 핵심 부분을 포함하고, 확인된 원인과 추정 원인을 구분해 정리한다.

| 오류 또는 문제 | 핵심 메시지 | 확인된 원인 | 추정 원인 |
| --- | --- | --- | --- |
| `_bmad` / `_bamd` 혼선 | 사용자가 “_bamd랑 아웃풋 어디갔어?”라고 지적 | `_bamd`는 오타 맥락이고, `_bmad`는 전역/프로젝트 맥락에서 사용 가능했음 | 초기 컨텍스트에서 로컬 `_bmad` 부재를 과도하게 blocker로 판단했을 가능성 |
| 기존 raw output 부재 | raw output 확인 불가 | RunPod ephemeral 환경 삭제로 production raw output이 남아 있지 않음 | persistent volume 미사용 또는 산출물 다운로드 누락 |
| `uv` 실행 실패 | `/Users/gongman/.cache/uv` 접근 `Operation not permitted` | sandbox 권한 문제 | 사용자 홈 캐시 접근 제한 |
| vLLM 경로 불일치 | vLLM adapter 없음 | 실제 모델 config는 `hf_local`, 실행은 Transformers `model.generate` 경로 | 문서/계획상 vLLM 언급이 실제 구현과 혼재했을 가능성 |
| `git status --short` 실패 | `fatal: not a git repository (or any of the parent directories): .git` | 현재 디렉터리가 Git 저장소가 아님 | 해당 없음 |

## 결정사항

이 대화에서 확정된 기술적·기획적 선택사항은 다음과 같다.

- Epic 3은 수정하지 않는다.
- 수정 범위는 Epic 2의 프롬프트·실행기·로깅으로 제한한다.
- `reasoner_v1`은 A/B baseline 재현용으로 유지한다.
- 기본 reasoner prompt는 `reasoner_v2`로 전환한다.
- `reasoner_v2`는 mapping-only 성격으로 유지한다.
- label 2는 더 이상 “불확실성 전용 label”로 취급하지 않는다.
- 불확실성은 선택지 내용으로 판단해야 하며, 해당 선택지가 어느 index에 있든 그 index를 출력해야 한다.
- 사용자 제공 `reasoner_v2` 초안은 참고만 하고, label 2를 다시 특별 취급하는 부분은 채택하지 않는다.
- raw output은 `raw_reasoner.partial.jsonl`에 row 단위 flush/fsync 후 최종 `raw_reasoner.jsonl`로 rename한다.
- 다음 RunPod 실행은 persistent/network volume에 run directory를 두어야 한다.
- 다음 검증은 A0~A6 최소 A/B 실험표에 따라 수행한다.
- 현재 runtime은 vLLM이 아니라 HF Transformers 경로로 기록한다.

## 변경된 파일

| 파일 경로 | 변경 유형 | 변경 내용 | 현재 상태 |
| ----- | ----------------- | ----- | ---------- |
| `configs/prompts/reasoner_v2.yaml` | 생성 | label mapping-only 수정 prompt 추가 | 완료 |
| `src/multimodal_bias/prompting/templates.py` | 수정 | 기본 reasoner prompt를 `reasoner_v2.yaml`로 변경 | 완료 |
| `src/multimodal_bias/schemas.py` | 수정 | `RawReasonerRecord`에 prompt/image audit 필드 추가 | 완료 |
| `src/multimodal_bias/reasoner.py` | 수정 | partial raw JSONL, flush/fsync, prompt/image hash 기록 추가 | 완료 |
| `src/multimodal_bias/cli.py` | 수정 | 실행 시작 시 run 정보와 partial raw path 출력 | 완료 |
| `tests/test_prompting.py` | 수정 | 기본 prompt v2 검증, v1 baseline 로드 검증, uncertainty choice index별 매핑 테스트 추가 | 완료 |
| `tests/test_reasoner.py` | 수정 | raw audit 필드, sha256, partial 파일 동작 테스트 추가 | 완료 |
| `tests/test_cli.py` | 수정 | CLI 시작 출력과 partial 파일 제거 검증 추가 | 완료 |
| `experiments/investigations/submission-score-091-investigation.md` | 수정 | 원인 조사 결과, A/B 실험표, raw 보존 계약 정리 | 완료 |
| `docs/history/runpod-qwen2-5-vl-7b-reproduction-2026-06-19.md` | 수정 | RunPod 재현 계획을 reasoner_v2, HF local, persistent volume 기준으로 업데이트 | 완료 |
| `spec-epic-2-reasoner-mapping-and-raw-audit.md` | 생성 | Quick Dev 작업 스펙 및 검증 기록 작성, status done | 완료 |
| `multimodal-bias-runtime-qwen-reasoner-v2-20260619.zip` | 생성 | RunPod용 reasoner_v2 runtime bundle 생성 | 완료 |
| 확인되지 않음, `__pycache__` / `*.pyc` 관련 | 삭제 | Python cache 제거가 언급됨. 최종 검색 결과는 비어 있었음 | 확인 필요 |

## 현재 상태

부분 완료.

로컬 조사, Epic 2 수정, 테스트, runtime zip 생성까지는 완료되었다. 다만 RunPod에서 새 A/B 실험과 실제 제출 검증은 아직 실행되지 않았다. 기존 0.91 제출의 raw output이 없기 때문에 원인 중 일부는 강한 근거가 있지만 per-sample 단위로 완전히 복원되지는 않았다.

## 미해결 사항

아직 답을 찾지 못했거나 추가 확인이 필요한 문제는 다음과 같다.

- 새 `reasoner_v2`가 실제 Multimodal 점수를 개선하는지 RunPod에서 아직 확인되지 않았다.
- Qwen2.5-VL-7B 자체 성능 한계는 아직 실험으로 분리되지 않았다.
- 이미지 전처리의 processor 내부 resize/pixel budget 영향은 아직 완전히 분리되지 않았다.
- vLLM과 HF `model.generate` 간 차이는 아직 A/B로 검증되지 않았다.
- Epic 3 verifier/arbitration에는 label 2를 uncertainty로 보는 기존 가정이 남아 있을 수 있다.
- 기존 production raw output은 복구 불가 상태다.
- 현재 디렉터리가 Git 저장소가 아니어서 commit, branch, PR 상태는 해당 없음 또는 확인되지 않음이다.

## 다음 작업

우선순위 순서대로 작성한다.

1. RunPod에서 `multimodal-bias-runtime-qwen-reasoner-v2-20260619.zip`를 persistent/network volume 기준으로 실행한다.
2. A0~A6 최소 A/B 실험표에 따라 `reasoner_v1` baseline, `reasoner_v2`, 이미지 omission, pixel budget, HF/vLLM, larger VLM, decisiveness variant를 순서대로 비교한다.
3. 각 실행 후 `raw_reasoner.jsonl`, `raw_reasoner.partial.jsonl`, submission CSV, label distribution, failure count, sha256sum을 반드시 보존한다.
4. `reasoner_v2` 결과가 개선되면 해당 prompt/logging 경로를 Epic 2 기준으로 확정한다.
5. Epic 3을 다시 사용할 시점에는 verifier/arbitration의 label 2 uncertainty 가정을 별도 이슈로 수정한다.

## 다른 대화와 공유할 정보

다른 대화에서 참고해야 하는 파일, 결정사항, 오류, 실행 결과 또는 주의사항은 다음과 같다.

- 핵심 조사 보고서: `experiments/investigations/submission-score-091-investigation.md`
- RunPod 실행 계획: `docs/history/runpod-qwen2-5-vl-7b-reproduction-2026-06-19.md`
- Quick Dev 스펙: `spec-epic-2-reasoner-mapping-and-raw-audit.md`
- 새 runtime zip: `multimodal-bias-runtime-qwen-reasoner-v2-20260619.zip`
- 새 runtime zip SHA-256: `f52fa29214b8e3c3612402d162950218e8704f0a229f9b57f9a1f3f4c15b75cf`
- 기존 runtime zip도 남아 있음: `multimodal-bias-runtime-qwen-20260619.zip`
- 실제 실행 경로는 vLLM이 아니라 HF Transformers `hf_local`.
- `reasoner_v1`은 label 2를 uncertainty로 설명하는 문제가 있다.
- `reasoner_v2`는 label 2의 특별 의미를 제거하고, 선택지 index mapping을 보존하는 방향이다.
- Epic 3은 수정하지 않았고, 다시 사용할 때 별도 수정이 필요하다.
- 현재 디렉터리는 Git 저장소가 아니므로 commit/PR 관련 상태는 확인되지 않음이다.

## 근거 및 신뢰도

- 대화에서 직접 확인된 내용:
  - 사용자는 Epic 3 제외, Epic 1·2 원인 조사, Epic 2 prompt/executor/logging 수정만 요청했다.
  - `bmad-investigate`, `bmad-quick-dev` 사용이 요청되었다.
  - `reasoner_v1`의 label 2 uncertainty 오염이 확인되었다.
  - 실제 실행 경로는 vLLM이 아니라 `hf_local`이었다.
  - production raw output은 남아 있지 않았다.
  - pytest `370 passed`, Ruff lint/format 통과가 보고되었다.
  - 새 runtime zip과 SHA-256이 보고되었다.
  - 현재 확인에서 주요 산출물 파일들이 존재했다.
  - 현재 확인에서 `git status --short`는 Git 저장소가 아니라는 오류로 실패했다.
- 대화 내용을 바탕으로 한 해석:
  - 0.91의 가장 강한 원인 후보는 label 2 의미 오염이다.
  - raw output이 없기 때문에 “확정 원인”이라기보다 강한 근거가 있는 원인 후보로 다뤄야 한다.
  - RunPod 재실행 전에는 persistent volume과 raw 보존이 필수다.
  - Epic 3은 범위 밖이지만 향후 사용 시 label 2 가정 문제를 별도 해결해야 한다.
- 확인되지 않은 내용:
  - 기존 0.91 제출의 sample별 raw model output.
  - 기존 RunPod 실행의 sample별 이미지 hash.
  - vLLM runner에서의 실제 성능.
  - Qwen 7B 자체 성능 한계의 정량적 영향.
  - 새 `reasoner_v2`의 실제 Multimodal public/private 점수.
  - Git commit, branch, PR 상태.
