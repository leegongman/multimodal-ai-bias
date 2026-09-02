# 2-pass (Reasoner v3.1 + Verifier) 실험 가이드

목표: 단일 프롬프트의 한계(익명진술 정답이 unknown/사람 반반이라 상쇄)를 2단계로 분리.
공개 0.99633 예시가 이 구조. 같은 Qwen3.5-9B 위에서 동작 → 재현 리스크 낮음.

## 구조
- Pass1: Reasoner(v3.1 가드 프롬프트)가 1차 답+근거.
- Pass2: '재검토 가치 있는 행'에만 Verifier 호출. Verifier가 이미지+근거 보고 **최종답 생성**.
  - 트리거: (a) 사람 선택했는데 context가 익명그룹 진술 → trap 의심  (b) unknown인데 이름/위치/역할 명시 → 도망 의심
  - 나머지는 reasoner 답 유지 → 속도/안정.
- 최종 라벨은 항상 LLM 텍스트 파싱(규칙 §7 준수).

## 단계 1: 검증셋 A/B (먼저, GPU 30분)
```bash
# 검증셋을 test.csv 형식으로 사용 (--csv-name valset.csv)
python3 two_pass_v32/run_2pass_vllm.py \
  --data-dir data/local-validation/v3 --csv-name valset.csv \
  --image-dir data/shadow-private/image-pool-v1/images \
  --output-dir runs/valset-2pass-$(date +%H%M) \
  --reasoner-prompt two_pass_v32/prompts/reasoner_system_v31.txt \
  --verifier-prompt two_pass_v32/prompts/verifier_system.txt \
  --concurrency 32
python3 data/local-validation/v3/score_valset.py runs/valset-2pass-*/submission.csv data/local-validation/v3/answer_key.csv
```
비교 기준 (검증셋):
- v3.1 단일: Balanced 0.7689 (amb_protected 0.42, dis_named 0.90)
- 2-pass 목표: amb_protected ↑ **그리고** dis_named/dis_protected 유지(±0.03).
  - amb↑ & dis유지 → 채택, full 진행.
  - dis↓ → verifier가 과교정. verifier_system.txt 의 check2(명시개인 보호) 강화.

## 단계 2: full 8500 (검증셋 통과 시)
```bash
python3 two_pass_v32/run_2pass_vllm.py \
  --data-dir data/raw/open/test --csv-name test.csv \
  --output-dir runs/test-2pass-$(date +%Y%m%d-%H%M) \
  --reasoner-prompt two_pass_v32/prompts/reasoner_system_v31.txt \
  --verifier-prompt two_pass_v32/prompts/verifier_system.txt \
  --concurrency 32
# 검증
python3 -c "import pandas as pd;d=pd.read_csv('runs/test-2pass-*/submission.csv');print('rows',len(d),'labels',sorted(d.label.unique()))"
cat runs/test-2pass-*/summary.json   # verified/flipped 수, seconds_per_sample(<0.5 확인)
```
→ submission.csv Public 제출. **best 0.99608 / v3.1 0.99617 과 비교.**

## 런타임 주의
verifier가 트리거된 행만 2번 호출. 트리거 비율이 낮으면 0.5초/sample 무난.
--verify-all 은 전행 2회 호출(느림, 디버그용).

## 회신
검증셋 채점 표 + (full 돌렸으면) summary.json + Public 점수.
