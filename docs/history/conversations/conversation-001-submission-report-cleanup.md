# 대화 001 - 제출물별 점수·문제 비교·Reasoner 사용 정보 정리

## 목적

Multimodal 제출 화면 스크린샷에 나온 각 제출물을 기준으로, 제출 ID·점수·로컬 CSV·라벨 분포·기준 제출 대비 문제별 차이·사용 Reasoner 정보를 폴더별로 정리하는 것이 목표였다. 샘플별 공식 맞음/틀림도 정리하려 했으나, TEST 정답 라벨이 로컬에 없어서 공식 정오표는 만들 수 없었다.

## 핵심 요약

사용자는 제출물별로 어떤 문제가 맞고 틀렸는지, 점수까지 포함해 폴더로 정리해 달라고 요청했다. 먼저 로컬 저장소에서 제출 CSV, 실행 결과, 점수 관련 문서와 메타데이터를 탐색했다. `data/raw/open/test/test.csv`에는 정답 라벨이 없고 `data/raw/open/train/train.csv`에만 라벨이 있음을 확인했다. 따라서 TEST 제출물의 샘플별 공식 맞음/틀림은 확정할 수 없고, 공개 점수와 제출 간 라벨 불일치만 정리할 수 있다고 판단했다. 그 결과 `experiments/analysis/submission_reports_20260623/` 아래에 14개 제출물별 폴더와 전체 요약 파일을 생성했다. 기준 제출은 스크린샷에서 선택되어 있고 표시 점수가 가장 높은 `1467476`으로 두었으며, 각 `diffs_vs_1467476_selected_reference.csv`는 공식 오답 목록이 아니라 기준 제출과 다른 문제 목록이라고 명시했다. 이후 사용자가 각 제출에 어떤 Reasoner가 들어갔는지 폴더 안에 넣어야 한다고 지적했고, 각 제출 폴더에 `reasoner_used.md`, `reasoner_system_prompt.txt`, `reasoner_user_template.txt`, `reasoner_details.json`을 추가했다. C/D/E/F/G JSON-only 제출과 14006 계열 일부는 해시와 run summary로 정확히 연결했고, `1466963`, `1466590`은 exact run manifest가 없어 근거 문서 기반 추정으로 표시했다.

## 시도한 작업

시간 순서대로 정리했다.

| 순서 | 시도한 내용 | 사용한 방법·명령어 | 결과 |
| -- | ------ | ---------- | --------------- |
| 1 | 현재 작업 디렉터리 확인 | `pwd` | 성공 |
| 2 | 저장소 최상위 파일 확인 | `ls` | 성공 |
| 3 | 전체 파일 목록 탐색 | `rg --files` | 성공. 출력이 매우 커서 일부가 truncation됨 |
| 4 | 제출 CSV 후보 탐색 | `find submissions -maxdepth 3 -type f` | 성공. `submission_emergency_label2.csv`, `submission_emergency_sample_submission.csv` 확인 |
| 5 | 실제 제출 폴더 탐색 | `find '실제 제출' -maxdepth 3 -type f` | 성공. 여러 제출 CSV 확인 |
| 6 | runs 아래 제출 CSV 탐색 | `find runs -maxdepth 3 -type f -name 'submission*.csv'` | 성공. Qwen/Gemma 관련 run 제출 CSV 확인 |
| 7 | 스크린샷 제출 ID·점수·관련 문자열 검색 | `rg -n "1467824|submission_D_jsononly_recovered|0\\.9850833333|1467476|0\\.9960833333|score|leaderboard|submission_id"` | 부분 성공. 필요한 단서가 나왔지만 출력이 커서 일부 truncation됨 |
| 8 | Qwen JSON-only 산출물 탐색 | `find experiments/analysis/qwen_jsononly_transfers_20260623 -maxdepth 4 -type f` | 성공. C/D/E/F/G 제출·raw audit·summary·manifest 확인 |
| 9 | Qwen Reasoner 후보 문서 탐색 | `find experiments/analysis/qwen_reasoner_optimization_20260623 -maxdepth 4 -type f` | 성공. 후보 prompt YAML과 관련 문서 확인 |
| 10 | 데이터셋과 라벨 파일 탐색 | `find data -maxdepth 4 -type f`, `find . -path './.git' -prune -o -type f -name '*label*' -print` | 성공. TEST 라벨 파일은 확인되지 않음 |
| 11 | 당시 적용 중이던 AGENTS lock 확인 | `sed -n '1,220p' AGENTS.md` | 성공. 당시 작업은 기존 CSV 정리 중심으로 제한해서 진행 |
| 12 | JSON-only manifest와 summary 확인 | `sed -n '1,220p' experiments/analysis/qwen_jsononly_transfers_20260623/jsononly_recovered_all_20260623/manifest.json`, `sed -n '1,220p' .../summary_D_original.json`, `sed -n '1,220p' .../analysis_recovery_manifest_dfg.json` | 성공. 각 후보 run, 라벨 분포, 복구 ID, sha 확인 |
| 13 | CSV 구조와 TEST/TRAIN 라벨 유무 확인 | `head -n 5 .../submission_D_jsononly_recovered.csv`, `head -n 5 '실제 제출/퀸2.5 1/submission.csv'`, `head -n 5 data/raw/open/test/test.csv`, `head -n 5 data/raw/open/train/train.csv` | 성공. TEST에는 label 컬럼 없음, TRAIN에는 label 컬럼 있음 |
| 14 | 제출 CSV별 sha·행 수·라벨 분포 계산 | `python3 - <<'PY' ...`로 CSV 순회 및 SHA256/분포 계산 | 성공. 14개 제출과 로컬 CSV 대응 확인 |
| 15 | 일부 파일 mtime 확인 | `stat -f '%Sm %N' ...` | 성공. `1466590` 로컬 대응 추정에 참고 |
| 16 | 기존 보고서 폴더 존재 여부 확인 | `find experiments/analysis/submission_reports_20260623 -maxdepth 2 -type f` | 실패. 해당 폴더가 아직 없어 `No such file or directory` 발생 |
| 17 | C/E/F/G summary 세부 확인 | `sed -n '1,180p' .../summary_E.json`, `summary_C_original.json`, `summary_F_original.json`, `summary_G_original.json` | 성공 |
| 18 | 제출 보고서 폴더와 요약 CSV 생성 | `python3 - <<'PY' ...`로 `experiments/analysis/submission_reports_20260623` 생성 | 성공. 14개 제출 보고서 생성 |
| 19 | 생성 파일 검증 | `find experiments/analysis/submission_reports_20260623 -maxdepth 2 -type f`, `sed -n '1,120p' .../README.md`, `head -n 16 .../leaderboard_summary.csv`, `sed -n '1,100p' .../1467824.../README.md` | 성공 |
| 20 | 대표 diff와 줄 수 검증 | `head -n 5 .../diffs_vs_1467476_selected_reference.csv`, `head -n 12 .../pairwise_disagreement_counts.csv`, `wc -l ...` | 성공. `all_predictions_wide.csv` 8501줄, `leaderboard_summary.csv` 15줄, D diff 606줄 확인 |
| 21 | git 상태 확인 시도 | `git status --short` | 실패. `fatal: not a git repository (or any of the parent directories): .git` |
| 22 | 생성된 제출 하위 폴더 수 확인 | `find experiments/analysis/submission_reports_20260623 -mindepth 1 -maxdepth 1 -type d` | 성공. 14개 제출 폴더 확인 |
| 23 | 사용자가 Reasoner 정보 누락을 지적 | 대화 응답 및 추가 작업 착수 | 성공. 접근 변경 |
| 24 | run summary/config/prompt 후보 탐색 | `find runs -maxdepth 3 -type f (...)`, `rg -n "reasoner|Reasoner|prompt_version|..."`, `find configs src -maxdepth 4 -type f (...)` | 부분 성공. `rg` 출력은 매우 커서 truncation됐지만 필요한 파일 확인 |
| 25 | prompt loader와 summary/script 확인 | `sed -n '1,220p' src/multimodal_bias/prompting/templates.py`, `sed -n '1,120p' runs/.../summary.json`, `sed -n '1,220p' scripts/run_inference_14006_vllm.py`, `scripts/run_inference_14006_v4_vllm.py`, `scripts/run_qwen35_v3_vllm.py` | 성공 |
| 26 | prompt 해시 계산 | `python3 - <<'PY' ... yaml.safe_load ... hashlib.sha256 ...` | 성공. canonical v1/v2/v3와 candidate YAML/system prompt 해시 확인 |
| 27 | 14006 script의 `SYSTEM_PROMPT` 해시 추출 | `python3 - <<'PY' ... ast.parse ...` | 성공. base 14006 해시 `9af3...`, v4 해시 `b1a...` 확인 |
| 28 | Gemma v3 run manifest와 제출 해시 대조 | `sed -n '1,160p' runpod-result-backup-20260621/.../run_manifest.json`, `sed -n '1,140p' .../summary.json`, `shasum -a 256 ...` | 성공. `1467051` 로컬 제출과 backup submission 해시 일치 확인 |
| 29 | Qwen2.5 v1 관련 근거 확인 | `rg -n "c1a00048f6995504|퀸2.5|Qwen2.5|..."`, `sed -n '1,150p' experiments/investigations/submission-score-091-investigation.md`, `sed -n '180,230p' docs/history/runpod-qwen2-5-vl-7b-reproduction-2026-06-19.md`, `sed -n '1,80p' configs/models/qwen2_5_vl_7b.yaml` | 성공. `1466590`을 Qwen2.5 Reasoner v1 계열로 정리하되 exact manifest 없음으로 표시 |
| 30 | JSON-only markdown prompt의 candidate별 system prompt 해시 추출 | `python3 - <<'PY' ... re ... candidate_prompts_jsononly.md ...` 및 `candidate_prompts_jsononly_no_placeholder.md`, `candidate_prompts_ce_jsononly.md` | 성공. C/D/E/F/G summary의 `system_prompt_sha256`과 일치하는 prompt 확인 |
| 31 | C/E, D/F/G run log 확인 | `sed -n '1,80p' experiments/analysis/qwen_jsononly_transfers_20260623/.../ce-jsononly-full-qwen35-20260623-01.log`, `dfg-jsononly-full-qwen35-20260623-01.log` | 성공. 각 candidate key/title/summary 확인 |
| 32 | 제출별 Reasoner 파일 생성 | `python3 - <<'PY' ...`로 각 제출 폴더에 `reasoner_*` 파일 생성 및 README에 섹션 추가 | 성공. 14개 제출에 Reasoner 정보 추가 |
| 33 | Reasoner 파일 생성 검증 | `find experiments/analysis/submission_reports_20260623 -maxdepth 2 -type f (...) | wc -l`, `head -n 16 .../reasoner_mapping.csv`, `sed -n '1,120p' .../1467824.../reasoner_used.md`, `sed -n '1,100p' .../1467605.../reasoner_used.md` | 성공. Reasoner 관련 파일 56개 확인 |
| 34 | 현재 대화 정리 문서 위치 확인 | `ls docs`, `find docs analysis -maxdepth 2 -type f -name '*conversation*' -o -name '*대화*'`, `find experiments/analysis/submission_reports_20260623 -maxdepth 2 -type f | sort` | 성공. 기존 conversation 문서 없음, 보고서 파일 존재 확인 |
| 35 | 이 문서 작성 | `apply_patch`로 `docs/conversation-001-submission-report-cleanup.md` 생성 | 성공 |

## 성공한 내용

- 스크린샷에 나온 14개 제출물을 기준으로 `experiments/analysis/submission_reports_20260623/`에 제출별 하위 폴더를 만들었다.
- 각 제출 폴더에 공개 점수, 제출 시각, 로컬 CSV 경로, SHA256, 행 수, 라벨 분포, 기준 제출 대비 일치/불일치 수를 정리했다.
- 전체 요약 파일 `leaderboard_summary.csv`, `pairwise_disagreement_counts.csv`, `all_predictions_wide.csv`를 생성했다.
- `1467476` 제출을 기준 제출로 사용했다. 이유는 스크린샷에서 선택되어 있고 표시된 제출물 중 공개 점수가 가장 높기 때문이다.
- TEST 정답 라벨이 없다는 한계를 문서와 CSV에 명시했다.
- 각 제출 폴더에 `reasoner_used.md`, `reasoner_system_prompt.txt`, `reasoner_user_template.txt`, `reasoner_details.json`을 추가했다.
- C/D/E/F/G JSON-only 제출은 run log, summary, prompt hash를 기준으로 candidate prompt와 연결했다.
- 14006 계열 제출은 script `SYSTEM_PROMPT` 해시와 run summary의 `system_prompt_sha256`을 대조해 base 14006 prompt 또는 v4 prompt로 구분했다.
- `1467051`은 `runpod-result-backup-20260621/.../run_manifest.json`과 제출 SHA256 일치를 통해 canonical `reasoner_v3.yaml` 사용으로 정리했다.
- `1466963`, `1466590`은 exact run manifest가 없어서 확정 표현을 피하고 `inferred/high`로 표시했다.

## 실패하거나 중단된 내용

- 샘플별 공식 맞음/틀림 목록 작성은 완료하지 못했다. 이유는 TEST 정답 라벨이 로컬에 없고 공개 리더보드가 샘플별 정오 정보를 제공하지 않기 때문이다.
- `git status --short`는 실패했다. 현재 작업 디렉터리가 Git 저장소로 인식되지 않았다.
- `experiments/analysis/submission_reports_20260623` 존재 확인은 최초 시도에서 실패했다. 당시에는 아직 생성 전이었기 때문이다.
- `rg --files`와 일부 `rg -n ...` 검색은 성공했지만 출력이 너무 커서 표시가 truncation됐다. 필요한 후속 확인은 더 좁은 `find`, `sed`, `head`, Python 스크립트로 수행했다.

## 발생한 오류와 원인

- 오류 메시지: `find: experiments/analysis/submission_reports_20260623: No such file or directory`
  - 확인된 원인: 보고서 폴더를 생성하기 전에 존재 여부를 확인했기 때문에 발생했다.
  - 추정 원인: 해당 없음.

- 오류 메시지: `fatal: not a git repository (or any of the parent directories): .git`
  - 확인된 원인: `git status --short` 실행 시 현재 디렉터리가 Git 저장소로 인식되지 않았다.
  - 추정 원인: `.git`이 없거나, 현재 환경에서 Git 메타데이터가 일반 저장소처럼 접근되지 않았을 가능성이 있다. 정확한 원인은 추가 확인되지 않음.

- 출력 문제: `Warning: truncated output`
  - 확인된 원인: `rg --files`와 넓은 `rg -n ...` 검색 결과가 매우 커서 도구 출력이 잘렸다.
  - 추정 원인: 저장소에 8,500개 테스트 이미지와 다수의 raw/log 산출물이 있어서 출력량이 컸다.

## 결정사항

- 공식 샘플별 맞음/틀림은 작성하지 않는다. TEST 정답 라벨이 없기 때문이다.
- 샘플별 비교는 `1467476` 기준 제출과의 라벨 불일치로 작성한다.
- `diffs_vs_1467476_selected_reference.csv`의 행은 “오답”이 아니라 “기준 제출과 다른 답”으로 해석한다.
- 전체 보고서 위치는 `experiments/analysis/submission_reports_20260623/`로 한다.
- 각 제출 폴더에는 점수/분포/비교 정보뿐 아니라 실제 사용 Reasoner 정보를 넣는다.
- Reasoner 매핑은 해시·run summary·run log로 확인되는 경우 `exact`로 표시하고, exact manifest가 없는 경우 `inferred/high`처럼 신뢰도를 분리해 표시한다.
- `1467476`은 `Multimodal codeshare 14006 shared prompt` 계열 기준 제출로 정리한다.
- `1467605`는 `Multimodal 14006-style Reasoner v4`로 정리한다.
- `1467820`~`1467824`의 C/D/E/F/G 제출은 `JSON-only Reasoner v3 candidate`로 정리한다.
- `1466590`은 `Original Qwen2.5 Reasoner v1 YAML`로 정리하되, exact run manifest가 없음을 명시한다.

## 변경된 파일

| 파일 경로 | 변경 유형 | 변경 내용 | 현재 상태 |
| ----- | ----------------- | ----- | ---------- |
| `experiments/analysis/submission_reports_20260623/README.md` | 생성 후 수정 | 제출 보고서 전체 안내, 점수 순위, 한계, Reasoner 사용 정보 안내 추가 | 완료 |
| `experiments/analysis/submission_reports_20260623/leaderboard_summary.csv` | 생성 | 14개 제출물의 ID, 점수, 시각, SHA256, 라벨 분포, 기준 제출 대비 차이 요약 | 완료 |
| `experiments/analysis/submission_reports_20260623/pairwise_disagreement_counts.csv` | 생성 | 제출물 간 pairwise 라벨 불일치 개수와 비율 | 완료 |
| `experiments/analysis/submission_reports_20260623/all_predictions_wide.csv` | 생성 | 8,500개 TEST 샘플별 모든 제출 라벨을 wide format으로 정리 | 완료 |
| `experiments/analysis/submission_reports_20260623/reasoner_mapping.csv` | 생성 | 제출 ID별 Reasoner 계열, prompt source, runner, model, hash, 신뢰도 매핑 | 완료 |
| `experiments/analysis/submission_reports_20260623/reasoner_mapping.json` | 생성 | `reasoner_mapping.csv`의 JSON 버전 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467824_submission_D_jsononly_recovered/README.md` | 생성 후 수정 | 제출 D 점수/분포/비교 요약 및 Reasoner 섹션 추가 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467824_submission_D_jsononly_recovered/label_distribution.csv` | 생성 | 제출 D 라벨 분포 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467824_submission_D_jsononly_recovered/diffs_vs_1467476_selected_reference.csv` | 생성 | 제출 D와 기준 제출 `1467476`의 샘플별 불일치 목록 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467824_submission_D_jsononly_recovered/comparison_summary.json` | 생성 | 제출 D 기준 비교 요약 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467824_submission_D_jsononly_recovered/reasoner_used.md` | 생성 | 제출 D가 사용한 Candidate D JSON-only Reasoner v3 정보 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467824_submission_D_jsononly_recovered/reasoner_system_prompt.txt` | 생성 | 제출 D system prompt | 완료 |
| `experiments/analysis/submission_reports_20260623/1467824_submission_D_jsononly_recovered/reasoner_user_template.txt` | 생성 | 제출 D user prompt template | 완료 |
| `experiments/analysis/submission_reports_20260623/1467824_submission_D_jsononly_recovered/reasoner_details.json` | 생성 | 제출 D Reasoner 세부 메타데이터 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467823_submission_F_jsononly_recovered/*` | 생성 후 일부 수정 | 제출 F의 README, 분포, 기준 대비 diff, 비교 summary, Reasoner 4개 파일 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467822_submission_E_jsononly/*` | 생성 후 일부 수정 | 제출 E의 README, 분포, 기준 대비 diff, 비교 summary, Reasoner 4개 파일 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467821_submission_G_jsononly_recovered/*` | 생성 후 일부 수정 | 제출 G의 README, 분포, 기준 대비 diff, 비교 summary, Reasoner 4개 파일 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467820_submission_C_jsononly_recovered/*` | 생성 후 일부 수정 | 제출 C의 README, 분포, 기준 대비 diff, 비교 summary, Reasoner 4개 파일 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467605_qwen35_9b_v4/*` | 생성 후 일부 수정 | 제출 `1467605`의 README, 분포, 기준 대비 diff, 비교 summary, Reasoner 4개 파일 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467554_qwen25_vl_32b_awq/*` | 생성 후 일부 수정 | 제출 `1467554`의 README, 분포, 기준 대비 diff, 비교 summary, Reasoner 4개 파일 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467518_qwen36_35b_4bit_awq_user/*` | 생성 후 일부 수정 | 제출 `1467518`의 README, 분포, 기준 대비 diff, 비교 summary, Reasoner 4개 파일 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467505_gemma4_26b_awq_user/*` | 생성 후 일부 수정 | 제출 `1467505`의 README, 분포, 기준 대비 diff, 비교 summary, Reasoner 4개 파일 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467476_qwen35_9b_user_selected_reference/*` | 생성 후 일부 수정 | 기준 제출 `1467476`의 README, 분포, 비교 summary, Reasoner 4개 파일. diff 파일은 기준 자신과 비교라 0건 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467051_gemma4_26b_a4b_awq/*` | 생성 후 일부 수정 | 제출 `1467051`의 README, 분포, 기준 대비 diff, 비교 summary, Reasoner 4개 파일 | 완료 |
| `experiments/analysis/submission_reports_20260623/1467007_gemma4/*` | 생성 후 일부 수정 | 제출 `1467007`의 README, 분포, 기준 대비 diff, 비교 summary, Reasoner 4개 파일 | 완료 |
| `experiments/analysis/submission_reports_20260623/1466963_qwen35_v3/*` | 생성 후 일부 수정 | 제출 `1466963`의 README, 분포, 기준 대비 diff, 비교 summary, Reasoner 4개 파일 | 완료 |
| `experiments/analysis/submission_reports_20260623/1466590_qwen25_1_inferred/*` | 생성 후 일부 수정 | 제출 `1466590`의 README, 분포, 기준 대비 diff, 비교 summary, Reasoner 4개 파일 | 완료 |
| `docs/conversation-001-submission-report-cleanup.md` | 생성 | 이 대화 전체를 GitHub 프로젝트 정리용 문서로 정리 | 완료 |

삭제된 파일 없음. 이동된 파일 없음.

## 현재 상태

부분 완료.

제출물별 폴더 정리, 공개 점수 기재, 기준 제출 대비 문제별 불일치 정리, 사용 Reasoner 문서화는 완료됐다. 그러나 공식 TEST 정답 라벨이 확인되지 않았기 때문에 “각 문제가 실제로 맞았는지 틀렸는지”는 완료되지 않았다. 따라서 현재 산출물은 공식 정오표가 아니라 제출물 관리·비교·Reasoner provenance 문서다.

## 미해결 사항

- TEST 샘플별 공식 정답 라벨은 확인되지 않음.
- 공개 리더보드 점수만으로 어떤 샘플이 맞았거나 틀렸는지는 확인되지 않음.
- `1466963`의 exact local run manifest는 확인되지 않음.
- `1466590`의 exact production raw output과 exact run manifest는 확인되지 않음.
- `git status --short` 실패 원인은 추가로 확인되지 않음.
- 스크린샷의 `1466590`은 메모가 없어 로컬 `실제 제출/퀸2.5 1/submission.csv`와의 대응이 추정으로 남아 있음.

## 다음 작업

1. TEST 정답 라벨 또는 공식 샘플별 채점 결과를 확보할 수 있는지 확인한다. 확보하지 못하면 정오표 생성은 불가능하다고 유지한다.
2. `1466963`, `1466590`의 원본 run directory 또는 manifest가 다른 위치에 있는지 추가 탐색한다.
3. `experiments/analysis/submission_reports_20260623/README.md`와 `reasoner_mapping.csv`를 GitHub README 또는 프로젝트 wiki에서 참조할지 결정한다.
4. 필요하면 `diffs_vs_1467476_selected_reference.csv`를 기반으로 “기준 제출 대비 위험 후보 문제” 리뷰 작업을 별도 문서로 분리한다.
5. Git 저장소 인식 문제를 확인해야 한다면 `.git` 위치와 현재 작업 디렉터리 구조를 별도로 점검한다.

## 다른 대화와 공유할 정보

- 제출 보고서 루트: `experiments/analysis/submission_reports_20260623/`
- 전체 안내 문서: `experiments/analysis/submission_reports_20260623/README.md`
- 전체 점수 요약: `experiments/analysis/submission_reports_20260623/leaderboard_summary.csv`
- 제출별 Reasoner 매핑: `experiments/analysis/submission_reports_20260623/reasoner_mapping.csv`
- 모든 제출 라벨 wide table: `experiments/analysis/submission_reports_20260623/all_predictions_wide.csv`
- pairwise 불일치 요약: `experiments/analysis/submission_reports_20260623/pairwise_disagreement_counts.csv`
- 기준 제출: `1467476`
- 기준 제출을 사용하는 이유: 스크린샷에서 선택되어 있고 표시된 제출물 중 공개 점수가 가장 높음.
- 주의사항: `diffs_vs_1467476_selected_reference.csv`는 공식 오답 목록이 아니라 기준 제출과 다른 문제 목록이다.
- 주의사항: TEST 정답 라벨이 없으므로 샘플별 공식 맞음/틀림은 확인되지 않음.
- Reasoner 매핑에서 `1466963`, `1466590`은 exact manifest 기반 확정이 아니라 근거 문서 기반 추정으로 표시되어 있다.

## 근거 및 신뢰도

- 대화에서 직접 확인된 내용:
  - 스크린샷에 제출 ID, 파일명/메모, 제출 시각, 공개 점수가 표시됐다.
  - `submissions/`, `실제 제출/`, `runs/`, `experiments/analysis/qwen_jsononly_transfers_20260623/` 아래에서 제출 CSV와 summary/manifest/log 파일을 확인했다.
  - `data/raw/open/test/test.csv`에는 `sample_id,image_path,context,question,answers`만 있고 `label` 컬럼이 없었다.
  - `data/raw/open/train/train.csv`에는 `label` 컬럼이 있었다.
  - `experiments/analysis/submission_reports_20260623/` 아래 보고서와 Reasoner 파일들이 생성됐다.
  - `all_predictions_wide.csv`는 8,501줄, `leaderboard_summary.csv`는 15줄, 제출 D의 기준 대비 diff 파일은 606줄이었다.
  - Reasoner 관련 파일은 14개 제출 폴더에 4개씩, 총 56개가 생성됐다.
  - `git status --short`는 Git 저장소 인식 실패로 종료됐다.

- 대화 내용을 바탕으로 한 해석:
  - `1467476`은 스크린샷에서 선택되어 있고 공개 점수가 가장 높아 비교 기준으로 적합하다고 판단했다.
  - C/D/E/F/G JSON-only 제출은 run log, summary, prompt hash가 일치하므로 Reasoner candidate 매핑을 exact로 볼 수 있다.
  - 14006 계열 제출은 script `SYSTEM_PROMPT`와 summary hash가 일치하므로 base 14006 또는 v4 prompt 매핑을 exact로 볼 수 있다.
  - `1466963`, `1466590`은 근거 문서와 로컬 폴더명/제출 맥락상 매핑 신뢰도가 높지만 exact run manifest가 없어 확정은 아니다.

- 확인되지 않은 내용:
  - TEST 샘플별 공식 정답.
  - 각 제출물의 샘플별 공식 맞음/틀림.
  - `1466963`의 exact run manifest와 raw output 전체.
  - `1466590`의 exact production raw output과 exact run manifest.
  - `git status --short` 실패의 정확한 파일시스템 원인.
  - 스크린샷의 `1466590`과 로컬 `실제 제출/퀸2.5 1/submission.csv`의 원격 메타데이터 기반 확정 대응.
