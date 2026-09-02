# v3.1 가드 프롬프트 A/B 실험 지시서

목적: best(14006) 대비 **익명 그룹 진술 가드**를 추가한 v3.1이 검증셋에서
- `amb_protected` 정확도를 올리는가 (best는 0.36)
- `dis_named`/`dis_protected`(명시 개인)를 유지하는가 (best는 0.90/0.94)
를 확인. 둘 다 만족하면 Public 1회 제출로 최종 판정.

## 배경 (한 줄)
v3 검증셋에서 best가 0.7249. 폭락 원인 = `amb_protected` 32/50 오답, 전부 "익명 그룹 진술(A White person did X)에 낚여 그 그룹 사람 선택". test에도 이 구조가 914행(11%) 실재, best가 39%에서 사람 선택 → 0.996 천장의 정체로 추정.

## 실행

### A. baseline (best, 이미 했으면 재사용)
```bash
python3 data/local-validation/v3/codex_handoff/run_valset.py \
  --valset-dir data/local-validation/v3 \
  --image-dir  data/shadow-private/image-pool-v1/images \
  --model-name Qwen/Qwen3.5-9B \
  --out data/local-validation/v3/sub_best.csv
python3 data/local-validation/v3/score_valset.py \
  data/local-validation/v3/sub_best.csv data/local-validation/v3/answer_key.csv
```

### B. v3.1 가드 프롬프트 (모델 동일, 프롬프트만 교체)
```bash
python3 data/local-validation/v3/codex_handoff/run_valset.py \
  --valset-dir data/local-validation/v3 \
  --image-dir  data/shadow-private/image-pool-v1/images \
  --model-name Qwen/Qwen3.5-9B \
  --system-prompt-file data/local-validation/v3/codex_handoff/prompts/system_v3_1_anon_guard.txt \
  --out data/local-validation/v3/sub_v31.csv
python3 data/local-validation/v3/score_valset.py \
  data/local-validation/v3/sub_v31.csv data/local-validation/v3/answer_key.csv
```

## 판정 (채택/폐기)

| 관찰 | 의미 | 조치 |
|---|---|---|
| amb_protected ↑ (0.36→0.6+) **그리고** dis_named/dis_protected 유지(±0.03) | 가드가 의도대로 작동 | **채택 후보** → Public 1회 제출 |
| amb_protected ↑ 인데 **dis_named/dis_protected ↓** (명시 개인까지 unknown으로) | v4 재현(과보호) | **폐기** 또는 가드 문구 약화 |
| amb_protected 거의 안 오름 | 가드 약함 | 문구 강화 재시도 |

전체 Balanced Accuracy보다 **서브셋별 표**가 중요. amb_protected ↑ + dis_* 유지가 핵심 시그널.

## 회신
두 실행의 score_valset.py 출력 표 전체 + `sub_best.csv`, `sub_v31.csv`, 각 `.raw.jsonl` 를 회신.

## 다음 (사람이 판단)
- 검증셋에서 좋으면 → v3.1 프롬프트로 **8500 full 추론 → Public 1회 제출**.
- Public이 0.99608 **이상**이면 채택, 미만이면 폐기(best 유지). 이게 최종 심판.
- 절대 검증셋 정답에만 의존해 full 제출을 확정하지 말 것. Public 교차확인 필수.
