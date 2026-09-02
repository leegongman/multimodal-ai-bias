---
baseline_commit: NO_VCS
created_at: 2026-06-21
---

# Story 4.3: Independently Review, Adjudicate, and Balance Samples

Status: backlog

> **HUMAN-OWNED HOLD (2026-06-21):** 사용자가 사람 검수를 현재 실행 범위에서 제외했다. 600건은 모두 `pending`으로 보존하며 평가, 동결, 모델 비교 또는 promotion 근거로 사용하지 않는다. Story 4.3을 재개하려면 새 명시적 사용자 승인이 필요하다.

## Story

경진평가 개발자로서,
나는 Shadow Private 후보를 작성 파이프라인과 분리된 사람이 블라인드 검수하고 불일치를 재심하며 최종 coverage를 감사하기를 원한다.
그래서 동결 전 label·subset·provenance를 방어할 수 있고 AI가 자기 정답을 승인하는 일을 막을 수 있다.

## Acceptance Criteria

1. 검수 결과는 엄격한 UTF-8 JSONL 계약으로 읽으며, 각 행은 `sample_id`, `reviewer_id`, `independent_label`, `proposed_label`, `decision`, `evidence_basis`, `evidence_note`, `natural_language_ok`, `protected_attribute_shortcut_absent`, `content_safety_ok`를 가진다. 누락·추가 필드, 중복 sample, 범위 밖 label, 빈 근거, 알 수 없는 enum은 전체 적용을 fail-closed로 중단한다.
2. 검수자는 원본 `author_id` 및 생성 파이프라인 ID와 달라야 한다. `proposed_label`은 원본 `expected_label`과 일치해야 하며, UI에서 독립 답과 근거를 제출하기 전 제안 정답을 노출하지 않는다.
3. `reviewed`는 독립 label과 제안 label이 같고 세 품질 체크가 모두 true일 때만 허용한다. ambiguous 정답은 `insufficient_evidence`, resolvable 정답은 `stated_text_fact`, `objective_visual_evidence`, `valid_elimination` 중 하나를 근거 유형으로 요구하며 subset과 근거 유형도 일치해야 한다. 불일치·거짓 체크를 자동 승인하거나 자동 수정하지 않는다.
4. 불일치는 `adjudication_required` 이력으로 보존한다. 재심 입력은 원 작성자와 1차 검수자 모두와 다른 `adjudicator_id`, 명시적 `final_label`, `final_subsets`, 최종 근거 유형·설명 및 `adjudicated|rejected` 결정을 요구한다. label 변경 시 `expected_is_uncertainty`를 명시적으로 재계산하고 전·후 값을 이력에 남긴다.
5. 적용 결과는 새 no-clobber 디렉터리에 base/review/adjudication 입력 SHA-256, `reviewed.jsonl`, `review-history.jsonl`, `disputes.jsonl`, `rejections.jsonl`, `report.json`, 출력 hash manifest를 기록한다. 원본 `pending-v1`, 이미지 pool, 입력 결정 파일을 수정하지 않는다.
6. promotion readiness는 원본 600건 전체에 terminal 검수 결정이 있고 미해결 dispute가 0이며, retained corpus가 300–600건, 필수 8개 subset 각각 30건 이상, uncertainty 위치 0/1/2 각각 30% 이상, ambiguous/resolvable 각각 120건 이상, 독립 검수·이미지 decode/hash·provenance gate를 모두 통과할 때만 true다.
7. rejected/disputed 행은 `reviewed.jsonl`에서 제외하되 원본 내용과 모든 결정을 감사 이력에 보존한다. 기각으로 coverage가 깨지면 부족 subset/position/class를 구체적으로 보고하고, 기존 행을 재분류하거나 새 후보를 자동 생성하지 않는다.
8. 기존 로컬 검수 화면은 정형 근거 유형과 content-safety 체크를 수집하고 canonical decision schema를 내보낸다. 정적 로컬 operator aid로만 유지하며 서버, 네트워크 API, 계정 시스템 또는 범용 labeling product를 만들지 않는다.
9. CPU-safe 테스트는 부분 pilot, 완전 승인, 중복·누락·extra ID, self-review, tampered proposed label, label 불일치 승인, false 품질 체크, 재심자 충돌, explicit label/subset 변경, 기각/coverage 붕괴, hash/no-clobber, 실제 Shadow loader 연동과 CLI exit code를 검증한다.
10. 이 Story는 사람 판단을 생성하거나 대행하지 않으며 Story 4.4 freeze, Story 4.5 metrics, 모델 추론·평가, sealed holdout 실행을 시작하지 않는다. 구현 완료 후 실제 사람 JSONL이 없으면 Story 상태는 `review` 또는 human-gated 상태로 남고 `done`으로 보고하지 않는다.

## Tasks / Subtasks

- [x] 검수·재심 계약을 typed schema로 추가한다. (AC: 1–4)
  - [x] `schemas.py`에 immutable review decision, adjudication decision, history entry, application report/result 타입과 stable enums를 추가한다.
  - [x] canonical 필드 이름을 `configs/validation/review-template.json`과 일치시키고 `adjudication-template.json`을 추가한다.
- [x] 검수 적용 경계를 구현한다. (AC: 1–7)
  - [x] 새 `shadow_review.py`에서 exact-schema JSONL load, ID/author/reviewer binding, decision semantics와 adjudication validation을 구현한다.
  - [x] 기존 `load_shadow_records`, `audit_shadow_records`, canonical JSON/hash/no-clobber 패턴을 재사용한다. 별도 Shadow record parser나 image validator를 만들지 않는다.
  - [x] 원본 순서를 유지해 accepted/adjudicated record만 `reviewed.jsonl`에 쓰고 rejected/disputed/pending은 sidecar history에 남긴다.
  - [x] partial pilot도 보고서는 만들 수 있지만 `promotion_ready=false`와 non-zero CLI 상태를 유지한다.
- [x] 기존 블라인드 검수 화면과 템플릿을 canonical 계약에 맞춘다. (AC: 2, 3, 8)
  - [x] `data/shadow-private/pending-v1/review.html`에 `evidence_basis`, `content_safety_ok`를 추가하고 label 불일치 시 승인 버튼을 비활성화한다.
  - [x] localStorage resume/export를 보존하고 fetch/image 경로 오류를 화면에 명확히 표시한다.
  - [x] HTML에 dataset 행이나 제안 label을 별도로 복제하지 않고 기존 `records.jsonl`을 read-only로 사용한다.
- [x] CLI를 추가한다. (AC: 5–7)
  - [x] `shadow-apply-reviews --dataset --image-root --decisions [--adjudications] --output-dir`를 `cli.py`에 등록한다.
  - [x] 성공 시 counts/hashes/readiness를 출력하고 incomplete/disputed/unbalanced 상태는 evidence bundle 작성 후 exit 1로 종료한다.
  - [x] overwrite, malformed input, self-review, tampering은 완료 디렉터리 없이 종료한다.
- [x] CPU-safe 계약·CLI 테스트를 추가한다. (AC: 1–10)
  - [x] 새 `tests/test_shadow_review.py`에 최소 fixture와 600건 balance fixture를 둔다.
  - [x] 기존 Shadow validation/acquisition/CLI 회귀 테스트와 Ruff를 실행한다.
  - [x] 어떤 테스트도 네트워크, GPU, 1.27GB 실제 이미지 전체 decode를 기본 suite에 요구하지 않는다.
- [ ] 사람 검수 checkpoint를 운영한다. (AC: 6, 7, 10)
  - [ ] 구현 검증 후 사람에게 먼저 30–50건 pilot export를 요청하고 시스템적 문항 결함·기각률을 보고한다.
  - [ ] 사람의 600건 결정과 필요한 재심 파일을 받은 뒤에만 real `review-v1` bundle을 생성한다.
  - [ ] coverage 부족 시 정확한 deficit을 보고하고 중단한다. replacement 생성은 Story 4.2의 별도 재승인 없이는 수행하지 않는다.

## Dev Notes

### 현재 상태와 재사용 경계

- `pending-v1/records.jsonl`은 600행이며 label과 uncertainty position이 각각 200/200/200, split은 selection 420 / sealed holdout 180이다. 현재 audit의 유일한 violation은 reviewed/adjudicated 0건이다.
- `validation.py`의 `load_shadow_records`가 exact field, provenance, author/reviewer separation, Pillow decode, image SHA-256을 이미 검증한다. `audit_shadow_records`가 corpus size/subset/position/class/holdout gate를 이미 계산하므로 이를 호출해야 한다.
- 현재 `review.html` export schema와 `configs/validation/review-template.json`이 서로 다르다. 한쪽을 임의 호환하는 대신 이 Story에서 위 AC의 canonical schema 하나로 통일한다.
- 검수 UI는 보조 수단일 뿐 truth source가 아니다. JSONL loader가 UI보다 강한 검증 경계이며, 사람이 파일을 수정해도 동일 gate를 통과해야 한다.
- VCS가 없는 workspace이므로 commit hash를 만들거나 존재한다고 기록하지 않는다.

### 데이터 적용 규칙

- `decision` enum: `reviewed`, `adjudication_required`, `rejected`.
- `evidence_basis` enum: `insufficient_evidence`, `stated_text_fact`, `objective_visual_evidence`, `valid_elimination`.
- subset/evidence binding: `ambiguous→insufficient_evidence`, `visual_grounded→objective_visual_evidence`, `elimination→valid_elimination`, `disambiguated_text|stereotype_trap|expression_trap|role_or_function→stated_text_fact`, `parsing_stress→stated_text_fact|valid_elimination`.
- 1차 `reviewed`는 label 일치와 모든 품질 flag true가 필수다. `adjudication_required` 또는 `rejected`는 승인 corpus에 들어가지 않는다.
- 재심은 `decision: adjudicated|rejected`, `final_label`, `final_subsets`, 최종 evidence 필드를 요구한다. 자동 다수결, AI 재판정, numeric label 의미 추론은 금지한다.
- output corpus는 기존 `ShadowRecord` schema만 유지한다. review/adjudication 상세는 별도 append-only history JSONL에 둬 Story 4.4 freeze loader를 깨지 않는다.
- 동일한 입력 bytes로 생성되는 JSONL/report/hash payload는 결정론적이어야 한다. 사용자 제공 파일의 순서를 기록하되 reviewed corpus는 base dataset 순서를 보존한다.

### Architecture Compliance

- Python 3.10, 기존 Pillow/Typer/stdlib만 사용하고 새 dependency, DB, web framework, remote service를 추가하지 않는다.
- importable code는 `src/multimodal_bias/`에 둔다. shared dataclass는 `schemas.py`, review orchestration은 새 `shadow_review.py`, CLI glue는 `cli.py`에 둔다.
- UTF-8 JSONL/JSON, no-clobber, `.partial` staging 후 atomic rename 패턴을 따른다.
- `data/raw/open/test`, 제출 예측, model/Public disagreement, leaderboard 또는 evaluation 패턴을 검수 근거로 읽지 않는다.
- Story 4.4가 freeze와 sealed policy를 소유한다. 이 Story의 manifest는 review provenance용이며 frozen dataset version을 선언하지 않는다.

### File Structure Requirements

- UPDATE `src/multimodal_bias/schemas.py`: review/adjudication/result contracts.
- NEW `src/multimodal_bias/shadow_review.py`: strict loaders, merge/history, balance report, atomic publication.
- UPDATE `src/multimodal_bias/cli.py`: `shadow-apply-reviews` command only.
- UPDATE `configs/validation/review-template.json`; NEW `configs/validation/adjudication-template.json`.
- UPDATE `configs/validation/README.md`: blind review, pilot, export/apply and human gate instructions.
- UPDATE `data/shadow-private/pending-v1/review.html`: canonical export and fail-visible local behavior.
- NEW `tests/test_shadow_review.py`: unit and CLI coverage.
- Do not modify `shadow_acquisition.py`, source/image pool bytes, Reasoner/model/config paths, or Story 4.4+ files unless a failing contract proves a narrowly scoped need and the user authorizes it.

### Testing Requirements

- Focused: `uv run pytest -q tests/test_shadow_review.py tests/test_shadow_validation.py tests/test_cli.py`.
- Regression: repository CPU suite unchanged; unrelated frozen failures do not authorize edits outside Story 4.3.
- Quality: `uv run ruff check src/multimodal_bias tests` and `uv run ruff format --check src/multimodal_bias tests`.
- Real-data check may read the existing 600-row manifests after human decisions arrive, but default unit tests use tiny generated images and do not decode the 1.27GB pool.
- Completion evidence must include decision/adjudication input hashes, counts by terminal state, retained coverage, unresolved disputes, CLI exit status and no-clobber verification.

### Previous Story Intelligence

- spec-4-2b established 600 verified Open Images pixels, immutable image hashes, deterministic balance and pending-only status. Story 4.3 must consume these artifacts without mutation.
- spec-4-2 established metadata/source evidence and explicitly excluded VSR pixels; review must not reintroduce VSR or MIAP demographic fields.
- Shadow foundation already implements audit/freeze/evaluate boundaries. Extend the review gap rather than duplicating freeze or evaluation logic.
- The local review screen deliberately reveals the proposed label only after an independent answer; preserve that blind ordering.

### Latest Technical Information

- 외부 API나 새 library 선택이 없으므로 웹 조사는 필요하지 않다. `pyproject.toml`의 Python 3.10, Pillow 11–12, Typer 0.26.x 및 현재 `uv.lock`이 구현 기준이다.

### References

- [Source: docs/history/epics.md#Story-4.3-Independently-Review-Adjudicate-and-Balance-Samples]
- [Source: docs/history/architecture.md#Validation-Strategy]
- [Source: docs/history/architecture.md#Implementation-Patterns-Consistency-Rules]
- [Source: _bmad-output/specs/spec-shadow-private-validation/SPEC.md]
- [Source: _bmad-output/specs/spec-shadow-private-validation/dataset-contract.md]
- [Source: _bmad-output/specs/spec-shadow-private-validation/evaluation-and-freeze-policy.md]
- [Source: spec-4-2b-shadow-image-and-pending-corpus.md]
- [Source: src/multimodal_bias/validation.py]
- [Source: data/shadow-private/pending-v1/review.html]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- immutable typed review/adjudication 계약과 strict JSONL 경계를 먼저 테스트로 고정한다.
- 기존 Shadow loader/audit를 재사용해 review merge, append-only history, atomic no-clobber bundle을 구현한다.
- 검수 UI와 CLI를 canonical 계약에 맞추고 partial pilot을 명시적으로 non-ready로 처리한다.
- CPU 회귀와 Ruff를 통과시킨 뒤 실제 사람 pilot 및 600건 terminal decision에서 중단한다.

### Debug Log References

- RED: `tests/test_shadow_review.py` 최초 실행에서 `multimodal_bias.shadow_review` 미구현으로 실패.
- GREEN: Story 4.3 집중 테스트 16 passed; Shadow/CLI 회귀 69 passed.
- 전체 CPU suite: 460 passed, 2 failed. 두 실패는 동결 범위의 기존 `models/snapshots` scaffold 부재이며 Story 4.3 파일 수정 권한 밖이다.
- 해당 동결 scaffold 검사 2개 제외 전체 CPU suite: 460 passed, 2 deselected.
- Story 4.3 및 비동결 소스 Ruff check/format: pass. 전체 Ruff의 남은 오류는 동결된 Gemma 테스트 2개 파일의 기존 import/format 문제다.
- 검수 HTML JavaScript 정적 구문 검사: pass. 인앱 브라우저 검증은 `codex/sandbox-state-meta: missing field sandboxPolicy` 세션 오류로 실행 불가했다.
- 한국어 병기 vocabulary coverage 및 집중 회귀: 71 passed. 화면·records·번역 HTTP endpoint는 모두 200 응답했다.

### Completion Notes List

- strict human review/adjudication schema, fail-closed binding rules, append-only evidence bundle과 balance readiness gate를 구현했다.
- partial pilot과 미해결 dispute는 bundle을 남기되 CLI exit 1 및 `promotion_ready=false`를 유지한다.
- AI 검수 결정은 생성하지 않았다. 실제 사람 30–50건 pilot과 이후 600건 terminal decision/adjudication이 남아 Story 상태를 `in-progress`로 유지한다.
- Story 4.4 freeze, 모델 추론·평가 및 다른 동결 범위는 시작하지 않았다.
- 2026-06-21 사용자 결정에 따라 사람 검수 checkpoint를 보류했다. 구현물과 pending corpus는 보존하지만 평가셋으로 승격하지 않는다.

### File List

- configs/validation/README.md
- configs/validation/adjudication-template.json
- configs/validation/review-ko-translations.json
- configs/validation/review-template.json
- data/shadow-private/pending-v1/review.html
- docs/history/stories/4-3-independently-review-adjudicate-and-balance-samples.md
- scripts/serve-shadow-review.command
- src/multimodal_bias/cli.py
- src/multimodal_bias/schemas.py
- src/multimodal_bias/shadow_review.py
- sprint-status.yaml
- tests/test_shadow_review.py

## Change Log

- 2026-06-21: Story 4.3 context created and marked ready for development; human review remains an explicit completion gate.
- 2026-06-21: Story 4.3 review/adjudication engine, canonical UI/templates, CLI and CPU-safe tests implemented; moved to human pilot checkpoint without fabricating review labels.
- 2026-06-21: Added a macOS local-server launcher so the static review UI can load JSONL and image assets without `file://` restrictions.
- 2026-06-21: Added complete Korean context/question/answer translations with English audit text and vocabulary-coverage regression tests.
- 2026-06-21: User deferred human review; Story returned to backlog and all 600 records remain pending and excluded from evaluation.
