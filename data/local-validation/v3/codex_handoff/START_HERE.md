# Multimodal 236722 검증셋 v3 핸드오프 — 시작점

**먼저 읽기:** `INSTRUCTIONS.md` (이 폴더)

## v3란
v2가 너무 쉬워서(best 0.9944) test 수준으로 어렵게 재제작한 188문항. 변별력 확보가 목적.

## 3줄 실행 (레포 루트 기준)
1. vLLM 서버 (Qwen/Qwen3.5-9B, --mm-processor-kwargs '{"max_pixels":200704,"min_pixels":50176}')
2. `python3 data/local-validation/v3/codex_handoff/run_valset.py --valset-dir data/local-validation/v3 --image-dir data/shadow-private/image-pool-v1/images --model-name Qwen/Qwen3.5-9B --out data/local-validation/v3/sub_best.csv`
3. `python3 data/local-validation/v3/score_valset.py data/local-validation/v3/sub_best.csv data/local-validation/v3/answer_key.csv`

→ 채점 표(Balanced/Acc_amb/Acc_dis + 서브셋) + sub_best.csv + sub_best.raw.jsonl 를 회신.
