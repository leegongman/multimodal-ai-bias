# 모델 교체 실험 — InternVL3-14B + v3.1 + 2-pass

## 핵심: 추론 코드/프롬프트는 그대로. 모델만 교체.
- Reasoner 프롬프트: v3.1 (two_pass_v32/prompts/reasoner_system_v31.txt) — 변경 없음
- Verifier 프롬프트: (two_pass_v32/prompts/verifier_system.txt) — 변경 없음
- 2-pass 로직: run_2pass_vllm.py — 변경 없음
- **바뀌는 것: vLLM 서버가 띄우는 모델 + --model-name 값 뿐**

## 왜 이 모델
- visual_needed 유형 1990행(이미지 봐야 풀림)에서 Qwen3.5-9B가 약함. 그 18행이 25등(0.99833)과의 격차.
- InternVL3-14B: 2025-04 공개(규칙 OK), RefCOCO grounding 강함, 14B라 48GB 적재 가능.
- ⚠️ 솔직한 경고: 과거 Qwen2.5-VL-32B/gemma-26B는 (가드 없이) 떨어졌음. 시각↑여도 trap↓면 도루묵.
  그래서 **반드시 검증셋부터 재서 trap(amb) 안 무너지는지 확인 후 full.**

## 0. 모델 다운로드 (RunPod)
```bash
# 적격성: OpenGVLab/InternVL3-14B, 2025-04-11 공개. 라이선스 확인할 것(MIT/Apache 계열).
huggingface-cli download OpenGVLab/InternVL3-14B --local-dir model/InternVL3-14B
```

## 1. vLLM 서버 (모델만 교체, 이미지 설정 동일)
```bash
vllm serve model/InternVL3-14B \
  --served-model-name OpenGVLab/InternVL3-14B \
  --host 127.0.0.1 --port 8000 \
  --max-model-len 32768 \
  --trust-remote-code \
  --mm-processor-kwargs '{"max_pixels":200704,"min_pixels":50176}'
# InternVL은 trust-remote-code 필요할 수 있음. 이미지 토큰 설정은 Qwen과 동일하게 시작.
curl -fsS http://127.0.0.1:8000/v1/models
```

## 2. 검증셋 A/B 먼저 (GPU ~1시간, full 전 필수 게이트)
```bash
python3 two_pass_v32/run_2pass_vllm.py \
  --data-dir data/local-validation/v3 --csv-name valset.csv \
  --image-dir data/shadow-private/image-pool-v1/images \
  --output-dir runs/valset-internvl-2pass-$(date +%H%M) \
  --reasoner-prompt two_pass_v32/prompts/reasoner_system_v31.txt \
  --verifier-prompt two_pass_v32/prompts/verifier_system.txt \
  --model-name OpenGVLab/InternVL3-14B \
  --concurrency 16
python3 data/local-validation/v3/score_valset.py runs/valset-internvl-2pass-*/submission.csv data/local-validation/v3/answer_key.csv
```

### 판정 (검증셋)
기준선 = Qwen3.5-9B 2-pass: Balanced 0.8069, amb_protected 0.52, dis_named 0.94
- amb 유지(±0.03) **그리고** dis ↑ (특히 시각 관련) → **승산. full 진행**
- amb 크게 떨어짐 → trap에 약함(과거 실패 재현). **즉시 폐기**, Qwen3.5-9B 2-pass 유지
- 별 차이 없음 → 모델 교체 효과 없음. 폐기.

## 3. full 8500 (검증셋 통과 시에만)
```bash
python3 two_pass_v32/run_2pass_vllm.py \
  --data-dir data/raw/open/test --csv-name test.csv \
  --output-dir runs/test-internvl-2pass-$(date +%Y%m%d-%H%M) \
  --reasoner-prompt two_pass_v32/prompts/reasoner_system_v31.txt \
  --verifier-prompt two_pass_v32/prompts/verifier_system.txt \
  --model-name OpenGVLab/InternVL3-14B \
  --concurrency 16
cat runs/test-internvl-2pass-*/summary.json   # seconds_per_sample < 0.5 확인!
```
→ submission.csv Public 제출. best 0.99608 / Qwen2pass 0.99617 / 25등 0.99833 과 비교.

## 주의
- 14B는 9B보다 느림. seconds_per_sample 확인 필수(<0.5). 넘으면 동시성/이미지 토큰 조정.
- 다운로드~서버~검증셋에 1~2시간. full 추가 1시간. 시간 예산 확인.
- 검증셋에서 안 좋으면 full 가지 말 것 (제출 횟수·시간 낭비).

## 대안 후보 (InternVL 안되면)
- Qwen2.5-VL-7B (레포에 이미 있음, RefCOCO Qwen3.5급, 더 빠름). --model-name 만 교체.
