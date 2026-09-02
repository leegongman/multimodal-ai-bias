# v3.1 가드 프롬프트 — test 8500 full 추론 & Public 제출

목적: 검증셋에서 best(0.7249)→v3.1(0.7689, +0.044) 개선 확인됨.
이제 **test 8500 full 추론 → Public 1회 제출**로 진짜 효과 확인.

## 이게 best와 다른 단 한 가지
`run_inference_v31_vllm.py`는 기존 검증된 `run_inference_14006_vllm.py`와 **SYSTEM_PROMPT만 다름**.
모델(Qwen3.5-9B), 파서, 디코딩(temp=0,top_k=1,max_tokens=200), max_pixels(200704) 전부 동일.
추가된 것: 규칙4 "익명 그룹 진술(A White person did X)은 개인 지목 근거가 아니다 → unknown".

## 실행 (best 돌릴 때와 100% 동일, 스크립트 이름만 다름)

### 1. vLLM 서버 (best와 동일)
```bash
bash scripts/serve_inference_14006_vllm.sh   # Qwen3.5-9B, max_pixels 200704
curl -fsS http://127.0.0.1:8000/v1/models
```

### 2. full 추론 (8500)
```bash
# run_inference_v31_vllm.py 를 scripts/ 에 두거나 경로 맞춰 실행
python3 run_inference_v31_vllm.py \
  --data-dir data/raw/open/test \
  --output-dir runs/qwen35-9b-v31-full-$(date +%Y%m%d-%H%M) \
  --base-url http://127.0.0.1:8000/v1 \
  --concurrency 32
```
(best가 8500을 ~32분에 돌렸으므로 동일 예상)

### 3. 출력 검증 (제출 전 필수)
```bash
OUT=runs/qwen35-9b-v31-full-*   # 위 output-dir
wc -l $OUT/submission.csv                    # 8501 (헤더+8500)
python3 -c "import pandas as pd; d=pd.read_csv('$OUT/submission.csv'); print('rows',len(d)); print('labels',sorted(d.label.unique())); print(d.label.value_counts().sort_index())"
cat $OUT/summary.json | python3 -m json.tool | grep -E 'failure|parse|generated|seconds_per'
```
체크: rows=8500, label∈{0,1,2}, failure_count=0, parse 전부 valid.

### 4. Public 제출
- `submission.csv`를 Multimodal에 제출 (UTF-8, sample_id,label).
- **best와 비교:** best Public = 0.99608.
  - v3.1 ≥ 0.99608 → **가드 가설 확정.** 채택 + 더 강화 가치 확정.
  - v3.1 < 0.99608 → 검증셋 정답이 평가와 불일치. **폐기**, best 유지.

## 참고 — v3.1 라벨 분포 예상
가드가 사람→unknown 일부 이동시키므로 best보다 unknown(분포상 특정 라벨)이 늘 수 있음.
best 분포: {0:2956, 1:2731, 2:2813}. 큰 폭 이동(수백)이면 과보호 의심.

## 회신
`submission.csv`, `summary.json`, 그리고 Public 점수.
