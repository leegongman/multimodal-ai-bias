# Codex 작업 지시서 — Multimodal 236722 로컬 검증셋 실행 & 모델 후보 평가

작성: 2026-06-23 | 대상 실행자: Codex (RunPod RTX 6000 / A6000 48GB 환경)

---

## 0. 한 장 요약 (먼저 읽기)

우리는 Multimodal 236722(멀티모달 Bias QA, Balanced Accuracy)에서 **Public 0.99608 제출(best = Qwen3.5-9B + "14006" 프롬프트)** 를 보유. 리더보드 약 47위. test 8500개에 정답이 없어 **모든 개선이 Public 제출 도박**이었다.

이 핸드오프는 그 도박을 없애기 위한 **test 비파생 로컬 검증셋(188문항, 정답 포함)** 과 **자립 실행/채점 스크립트**다.

**해야 할 일(요약):**
1. best 프롬프트로 검증셋 추론 → 채점 = **baseline 확보**
2. 후보(다른 VL 모델 / 프롬프트 변경)를 **같은 검증셋**에 돌려 비교
3. `Acc_ambiguous`(편향회피)와 `Acc_disambiguated`(명시사실 사용)를 분리해 보고 → 진짜 개선만 채택
4. 결과 표를 사람에게 회신

**철칙:** 검증셋은 평가 전용. 절대 학습/파인튜닝에 쓰지 말 것. 정답을 보고 문항을 고치지 말 것(그러면 검증셋 무효).


## ⚠️ v3 변경 (v2 대비)
v2(188문항)는 best가 Balanced 0.9944로 너무 쉬웠다(answer를 거의 직접 알려주는 문장). 
v3는 **test 실제 스타일로 난이도 상향**: "does not identify which individual" 같은 안내문 제거, 
익명성/모호성을 모델이 스스로 판단하게 함. dis_named에 likely류 추가(best가 약했던 구간).
목적: best가 0.95~0.97대로 내려와 **후보 모델 간 변별**이 가능해지는 것.
이번에도 먼저 best로 baseline 재측정 → 그 다음 후보 비교.

---

## 1. 배경 — 왜 이 검증셋인가 (데이터로 확인된 사실)

8500개 전체 예측 교차분석 결과:
- best는 unknown을 58.6% 선택(5모델 중 최다). **점수 높은 모델일수록 unknown 多.** 이 task가 Bias 벤치라 ambiguous(정답=unknown) 비중이 크기 때문.
- "best=unknown인데 다른 3+모델=동일인물" = **355건**, 반대 = 17건 (20:1 비대칭).
- 그 355건을 직접 판독: **66%가 보호속성 익명진술 trap**("A White person이 거짓말 같은 얘길 했다"→옵션의 The White person 지목은 인종라벨 편향), **추가로 성별역할/표정 trap**. 즉 **best의 unknown이 옳고 다른 모델이 trap에 빠진 경우가 다수.**
- 결론: 프롬프트로 "사람 더 고르게" 바꾸면 trap에서 점수 하락(= 과거 v4가 0.99608→0.99133로 실패한 메커니즘).

→ 그래서 개선의 진짜 후보는 **"trap은 그대로 피하면서 객관적 시각 grounding을 더 잘하는 모델"**. 그걸 **제출 없이** 가리려면 이 검증셋이 필요.

---

## 2. 파일 설명 (이 폴더 = `data/local-validation/v3/`)

| 파일 | 무엇 |
|---|---|
| `valset.csv` | 추론 입력. 188행. 컬럼 `sample_id,image_path,context,question,answers` (test.csv와 동일 포맷, `answers`는 JSON 배열 문자열) |
| `answer_key.csv` | 정답키. `sample_id,expected_label,uncertainty_option_index,expected_is_uncertainty,subset` |
| `records.jsonl` | 전체 레코드(서브셋·근거 포함, 사람이 읽기용) |
| `score_valset.py` | 채점기. submission(sample_id,label) → Balanced Accuracy + 서브셋 분해 |
| `README.md` | 검증셋 설계 상세 |
| `codex_handoff/run_valset.py` | **자립 추론 스크립트.** vLLM 서버에 붙어 best 프롬프트(또는 대체 프롬프트)로 추론 → submission CSV |
| `codex_handoff/INSTRUCTIONS.md` | 이 문서 |

이미지: `data/shadow-private/image-pool-v1/images/` (실제 Open Images, CC 라이선스). `valset.csv`의 `image_path`는 `images/<sha>.jpg` 형식 — `run_valset.py`는 `--image-dir`로 받은 폴더에서 basename으로 찾는다.

### 검증셋 구성 (188)
- **ambiguous 90 (정답=unknown):** protected 50 / gender_role 20 / expression 20
- **disambiguated 98 (정답=인물):** named 48 / position 32 / protected 18
- 라벨·unknown위치 균형. test 문항을 복사하지 않고 *구조*만 재현(leakage 아님).

---

## 3. 실행 단계

### Step 0. 사전 확인
```bash
cd <레포 루트>          # 예: /workspace/multimodal-bias 또는 멀티모달 AI Bias 루트
ls data/local-validation/v3/valset.csv data/local-validation/v3/answer_key.csv
ls data/shadow-private/image-pool-v1/images | head -1     # 이미지 존재 확인
pip show openai >/dev/null 2>&1 || pip install openai     # 추론 클라이언트
```

### Step 1. vLLM 서버 (best와 동일 설정)
best는 `Qwen/Qwen3.5-9B`, `--max-model-len 32768`, `--mm-processor-kwargs '{"max_pixels":200704,"min_pixels":50176}'`.
기존 스크립트가 있으면 그대로:
```bash
bash scripts/serve_inference_14006_vllm.sh
# 또는 직접:
# vllm serve <Qwen3.5-9B 경로> --served-model-name Qwen/Qwen3.5-9B \
#   --host 127.0.0.1 --port 8000 --max-model-len 32768 \
#   --mm-processor-kwargs '{"max_pixels":200704,"min_pixels":50176}'
curl -fsS http://127.0.0.1:8000/v1/models   # 준비 확인
```

### Step 2. baseline 추론 (best 프롬프트)
```bash
python3 data/local-validation/v3/codex_handoff/run_valset.py \
  --valset-dir data/local-validation/v3 \
  --image-dir  data/shadow-private/image-pool-v1/images \
  --base-url   http://127.0.0.1:8000/v1 \
  --model-name Qwen/Qwen3.5-9B \
  --out        data/local-validation/v3/sub_best.csv
```
(188개라 1~2분. `sub_best.csv` + `sub_best.raw.jsonl` 생성)

### Step 3. 채점
```bash
python3 data/local-validation/v3/score_valset.py \
  data/local-validation/v3/sub_best.csv \
  data/local-validation/v3/answer_key.csv
```
→ 출력되는 표 전체를 사람에게 회신.

---

## 4. 후보 평가 (baseline 확보 후)

### 4-A. 다른 모델 비교 (가장 중요)
동일 검증셋에 **다른 VL 모델**을 같은 best 프롬프트로 돌려 비교. 모델만 바꾸면 됨:
```bash
# 후보 모델로 vLLM 서버를 띄운 뒤 (규칙: 2026.05.31 이전 공개 가중치, 48GB 적재, 평균 0.5s/sample 이내)
python3 .../run_valset.py --valset-dir ... --image-dir ... \
  --model-name <후보모델ID> --out data/local-validation/v3/sub_<후보>.csv
python3 .../score_valset.py data/local-validation/v3/sub_<후보>.csv data/local-validation/v3/answer_key.csv
```
**후보 모델 우선순위 가이드:** "더 큰 Qwen"은 이미 실패(32B/35B < 9B). 객관적 시각 grounding이 강한 *다른 계열* VL을 우선. 단 규칙 적격성(공개일/라이선스/오프라인) 먼저 확인.

### 4-B. 프롬프트 변경 비교 (선택)
대체 프롬프트 텍스트 파일을 만들어:
```bash
python3 .../run_valset.py ... --system-prompt-file my_prompt.txt --out sub_promptB.csv
```

---

## 5. 결과 해석 — 채택/폐기 규칙

채점 출력의 세 숫자가 핵심: `Acc_ambiguous`, `Acc_disambiguated`, `Balanced Accuracy`.

| 관찰 | 의미 | 조치 |
|---|---|---|
| Balanced ↑, **Acc_ambiguous 유지** + Acc_disambiguated ↑ | 이상적. best 약점(명시사실 도망)만 보완 | **채택 후보.** Public 1회 제출로 교차확인 |
| Balanced ↑ 인데 **Acc_ambiguous ↓** | trap에 더 낚인 것(v4 패턴). Public은 올라도 Hidden서 붕괴 위험 | **폐기** |
| Balanced ≈ best | 차이 없음 | 단순/안전한 best 유지 |
| best가 여기서 거의 만점(>0.98) | 검증셋 변별력 부족 | 사람에게 보고 → 난이도 상향 요청 |

**서브셋 표도 함께 보고:** 예) 후보가 `disambiguated_position`(시각 grounding)만 올리고 `ambiguous_protected` 유지면 = 우리가 찾던 개선.

---

## 6. 회신 형식 (사람에게)

아래를 채워서 회신:
```
[모델/프롬프트]        Balanced  Acc_amb  Acc_dis  비고
best(Qwen3.5-9B/14006)  0.???     0.???    0.???    baseline
후보A(<모델>)            0.???     0.???    0.???
...
서브셋별 표: (각 실행의 score_valset.py 출력 그대로)
```

---

## 7. 하지 말 것 (규칙·무결성)
- 검증셋을 학습/파인튜닝 데이터로 쓰지 말 것.
- answer_key를 보고 valset 문항을 수정하지 말 것(검증셋 무효화).
- test.csv 패턴·정답을 추론해 프롬프트에 넣지 말 것(평가 §7 leakage 금지).
- 최종 답은 LLM 생성 텍스트여야 함. 룰/조건문으로 라벨을 직접 결정하지 말 것.
- 원격 API 모델 금지. 로컬 가중치만.
