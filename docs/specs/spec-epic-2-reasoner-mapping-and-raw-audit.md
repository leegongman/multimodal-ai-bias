---
title: 'Epic 2 Reasoner 선택지 매핑 및 raw 감사 강화'
type: 'bugfix'
created: '2026-06-19'
status: 'done'
baseline_commit: 'NO_VCS'
context:
  - 'docs/history/epics.md'
  - 'docs/history/stories/2-2-build-evidence-grounded-reasoner-prompts.md'
  - 'docs/history/stories/2-4-run-reasoner-inference-and-preserve-raw-outputs.md'
  - 'experiments/investigations/submission-score-091-investigation.md'
---

## CURRENT EXECUTION LOCK — HUMAN OWNED

현재 허용된 범위는 **Qwen2.5-VL-7B Reasoner v3 조기 재제출 경로**뿐이다. Story 2.9·2.10, Epic 3·4·5 전체, MiniCPM/LLaVA/InternVL/Qwen 32B 등 다른 모든 모델과 관련 코드·설정·의존성·스냅샷·실행은 사용자가 대상을 명시적으로 해제하기 전까지 수정하거나 실행하지 않는다. 전체 회귀 테스트가 기존 파일을 읽거나 실행하는 것은 허용하지만, 실패를 이유로 동결 범위를 수정해서는 안 된다. 상세 규칙은 [`AGENTS.md`](AGENTS.md)를 따른다.

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `reasoner_v1`은 불확실성 선택지를 항상 label `2`로 간주하지만 Multimodal label은 현재 선택지 배열의 0-based 인덱스다. 기존 raw artifact는 실제 요청 프롬프트와 이미지 바이트 식별자를 저장하지 않고 정상 종료 전에는 숨은 임시파일만 유지해, RunPod 장애 후 원인 검증이 불가능하다.

**Approach:** 기존 v1을 재현용으로 보존하고 인덱스 의미를 명시한 v2를 기본 프롬프트로 추가한다. Reasoner 실행기는 논리 요청 프롬프트와 이미지 해시/크기/형식을 행별로 기록하고, 명시적인 partial JSONL을 주기적으로 동기화한 뒤 정상 완료 시에만 최종 raw artifact로 승격한다.

## Boundaries & Constraints

**Always:** 선택지 원문 순서와 label 인덱스를 그대로 보존한다. 최종 label은 모델 생성 텍스트에서만 파싱한다. raw 행은 UTF-8이며 샘플 순서와 실패 행을 유지한다. 기존 v1은 A/B 재현을 위해 변경하지 않는다.

**Ask First:** 새 모델 엔진 도입, vLLM adapter 구현, 외부 스토리지 업로드, 재시작/resume 기능 추가.

**Never:** 에픽 3 verifier/arbitration 파일 수정, 테스트 데이터 기반 정답 규칙 추가, unknown 문구 regex로 label 결정, 이미지가 전달되지 않았는데 성공으로 기록, partial artifact를 완전한 최종 산출물로 취급.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 불확실성 선택지가 index 0/1/2 | 3개 선택지 | v2는 의미상 불확실한 선택지의 실제 인덱스를 출력하도록 지시 | 특정 인덱스를 불확실성으로 고정하지 않음 |
| 정상 생성 | prompt + loaded image bytes | raw 행에 prompt text/hash, image hash/byte count/format, output/metadata 기록 | partial을 flush하고 최종 완료 때 승격 |
| 샘플 실패 | image/prompt/inference 실패 | 동일 sample_id 실패 행 기록 | 가능한 감사 필드는 유지하고 output은 null |
| 비정상 실행 중단 | 일부 행 작성 후 예외/Pod 종료 | `raw_reasoner.partial.jsonl` 유지 | 최종 `raw_reasoner.jsonl`은 생성하지 않음 |

</frozen-after-approval>

## Code Map

- `configs/prompts/reasoner_v1.yaml` -- 결함 재현용 기존 프롬프트.
- `configs/prompts/reasoner_v2.yaml` -- 수정된 기본 프롬프트.
- `src/multimodal_bias/prompting/templates.py` -- 기본 프롬프트 선택과 선택지 표시.
- `src/multimodal_bias/schemas.py` -- raw request 감사 필드 계약.
- `src/multimodal_bias/reasoner.py` -- 요청 구성, 행별 로깅, partial checkpoint/승격.
- `src/multimodal_bias/cli.py` -- 실행 시작 시 run/partial 위치 노출.
- `tests/test_prompting.py`, `tests/test_reasoner.py`, `tests/test_cli.py` -- CPU 회귀 검증.

## Tasks & Acceptance

**Execution:**
- [x] `configs/prompts/reasoner_v2.yaml`, `src/multimodal_bias/prompting/templates.py` -- label을 선택지 인덱스로 정의하고 v2를 기본값으로 설정한다.
- [x] `src/multimodal_bias/schemas.py`, `src/multimodal_bias/reasoner.py` -- prompt/image 감사 필드와 내구성 있는 partial JSONL을 구현한다.
- [x] `src/multimodal_bias/cli.py` -- 실행 시작 시 run ID, run directory, partial path를 출력한다.
- [x] `tests/test_prompting.py`, `tests/test_reasoner.py`, `tests/test_cli.py` -- 매핑, 감사 필드, 성공/실패/중단 artifact 수명을 검증한다.

**Acceptance Criteria:**
- Given 불확실성 선택지가 어느 인덱스에 있든, when v2 프롬프트를 구성하면, then label은 표시된 선택지 인덱스이며 `2`는 특별 의미가 없다고 명시된다.
- Given 생성 요청이 모델 adapter에 전달될 때, when raw 행을 기록하면, then exact prompt와 prompt/image SHA-256, image byte count/format이 감사 가능하다.
- Given 실행이 중단될 때, when 일부 샘플이 완료됐다면, then durable partial 행은 남고 완전한 최종 raw 파일은 존재하지 않는다.
- Given 정상 완료될 때, when 최종 raw 파일이 승격되면, then partial은 사라지고 기존 parser가 최종 파일을 처리한다.
- Given 변경 완료 후, when 전체 CPU test와 Ruff를 실행하면, then 에픽 1·2 회귀가 없고 에픽 3 소스는 수정되지 않는다.

## Spec Change Log

## Design Notes

`raw_reasoner.partial.jsonl`은 복구 가능한 불완전 artifact다. 매 행 flush, 일정 간격 fsync, 정상 완료 시 atomic replace를 사용한다. RunPod 자체 삭제까지 견디려면 run directory가 persistent volume에 있어야 하며 이는 코드 외 운영 전제다.

## Verification

**Commands:**
- `./.venv/bin/pytest tests/test_prompting.py tests/test_reasoner.py tests/test_cli.py -q` -- 대상 회귀 통과.
- `./.venv/bin/pytest -q` -- 전체 CPU suite 통과.
- `./.venv/bin/ruff check src tests` -- lint 통과.
- `./.venv/bin/ruff format --check src tests` -- format 통과.

## Suggested Review Order

**선택지 매핑 계약**

- 결함을 직접 제거하는 mapping-only v2 프롬프트부터 확인한다.
  [`reasoner_v2.yaml:6`](configs/prompts/reasoner_v2.yaml#L6)

- 기본 실행이 v2를 선택하되 v1은 A/B용으로 보존한다.
  [`templates.py:36`](src/multimodal_bias/prompting/templates.py#L36)

**요청 감사와 중단 복구**

- 행별 partial checkpoint와 정상 완료 승격이 핵심 실행 경계다.
  [`reasoner.py:75`](src/multimodal_bias/reasoner.py#L75)

- prompt/image 식별자가 raw artifact의 정식 계약이 된다.
  [`schemas.py:427`](src/multimodal_bias/schemas.py#L427)

- 시작 즉시 partial artifact 위치를 운영자에게 노출한다.
  [`cli.py:138`](src/multimodal_bias/cli.py#L138)

**검증과 운영 인계**

- uncertainty 위치 0/1/2를 모두 검사해 고정 label 회귀를 막는다.
  [`test_prompting.py:189`](tests/test_prompting.py#L189)

- 성공·실패·비정상 중단 artifact 수명을 검증한다.
  [`test_reasoner.py:166`](tests/test_reasoner.py#L166)

- 원인 등급과 최소 RunPod A/B 순서를 확인한다.
  [`submission-score-091-investigation.md:108`](experiments/investigations/submission-score-091-investigation.md#L108)

- persistent volume과 새 runtime bundle 절차를 확인한다.
  [`runpod-qwen2-5-vl-7b-reproduction-2026-06-19.md:16`](docs/history/runpod-qwen2-5-vl-7b-reproduction-2026-06-19.md#L16)
